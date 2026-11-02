"""End-to-end build pipeline."""

from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from situlearn.audio import (
    AudioCache,
    RateLimiter,
    synthesize_section,
    synthesize_term,
)
from situlearn.chains import extract_terms, plan_narrative, repair_narrative_chinese
from situlearn.dictionary import DictionaryClient, DictionaryEntry
from situlearn.gloss import gloss_terms
from situlearn.human_audio import HumanAudio, resolve_human_audio
from situlearn.knowledge import (
    AudioAsset,
    AudioSource,
    AudioStatus,
    NarrativeScript,
    ReportManifest,
    SourceInfo,
    SourceRef,
    TermCandidate,
    TermEntry,
)
from situlearn.llm import make_chat_model
from situlearn.progress import Progress
from situlearn.report import assemble_report
from situlearn.segmenter import segment_cues
from situlearn.srt import parse_srt
from situlearn.tts import XiaomiTTS

PROMPT_VERSION = "v2"
DEFAULT_CACHE_ROOT = Path.home() / ".cache" / "situlearn"


@dataclass
class BuildResult:
    report_path: Path
    manifest_path: Path
    cue_count: int
    segment_count: int
    term_count: int
    warnings: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def _read_json(path: Path) -> object | None:
    """Read a JSON cache file, returning None when it is missing or corrupt."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _load_or_create_narrative(
    llm,
    segments,
    cache_path: Path,
    *,
    force: bool,
) -> NarrativeScript:
    script = None
    if cache_path.exists() and not force:
        try:
            script = NarrativeScript.model_validate_json(cache_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            script = None
    if script is None:
        script = plan_narrative(llm, segments)

    repaired = repair_narrative_chinese(llm, script)
    if repaired != script or not cache_path.exists():
        cache_path.write_text(repaired.model_dump_json(indent=2), encoding="utf-8")
    return repaired


def _load_or_create_terms(
    llm,
    segments,
    script: NarrativeScript,
    cache_path: Path,
    *,
    force: bool,
) -> list[TermCandidate]:
    if cache_path.exists() and not force:
        payload = _read_json(cache_path)
        if isinstance(payload, list):
            try:
                return [TermCandidate.model_validate(item) for item in payload]
            except (TypeError, ValueError):
                pass
    terms = extract_terms(llm, segments, script)
    cache_path.write_text(
        json.dumps([term.model_dump(mode="json") for term in terms], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return terms


def _lookup_dictionary(terms: list[TermCandidate]) -> dict[str, DictionaryEntry]:
    client = DictionaryClient()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda term: client.lookup(term.term), terms))
    mapping: dict[str, DictionaryEntry] = {}
    for term, entry in zip(terms, results):
        if entry is None:
            continue
        mapping[term.term.casefold()] = entry
        mapping[term.lemma.casefold()] = entry
    return mapping


def _load_or_create_dictionary(
    candidates: list[TermCandidate],
    cache_path: Path,
    *,
    force: bool,
) -> dict[str, DictionaryEntry]:
    if cache_path.exists() and not force:
        payload = _read_json(cache_path)
        if isinstance(payload, dict):
            try:
                return {
                    key: DictionaryEntry.model_validate(value)
                    for key, value in payload.items()
                }
            except (TypeError, ValueError):
                pass
    mapping = _lookup_dictionary(candidates)
    cache_path.write_text(
        json.dumps(
            {key: value.model_dump(mode="json") for key, value in mapping.items()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return mapping


def _load_or_create_gloss(llm, candidates, dictionary, cache_path: Path, *, force: bool) -> list[TermEntry]:
    if cache_path.exists() and not force:
        payload = _read_json(cache_path)
        if isinstance(payload, list):
            try:
                return [TermEntry.model_validate(item) for item in payload]
            except (TypeError, ValueError):
                pass
    terms = gloss_terms(llm, candidates, dictionary)
    cache_path.write_text(
        json.dumps(
            [term.model_dump(mode="json") for term in terms],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return terms


def _asset_for(
    ref: str,
    text: str,
    source: AudioSource,
) -> AudioAsset:
    return AudioAsset(
        asset_id=Path(ref).stem,
        path=ref,
        duration_ms=0,
        text_sha256=_sha256_text(text),
        source=source,
    )


def build_report(
    input_path: Path,
    out_dir: Path,
    *,
    voice: str = "冰糖",
    terms_min: int = 30,
    terms_max: int = 80,
    no_audio: bool = False,
    force: bool = False,
    cache_root: Path | None = None,
    progress: Progress | None = None,
) -> BuildResult:
    started = time.time()
    progress = progress or Progress()
    input_path = input_path.expanduser().resolve()
    out_dir = out_dir.expanduser().resolve()
    warnings: list[str] = []

    cues = parse_srt(input_path)
    progress.stage(f"解析字幕：{len(cues)} 条")
    segments = segment_cues(cues)
    progress.stage(f"内容切分：{len(segments)} 个片段")
    input_sha = _sha256_file(input_path)
    cache_base = cache_root or DEFAULT_CACHE_ROOT
    run_cache = cache_base / input_sha[:16]
    run_cache.mkdir(parents=True, exist_ok=True)
    progress.stage(f"缓存目录：{cache_base}")

    llm = make_chat_model()
    narrative_path = run_cache / f"narrative-{PROMPT_VERSION}.json"
    progress.stage(
        "叙事脉络：命中缓存"
        if narrative_path.exists() and not force
        else "叙事脉络：调用 LLM 生成（首次约 1-2 分钟）"
    )
    script = _load_or_create_narrative(llm, segments, narrative_path, force=force)

    terms_path = run_cache / f"terms-{PROMPT_VERSION}.json"
    progress.stage(
        "术语提取：命中缓存"
        if terms_path.exists() and not force
        else "术语提取：调用 LLM 分析字幕"
    )
    candidates = _load_or_create_terms(
        llm,
        segments,
        script,
        terms_path,
        force=force,
    )

    if not terms_min <= len(candidates) <= terms_max:
        warnings.append(f"term_count_out_of_range={len(candidates)}")

    dictionary_path = run_cache / "dictionary.json"
    progress.stage(
        "词典查询：命中缓存"
        if dictionary_path.exists() and not force
        else f"词典查询：{len(candidates)} 个词条"
    )
    dictionary = _load_or_create_dictionary(candidates, dictionary_path, force=force)

    gloss_path = run_cache / f"gloss-{PROMPT_VERSION}.json"
    progress.stage(
        "释义生成：命中缓存"
        if gloss_path.exists() and not force
        else "释义生成：调用 LLM 编写中英释义"
    )
    terms: list[TermEntry] = _load_or_create_gloss(
        llm,
        candidates,
        dictionary,
        gloss_path,
        force=force,
    )
    if not terms:
        raise RuntimeError("gloss stage returned no terms")
    if not terms_min <= len(terms) <= terms_max:
        warnings.append(f"glossed_term_count_out_of_range={len(terms)}")

    assets: list[AudioAsset] = []
    if no_audio:
        progress.stage("音频：已通过 --no-audio 跳过")
        for section in script.sections:
            section.audio_refs = []
            section.audio_status = AudioStatus.UNAVAILABLE
        for term in terms:
            term.audio_ref = "unavailable"
            term.audio_source = AudioSource.UNAVAILABLE
        warnings.append("audio_disabled")
    else:
        tts = XiaomiTTS()
        cache = AudioCache(cache_base / "audio")
        limiter = RateLimiter(90)
        assets_dir = out_dir / "assets" / "audio"
        progress.stage(f"真人发音：检查 {len(terms)} 个词条")
        human_audio: dict[str, HumanAudio | None] = resolve_human_audio(
            terms,
            candidates,
            cache_dir=cache_base / "human_audio",
            cache_path=run_cache / "human_audio.json",
            force=force,
            on_item=lambda index, total: progress.counter("真人发音", index, total),
        )
        progress.finish()

        progress.stage(f"章节音频：{len(script.sections)} 段")
        for index, section in enumerate(script.sections, start=1):
            progress.counter("章节音频", index, len(script.sections))
            refs, status = synthesize_section(
                tts, cache, limiter, section, assets_dir, voice=voice
            )
            section.audio_refs = refs
            section.audio_status = status
            for ref in refs:
                assets.append(_asset_for(ref, section.spoken_text, AudioSource.TTS))
            if status is not AudioStatus.READY:
                warnings.append(f"{section.section_id}_audio_{status.value}")
        progress.finish()

        progress.stage(f"词条音频：{len(terms)} 个词条")
        for index, term in enumerate(terms, start=1):
            progress.counter("词条音频", index, len(terms))
            human = human_audio.get(term.term)
            if human is not None:
                slug = hashlib.sha256(term.term.casefold().encode()).hexdigest()[:12]
                destination = assets_dir / f"term-{slug}.mp3"
                assets_dir.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(human.data)
                term.audio_ref = f"assets/audio/{destination.name}"
                term.audio_source = AudioSource.DICTIONARY
                term.sources.append(SourceRef(name=human.source, url=human.entry_url))
                if human.scope == "keyword":
                    term.pronunciation_note = (
                        f"多词词条，播放关键词「{human.matched}」的真人发音。"
                    )
                elif human.scope == "alias":
                    term.pronunciation_note = (
                        f"词形变体，播放「{human.matched}」的真人发音。"
                    )
                elif not term.ipa:
                    term.pronunciation_note = f"真人发音来源：{human.source}"
                assets.append(_asset_for(term.audio_ref, term.term, AudioSource.DICTIONARY))
                continue

            ref = synthesize_term(tts, cache, limiter, term, assets_dir, voice=voice)
            term.audio_ref = ref
            term.audio_source = (
                AudioSource.TTS if ref != "unavailable" else AudioSource.UNAVAILABLE
            )
            term.pronunciation_note = "无免费真人音源，使用 TTS 发音"
            if ref != "unavailable":
                assets.append(_asset_for(ref, term.term, AudioSource.TTS))
            else:
                warnings.append(f"term_audio_unavailable={term.term}")

        progress.finish()

        if assets_dir.exists():
            referenced = {Path(asset.path).name for asset in assets}
            for path in assets_dir.glob("*.mp3"):
                if path.name not in referenced:
                    path.unlink()

    manifest = ReportManifest(
        schema_version="1.0.0",
        source=SourceInfo(
            filename=input_path.name,
            sha256=input_sha,
            duration_ms=max(cue.end_ms for cue in cues) - min(cue.start_ms for cue in cues),
            cue_count=len(cues),
        ),
        config={
            "llm_framework": "langchain",
            "llm_provider": "deepseek",
            "llm_model": "deepseek-flash",
            "narrative_language": "zh",
            "tts_model": "mimo-v2.5-tts",
            "tts_voice": voice,
            "prompt_version": PROMPT_VERSION,
            "langchain_version": _package_version("langchain"),
            "langchain_deepseek_version": _package_version("langchain-deepseek"),
        },
        narrative=script,
        terms=terms,
        assets=assets,
        warnings=warnings,
    )

    progress.stage("生成报告：manifest.json + report.html")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    report_path = assemble_report(manifest, out_dir)

    return BuildResult(
        report_path=report_path,
        manifest_path=manifest_path,
        cue_count=len(cues),
        segment_count=len(segments),
        term_count=len(terms),
        warnings=warnings,
        elapsed_s=time.time() - started,
    )
