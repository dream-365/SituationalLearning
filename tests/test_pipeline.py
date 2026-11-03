from __future__ import annotations

import hashlib
import json
from io import StringIO
from pathlib import Path

from situlearn import pipeline
from situlearn.knowledge import (
    AudioSource,
    AudioStatus,
    ContentType,
    NarrativeScript,
    NarrativeSection,
    SourceRef,
    TermCandidate,
    TermCategory,
    TermEntry,
)
from situlearn.progress import Progress


def _script() -> NarrativeScript:
    headings = ["第一章节", "第二章节", "第三章节", "第四章节"]
    sections = [
        NarrativeSection(
            section_id=f"sec-{index:02d}",
            heading=headings[index - 1],
            start_ms=(index - 1) * 15_000,
            end_ms=index * 15_000,
            summary="这是本节摘要，用来测试报告。" * 7,
            spoken_text="这是播报稿，用来测试报告。" * 4,
            audio_refs=[],
            audio_status=AudioStatus.UNAVAILABLE,
        )
        for index in range(1, 5)
    ]
    return NarrativeScript(
        title="测试报告",
        logline="这是一句话简介，用来测试整份报告能否正确渲染。",
        background="这是背景。" * 30,
        sections=sections,
    )


def _movie_script() -> NarrativeScript:
    sections = [
        NarrativeSection(
            section_id=f"sec-{index:02d}",
            heading=f"第{index}场",
            start_ms=(index - 1) * 15_000,
            end_ms=index * 15_000,
            summary="这是本场剧情摘要，用来测试报告。" * 7,
            spoken_text="这是剧情复盘播报稿，用来测试报告。" * 4,
            audio_refs=[],
            audio_status=AudioStatus.UNAVAILABLE,
        )
        for index in range(1, 7)
    ]
    return NarrativeScript(
        title="电影测试报告",
        logline="这是一句话简介，用来测试电影报告能否正确渲染。",
        background="这是电影背景。" * 30,
        sections=sections,
    )


def _candidate() -> TermCandidate:
    return TermCandidate(
        term="cherub",
        lemma="cherub",
        surface_forms=["cherub"],
        category=TermCategory.PROPER_NOUN,
        cue_ids=[1],
        context_sentence="The one with the interested cherub looking on.",
        section_id="sec-01",
        why_it_matters="这个小天使是理解瓦萨里叙事立场的视觉线索。",
        confidence=0.95,
    )


def _entry() -> TermEntry:
    return TermEntry(
        term="cherub",
        ipa="/ˈtʃer.əb/",
        part_of_speech="noun",
        definition_zh="小天使，艺术史中常见的有翼天使形象。",
        definition_en="a winged angelic being",
        audio_ref="unavailable",
        audio_source=AudioSource.UNAVAILABLE,
        context_sentence="The one with the interested cherub looking on.",
        why_it_matters="这个小天使是理解瓦萨里叙事立场的视觉线索。",
        section_id="sec-01",
        category=TermCategory.PROPER_NOUN,
        sources=[SourceRef(name="Wiktionary", url="https://example.com/cherub")],
    )


def test_build_report_no_audio(tmp_path: Path, monkeypatch) -> None:
    srt = tmp_path / "sample.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:15,000\nThe one with the interested cherub.\n\n"
        "2\n00:00:15,000 --> 00:00:30,000\nA second cue for testing.\n\n"
        "3\n00:00:30,000 --> 00:00:45,000\nA third cue for testing.\n\n"
        "4\n00:00:45,000 --> 00:01:00,000\nA fourth cue for testing.\n",
        encoding="utf-8",
    )

    script = _script()
    candidate = _candidate()
    entry = _entry()

    monkeypatch.setattr(pipeline, "make_chat_model", lambda: object())
    monkeypatch.setattr(
        pipeline, "plan_narrative", lambda llm, segments, **kwargs: script
    )
    monkeypatch.setattr(
        pipeline,
        "extract_terms",
        lambda llm, segments, narrative, **kwargs: [candidate],
    )
    monkeypatch.setattr(pipeline, "_lookup_dictionary", lambda terms: {})
    monkeypatch.setattr(
        pipeline,
        "gloss_terms",
        lambda llm, terms, dictionary, **kwargs: [entry],
    )

    progress_out = StringIO()
    result = pipeline.build_report(
        srt,
        tmp_path / "out",
        no_audio=True,
        cache_root=tmp_path / ".cache",
        progress=Progress(progress_out),
    )

    messages = progress_out.getvalue()
    assert "解析字幕：4 条" in messages
    assert "内容切分：1 个片段" in messages
    assert "--no-audio" in messages
    assert result.report_path.exists()
    assert result.manifest_path.exists()
    assert result.cue_count == 4
    assert result.term_count == 1
    assert "audio_disabled" in result.warnings
    assert "测试报告" in result.report_path.read_text(encoding="utf-8")


def test_build_report_documentary_manifest_config_is_legacy(
    tmp_path: Path, monkeypatch
) -> None:
    srt = _write_sample_srt(tmp_path)
    _patch_llm_stages(monkeypatch, _script(), _candidate(), _entry())

    result = pipeline.build_report(
        srt,
        tmp_path / "out",
        terms_min=1,
        terms_max=1,
        no_audio=True,
        cache_root=tmp_path / ".cache",
    )

    config = json.loads(result.manifest_path.read_text(encoding="utf-8"))["config"]
    assert list(config) == [
        "llm_framework",
        "llm_provider",
        "llm_model",
        "narrative_language",
        "tts_model",
        "tts_voice",
        "prompt_version",
        "langchain_version",
        "langchain_deepseek_version",
    ]
    assert "content_type" not in config


