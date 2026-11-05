"""Migrate old manifest reports into SituLearn documents."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from situlearn import __version__
from situlearn.content import CATEGORY_LABELS, profile_for_manifest
from situlearn.document import (
    Document,
    DocumentValidationError,
    check_document,
    raise_for_errors,
)
from situlearn.knowledge import AudioSource, ReportManifest, is_ai_source

DEFAULT_ATTRIBUTION = (
    "Oxford Learner's Dictionaries",
    "Youdao Dictionary",
    "小米 MiMo TTS",
)


class MigrateError(RuntimeError):
    """An old report could not be migrated."""

    def __init__(self, message: str, *, code: str = "migrate/error") -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class MigrateInfo:
    out_dir: Path
    sections: int
    words: int
    resources: int
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class MigrateResult:
    report_key: str
    info: MigrateInfo | None
    error: str | None


@dataclass(frozen=True)
class CompileInfo:
    document: Document
    warnings: tuple[str, ...]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value)
    return cleaned.strip(".-") or "audio"


def _mime_for(suffix: str) -> str:
    return {
        ".aac": "audio/aac",
        ".m4a": "audio/mp4",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".wav": "audio/wav",
        ".webm": "audio/webm",
    }.get(suffix.lower(), "audio/mpeg")


def _source(value: AudioSource) -> str | None:
    if value is AudioSource.DICTIONARY:
        return "dictionary"
    if value is AudioSource.TTS:
        return "tts"
    return None


def _section_id_map(manifest: ReportManifest, warnings: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for index, section in enumerate(manifest.narrative.sections, start=1):
        if section.section_id in mapping:
            raise MigrateError(
                f"duplicate legacy section id: {section.section_id}",
                code="document/duplicate-id",
            )
        new_id = section.section_id
        if new_id == "vocabulary":
            new_id = f"vocabulary-legacy-{index}"
        if new_id in used:
            base = new_id
            suffix = 2
            while f"{base}-{suffix}" in used:
                suffix += 1
            new_id = f"{base}-{suffix}"
            warnings.append(f"section id collision; renamed {base} to {new_id}")
        if section.section_id == "vocabulary":
            warnings.append(f"legacy section 'vocabulary' renamed to {new_id}")
        mapping[section.section_id] = new_id
        used.add(new_id)
    return mapping


def _copy_resources(
    manifest: ReportManifest,
    old_dir: Path,
    out_dir: Path,
    warnings: list[str],
) -> tuple[dict[str, dict[str, object]], dict[str, str]]:
    used_paths: set[str] = set()
    for section in manifest.narrative.sections:
        used_paths.update(ref for ref in section.audio_refs if ref != "unavailable")
    for term in manifest.terms:
        if term.audio_ref != "unavailable":
            used_paths.add(term.audio_ref)

    assets_by_path = {asset.path: asset for asset in manifest.assets}
    sources_by_path: dict[str, str | None] = {}
    for asset in manifest.assets:
        sources_by_path[asset.path] = _source(asset.source)
    for term in manifest.terms:
        if term.audio_ref != "unavailable" and term.audio_ref not in sources_by_path:
            sources_by_path[term.audio_ref] = _source(term.audio_source)

    resources: dict[str, dict[str, object]] = {}
    resource_by_path: dict[str, str] = {}
    media_dir = out_dir / "media" / "audio"
    media_dir.mkdir(parents=True, exist_ok=True)

    for index, path in enumerate(sorted(used_paths), start=1):
        source_path = old_dir / path
        if not source_path.is_file():
            warnings.append(f"missing audio file: {path}")
            continue
        resource_id = f"r-{index:04d}"
        destination = media_dir / f"{index:04d}-{_safe_name(source_path.name)}"
        shutil.copy2(source_path, destination)
        data = destination.read_bytes()
        href = destination.relative_to(out_dir).as_posix()
        descriptor: dict[str, object] = {
            "type": "audio",
            "mime": _mime_for(source_path.suffix),
            "href": href,
            "sha256": _sha256(data),
        }
        asset = assets_by_path.get(path)
        if asset is not None and asset.duration_ms:
            descriptor["duration_ms"] = int(asset.duration_ms)
        source_value = sources_by_path.get(path)
        if source_value:
            descriptor["source"] = source_value
        resources[resource_id] = descriptor
        resource_by_path[path] = resource_id

    return resources, resource_by_path


def _word_blocks(
    manifest: ReportManifest,
    id_map: dict[str, str],
    resource_by_path: dict[str, str],
    warnings: list[str],
) -> tuple[list[dict[str, object]], dict[str, dict[str, object]]]:
    first_section = next(iter(id_map.values()), None)
    blocks: list[dict[str, object]] = []
    by_term: dict[str, dict[str, object]] = {}

    for index, term in enumerate(manifest.terms, start=1):
        word_id = f"w-{index:04d}"
        section_id = id_map.get(term.section_id)
        if section_id is None:
            section_id = first_section
            warnings.append(
                f"term {term.term!r} references unknown section {term.section_id!r}; "
                "assigned to the first narrative section"
            )
        block: dict[str, object] = {
            "id": word_id,
            "type": "word",
            "term": term.term,
            "definitions": {"zh": term.definition_zh, "en": term.definition_en},
            "section_id": section_id,
        }
        if term.ipa:
            block["ipa"] = term.ipa
        if term.pronunciation_note:
            block["pronunciation_note"] = term.pronunciation_note
        if term.part_of_speech:
            block["part_of_speech"] = term.part_of_speech
        if term.context_sentence:
            block["context"] = term.context_sentence
        if term.why_it_matters:
            block["note"] = term.why_it_matters
        if term.category:
            block["category"] = term.category.value
        if term.audio_ref != "unavailable":
            resource_id = resource_by_path.get(term.audio_ref)
            if resource_id:
                block["audio"] = resource_id
        sources = [source for source in term.sources if not is_ai_source(source)]
        if sources:
            block["sources"] = [source.model_dump(mode="json") for source in sources]
        blocks.append(block)
        key = term.term.casefold()
        if key in by_term:
            warnings.append(f"duplicate term {term.term!r}; first definition kept")
        else:
            by_term[key] = block
    return blocks, by_term


def _document(
    manifest: ReportManifest,
    id_map: dict[str, str],
    resources: dict[str, dict[str, object]],
    resource_by_path: dict[str, str],
    warnings: list[str],
    source_language: str,
) -> Document:
    profile = profile_for_manifest(manifest)
    labels = dataclasses.asdict(profile.labels)
    labels["vocabulary_heading"] = "生词本"
    labels.update({f"category.{key}": value for key, value in CATEGORY_LABELS.items()})

    word_blocks, by_term = _word_blocks(manifest, id_map, resource_by_path, warnings)

    sections: list[dict[str, object]] = []
    for section in manifest.narrative.sections:
        new_id = id_map[section.section_id]
        keywords: list[dict[str, str]] = []
        for term_text in section.key_terms:
            word = by_term.get(term_text.casefold())
            if word is None:
                warnings.append(
                    f"section {section.section_id!r} keyword {term_text!r} has no word card; dropped"
                )
                continue
            if word["section_id"] != new_id:
                warnings.append(
                    f"section {section.section_id!r} keyword {term_text!r} belongs to "
                    f"{word['section_id']!r}; dropped"
                )
                continue
            keywords.append({"word_id": str(word["id"])})

        narration_blocks: list[dict[str, object]] = [
            {"type": "text", "text": section.summary}
        ]
        for reference in section.audio_refs:
            resource_id = resource_by_path.get(reference)
            if resource_id is None:
                warnings.append(
                    f"section {section.section_id!r} audio {reference!r} not found; skipped"
                )
                continue
            narration_blocks.append({"type": "audio", "resource": resource_id})

        sections.append(
            {
                "id": new_id,
                "role": "narrative",
                "title": section.heading,
                "time": {"start_ms": section.start_ms, "end_ms": section.end_ms},
                "layout": "stack",
                "keywords": keywords,
                "blocks": [
                    {
                        "type": "group",
                        "role": "narration",
                        "layout": "stack",
                        "script": section.spoken_text,
                        "blocks": narration_blocks,
                    }
                ],
            }
        )

    sections.append(
        {
            "id": "vocabulary",
            "role": "vocabulary",
            "title": labels["vocabulary_heading"],
            "layout": "grid",
            "blocks": word_blocks,
        }
    )

    document = {
        "format": "situlearn.document",
        "version": 1,
        "meta": {
            "id": manifest.source.sha256,
            "title": manifest.narrative.title,
            "subtitle": manifest.narrative.logline,
            "description": manifest.narrative.background,
            "language": "zh-CN",
            "kind": profile.content_type.value,
            "generator": {"name": "situlearn-migrate", "version": __version__},
            "source": {
                "filename": manifest.source.filename,
                "sha256": manifest.source.sha256,
                "language": source_language,
                "duration_ms": manifest.source.duration_ms,
                "cue_count": manifest.source.cue_count,
            },
            "labels": labels,
            "attribution": list(DEFAULT_ATTRIBUTION),
        },
        "resources": resources,
        "sections": sections,
    }
    try:
        parsed = Document.model_validate(document)
    except ValidationError as exc:
        raise MigrateError(f"migrated document is invalid: {exc}", code="migrate/invalid-document") from exc
    issues = check_document(parsed, mode="write")
    try:
        raise_for_errors(issues)
    except DocumentValidationError as exc:
        raise MigrateError(f"migrated document failed checks: {exc}", code="migrate/invalid-document") from exc
    return parsed


def compile_manifest(
    manifest: ReportManifest,
    source_dir: Path,
    out_dir: Path,
    *,
    source_language: str = "en",
    slug: str | None = None,
    published_at: str | None = None,
) -> CompileInfo:
    """Compile an in-memory manifest and its media into a document directory."""

    source_dir = source_dir.resolve()
    out_dir = out_dir.resolve()
    warnings: list[str] = list(manifest.warnings)
    id_map = _section_id_map(manifest, warnings)
    out_dir.mkdir(parents=True, exist_ok=True)
    resources, resource_by_path = _copy_resources(manifest, source_dir, out_dir, warnings)
    document = _document(
        manifest,
        id_map,
        resources,
        resource_by_path,
        warnings,
        source_language,
    )
    (out_dir / "document.json").write_text(document.to_json(), encoding="utf-8")

    if slug:
        sidecar: dict[str, str] = {"slug": slug}
        if published_at:
            sidecar["published_at"] = published_at
        (out_dir / "publish.json").write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return CompileInfo(document=document, warnings=tuple(warnings))


def _word_count(document: Document) -> int:
    return sum(
        1
        for section in document.sections
        for block in section.blocks
        if block.type == "word"
    )


def migrate_report(
    old_dir: Path,
    out_dir: Path,
    *,
    source_language: str = "en",
    slug: str | None = None,
    published_at: str | None = None,
    force: bool = False,
) -> MigrateInfo:
    """Convert one old report directory into a document directory."""

    old_dir = old_dir.resolve()
    out_dir = out_dir.resolve()
    manifest_path = old_dir / "manifest.json"
    if not manifest_path.is_file():
        raise MigrateError(f"missing manifest.json: {manifest_path}", code="migrate/missing-manifest")
    if out_dir.exists() and out_dir.is_dir() and any(out_dir.iterdir()) and not force:
        raise MigrateError(f"output directory is not empty: {out_dir}", code="migrate/output-exists")

    try:
        manifest = ReportManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError) as exc:
        raise MigrateError(f"invalid manifest: {exc}", code="migrate/invalid-manifest") from exc

    compiled = compile_manifest(
        manifest,
        old_dir,
        out_dir,
        source_language=source_language,
        slug=slug,
        published_at=published_at,
    )
    document = compiled.document
    return MigrateInfo(
        out_dir=out_dir,
        sections=len(document.sections),
        words=_word_count(document),
        resources=len(document.resources),
        warnings=compiled.warnings,
    )


def migrate_batch(
    export_root: Path,
    out_root: Path,
    *,
    source_language: str = "en",
    force: bool = False,
) -> list[MigrateResult]:
    """Convert a directory of exported old bundles named by report_key."""

    export_root = export_root.resolve()
    out_root = out_root.resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    results: list[MigrateResult] = []
    for bundle in sorted(path for path in export_root.iterdir() if path.is_dir()):
        manifest_path = bundle / "manifest.json"
        if not manifest_path.is_file():
            results.append(
                MigrateResult(bundle.name, None, "missing manifest.json")
            )
            continue
        try:
            manifest = ReportManifest.model_validate_json(
                manifest_path.read_text(encoding="utf-8")
            )
            report_key = manifest.source.sha256
            if bundle.name != report_key:
                raise MigrateError(
                    f"bundle directory {bundle.name!r} does not match source sha256",
                    code="migrate/missing-source-sha256",
                )
            slug = None
            published_at = None
            bundle_meta = bundle / "bundle.json"
            if bundle_meta.is_file():
                metadata = json.loads(bundle_meta.read_text(encoding="utf-8"))
                slug = metadata.get("slug")
                published_at = metadata.get("published_at")
            info = migrate_report(
                bundle,
                out_root / report_key,
                source_language=source_language,
                slug=slug,
                published_at=published_at,
                force=force,
            )
            results.append(MigrateResult(report_key, info, None))
        except Exception as exc:  # noqa: BLE001 - batch isolates per-bundle failures
            results.append(MigrateResult(bundle.name, None, str(exc)))
    return results


__all__ = [
    "DEFAULT_ATTRIBUTION",
    "CompileInfo",
    "MigrateError",
    "MigrateInfo",
    "MigrateResult",
    "compile_manifest",
    "migrate_batch",
    "migrate_report",
]
