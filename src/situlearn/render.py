"""Render a SituLearn document into a derived, offline HTML directory."""

from __future__ import annotations

import dataclasses
import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from situlearn.content import CATEGORY_LABELS, DOCUMENTARY_PROFILE
from situlearn.document import (
    AudioBlock,
    Document,
    DocumentValidationError,
    WordBlock,
    iter_blocks,
    parse_document,
    raise_for_errors,
)
from situlearn.resolver import (
    DirectoryResolver,
    PackageResolver,
    ResourceNotFound,
)

CATEGORY_LABEL_KEYS = {f"category.{key}": value for key, value in CATEGORY_LABELS.items()}
DEFAULT_LABELS: dict[str, str] = {
    **dataclasses.asdict(DOCUMENTARY_PROFILE.labels),
    "vocabulary_heading": "生词本",
    **CATEGORY_LABEL_KEYS,
    "missing_image": "图片缺失",
}


class RenderError(RuntimeError):
    """A document could not be rendered."""

    def __init__(self, message: str, *, code: str = "render/error") -> None:
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class RenderInfo:
    out_dir: Path
    html_path: Path
    sections: int
    blocks: int
    missing: tuple[str, ...]
    warnings: tuple[str, ...]


def _format_ms(value: int) -> str:
    total_seconds = max(0, value) // 1000
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def _definition(block: WordBlock, language: str) -> str:
    definitions = block.definitions
    if language in definitions:
        return definitions[language]
    primary = language.split("-")[0]
    if primary in definitions:
        return definitions[primary]
    return next(iter(definitions.values()))


def _category_label(block: WordBlock, labels: dict[str, str]) -> str:
    if not block.category:
        return ""
    return labels.get(f"category.{block.category}", block.category)


def _template_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(_template_dir()),
        autoescape=True,
    )


def _render_html(
    document: Document,
    *,
    missing: set[str],
    labels: dict[str, str],
    pwa_manifest_url: str | None = None,
) -> str:
    word_index = {
        block.id: block
        for section in document.sections
        for block in iter_blocks(section.blocks)
        if isinstance(block, WordBlock)
    }
    section_audio = {
        section.id: any(isinstance(block, AudioBlock) for block in iter_blocks(section.blocks))
        for section in document.sections
    }
    duration_min = None
    if document.meta.source and document.meta.source.duration_ms:
        duration_min = round(document.meta.source.duration_ms / 60_000, 1)
    template = _environment().get_template("document.html.j2")
    return template.render(
        document=document,
        labels=labels,
        missing=missing,
        word_index=word_index,
        resources=document.resources,
        section_audio=section_audio,
        format_ms=_format_ms,
        definition=_definition,
        category_label=_category_label,
        duration_min=duration_min,
        pwa_manifest_url=pwa_manifest_url,
    )


def render_document_html(
    document: Document,
    *,
    missing: set[str] | None = None,
    labels: dict[str, str] | None = None,
    pwa_manifest_url: str | None = None,
) -> str:
    """Render a document to an HTML string without touching the filesystem."""

    merged = dict(DEFAULT_LABELS)
    merged.update(labels or {})
    merged.update(document.meta.labels)
    return _render_html(
        document,
        missing=missing or set(),
        labels=merged,
        pwa_manifest_url=pwa_manifest_url,
    )


def render_document_in_place(document: Document, out_dir: Path) -> RenderInfo:
    """Render ``index.html`` for a build directory that already has media."""

    out_dir.mkdir(parents=True, exist_ok=True)
    missing: set[str] = set()
    warnings: list[str] = []
    for resource in document.resources.values():
        path = out_dir / resource.href
        if not path.is_file():
            missing.add(resource.href)
            warnings.append(f"missing resource: {resource.href}")
            continue
        if hashlib.sha256(path.read_bytes()).hexdigest() != resource.sha256:
            missing.add(resource.href)
            warnings.append(f"hash mismatch: {resource.href}")
    labels = dict(DEFAULT_LABELS)
    labels.update(document.meta.labels)
    html = _render_html(document, missing=missing, labels=labels)
    html_path = out_dir / "index.html"
    html_path.write_text(html, encoding="utf-8")
    block_count = sum(len(list(iter_blocks(section.blocks))) for section in document.sections)
    return RenderInfo(
        out_dir=out_dir,
        html_path=html_path,
        sections=len(document.sections),
        blocks=block_count,
        missing=tuple(sorted(missing)),
        warnings=tuple(warnings),
    )


def render_document(source: Path, out_dir: Path) -> RenderInfo:
    """Render a document directory or .situ package into ``out_dir``."""

    source = source.resolve()
    out_dir = out_dir.resolve()
    if not source.exists():
        raise RenderError(f"source does not exist: {source}", code="render/missing-source")
    if source.is_dir() and out_dir.is_relative_to(source):
        raise RenderError(
            "output directory must not be inside the source directory",
            code="render/output-inside-source",
        )
    if out_dir.exists():
        if not out_dir.is_dir():
            raise RenderError("output path is not a directory", code="render/output-not-directory")
        if any(out_dir.iterdir()):
            raise RenderError("output directory is not empty", code="render/output-not-empty")
    else:
        out_dir.mkdir(parents=True, exist_ok=True)

    package: PackageResolver | None = None
    if source.is_file():
        try:
            package = PackageResolver(source)
        except (zipfile.BadZipFile, ValueError) as exc:
            raise RenderError(f"invalid .situ package: {exc}", code="render/invalid-package") from exc
        resolver = package
        raw = package.read_entry("document.json")
    else:
        document_path = source / "document.json"
        if not document_path.is_file():
            raise RenderError("missing document.json", code="render/missing-source")
        resolver = DirectoryResolver(source)
        raw = document_path.read_bytes()

    try:
        try:
            document, issues = parse_document(raw, mode="read")
            raise_for_errors(issues)
        except (DocumentValidationError, ValueError) as exc:
            raise RenderError(f"invalid document: {exc}", code="render/invalid-document") from exc

        warnings = [
            f"{issue.code}: {issue.message}" for issue in issues if issue.severity == "warning"
        ]
        missing: set[str] = set()
        for resource in document.resources.values():
            try:
                data = resolver.read(resource.href)
            except ResourceNotFound:
                missing.add(resource.href)
                warnings.append(f"missing resource: {resource.href}")
                continue
            if hashlib.sha256(data).hexdigest() != resource.sha256:
                missing.add(resource.href)
                warnings.append(f"hash mismatch: {resource.href}")
                continue
            destination = out_dir / resource.href
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)

        labels = dict(DEFAULT_LABELS)
        labels.update(document.meta.labels)
        html = _render_html(document, missing=missing, labels=labels)
        html_path = out_dir / "index.html"
        html_path.write_text(html, encoding="utf-8")
    finally:
        if package is not None:
            package.close()

    block_count = sum(
        len(list(iter_blocks(section.blocks))) for section in document.sections
    )
    return RenderInfo(
        out_dir=out_dir,
        html_path=html_path,
        sections=len(document.sections),
        blocks=block_count,
        missing=tuple(sorted(missing)),
        warnings=tuple(warnings),
    )


__all__ = [
    "DEFAULT_LABELS",
    "RenderError",
    "RenderInfo",
    "render_document",
    "render_document_html",
    "render_document_in_place",
]