def _write_sample_srt(tmp_path: Path) -> Path:
    srt = tmp_path / "sample.srt"
    srt.write_text(
        "1\n00:00:00,000 --> 00:00:15,000\nThe one with the interested cherub.\n\n"
        "2\n00:00:15,000 --> 00:00:30,000\nA second cue for testing.\n\n"
        "3\n00:00:30,000 --> 00:00:45,000\nA third cue for testing.\n\n"
        "4\n00:00:45,000 --> 00:01:00,000\nA fourth cue for testing.\n",
        encoding="utf-8",
    )
    return srt


def _patch_llm_stages(monkeypatch, script, candidate, entry) -> None:
    monkeypatch.setattr(pipeline, "make_chat_model", lambda: object())
    monkeypatch.setattr(
        pipeline, "plan_narrative", lambda llm, segments, **kwargs: script
    )
    monkeypatch.setattr(
        pipeline,
        "extract_terms",
        lambda llm, segments, narrative, **kwargs: [candidate],
    )
    monkeypatch.setattr(pipeline, "_lookup_dictionary", lambda terms: {})
    monkeypatch.setattr(
        pipeline,
        "gloss_terms",
        lambda llm, terms, dictionary, **kwargs: [entry],
    )


def test_build_report_movie_uses_plot_labels(tmp_path: Path, monkeypatch) -> None:
    srt = _write_sample_srt(tmp_path)
    _patch_llm_stages(monkeypatch, _movie_script(), _candidate(), _entry())

    progress_out = StringIO()
    result = pipeline.build_report(
        srt,
        tmp_path / "out",
        content_type="movie",
        terms_min=1,
        terms_max=1,
        no_audio=True,
        cache_root=tmp_path / ".cache",
        progress=Progress(progress_out),
    )

    manifest = result.manifest_path.read_text(encoding="utf-8")
    html = result.report_path.read_text(encoding="utf-8")
    messages = progress_out.getvalue()

    assert '"content_type": "movie"' in manifest
    assert "剧情脉络" in html
    assert "电影学习报告" in html
    assert "全部场景" in html
    assert "回到本场" in html
    assert "内容脉络" not in html
    assert "剧情脉络" in messages
    assert "--no-audio" in messages
    sha16 = hashlib.sha256(srt.read_bytes()).hexdigest()[:16]
    assert str(tmp_path / ".cache" / f"{sha16}-movie") in messages
    assert any(path.name.endswith("-movie") for path in (tmp_path / ".cache").iterdir())


def test_build_report_discards_out_of_profile_cached_narrative(
    tmp_path: Path, monkeypatch
) -> None:
    srt = _write_sample_srt(tmp_path)
    sha16 = hashlib.sha256(srt.read_bytes()).hexdigest()[:16]
    cache_dir = tmp_path / ".cache" / f"{sha16}-movie"
    cache_dir.mkdir(parents=True)
    (cache_dir / "narrative-v2.json").write_text(
        _script().model_dump_json(indent=2),
        encoding="utf-8",
    )

    _patch_llm_stages(monkeypatch, _movie_script(), _candidate(), _entry())
    calls: list[int] = []

    def fake_plan(llm, segments, **kwargs):
        calls.append(1)
        return _movie_script()

    monkeypatch.setattr(pipeline, "plan_narrative", fake_plan)

    result = pipeline.build_report(
        srt,
        tmp_path / "out",
        content_type="movie",
        terms_min=1,
        terms_max=1,
        no_audio=True,
        cache_root=tmp_path / ".cache",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert calls == [1]
    assert len(manifest["narrative"]["sections"]) == 6
    cached = json.loads((cache_dir / "narrative-v2.json").read_text(encoding="utf-8"))
    assert len(cached["sections"]) == 6


def test_build_report_cache_is_isolated_by_content_type(
    tmp_path: Path, monkeypatch
) -> None:
    srt = _write_sample_srt(tmp_path)
    candidate = _candidate()
    entry = _entry()

    def fake_plan(llm, segments, **kwargs):
        profile = kwargs["profile"]
        return _movie_script() if profile.content_type is ContentType.MOVIE else _script()

    _patch_llm_stages(monkeypatch, _script(), candidate, entry)
    monkeypatch.setattr(pipeline, "plan_narrative", fake_plan)

    documentary = pipeline.build_report(
        srt,
        tmp_path / "documentary",
        terms_min=1,
        terms_max=1,
        no_audio=True,
        cache_root=tmp_path / ".cache",
    )
    movie = pipeline.build_report(
        srt,
        tmp_path / "movie",
        content_type="movie",
        terms_min=1,
        terms_max=1,
        no_audio=True,
        cache_root=tmp_path / ".cache",
    )

    cache_dirs = {path.name for path in (tmp_path / ".cache").iterdir()}
    assert len(cache_dirs) == 2
    assert any(name.endswith("-movie") for name in cache_dirs)
    assert "测试报告" in documentary.report_path.read_text(encoding="utf-8")
    assert "电影测试报告" in movie.report_path.read_text(encoding="utf-8")
    assert '"content_type": "movie"' in movie.manifest_path.read_text(encoding="utf-8")
    assert "content_type" not in documentary.manifest_path.read_text(encoding="utf-8")
