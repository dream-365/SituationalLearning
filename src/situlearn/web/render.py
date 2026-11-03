"""Server-side rendering of public report pages."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path, PurePosixPath

from jinja2 import Environment, FileSystemLoader, select_autoescape

from situlearn.knowledge import ReportManifest
from situlearn.web.objectstore import ObjectStoreError
from situlearn.web.repository import ReportRecord, ReportRepository
from situlearn.web.storage import ReportStore

CATEGORY_LABELS = {
    "domain_term": "领域术语",
    "proper_noun": "专名",
    "work_title": "作品名",
    "school_genre": "流派/时期",
    "common_advanced": "低频普通词",
}


class ReportNotFound(LookupError):
    """The requested report does not exist."""


class ReportGone(LookupError):
    """The requested report exists but has been unpublished."""


class SectionNotFound(LookupError):
    """The requested section does not belong to the report."""


@dataclass(frozen=True)
class PublicReport:
    record: ReportRecord
    version_prefix: str
    title: str
    logline: str
    background: str
    duration_min: float
    sections: tuple[dict[str, object], ...]
    terms: tuple[dict[str, object], ...]
    attribution: tuple[str, ...]

    @property
    def slug(self) -> str:
        return self.record.slug

    def section(self, section_id: str) -> dict[str, object]:
        for section in self.sections:
            if section["section_id"] == section_id:
                return section
        raise SectionNotFound(section_id)


def _format_ms(value: int) -> str:
    total_seconds = max(0, value) // 1_000
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def _public_asset_url(slug: str, reference: str) -> str:
    if not reference or reference == "unavailable":
        return "unavailable"
    path = PurePosixPath(reference)
    if path.parts and path.parts[0] == "assets":
        relative = PurePosixPath(*path.parts[1:])
    else:
        relative = path
    return f"/r/{slug}/assets/{relative.as_posix()}"


def _build_sections(manifest: ReportManifest, slug: str) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "section_id": section.section_id,
            "heading": section.heading,
            "summary": section.summary,
            "spoken_text": section.spoken_text,
            "start_ms": section.start_ms,
            "end_ms": section.end_ms,
            "start": _format_ms(section.start_ms),
            "end": _format_ms(section.end_ms),
            "key_terms": list(section.key_terms),
            "audio_refs": [
                _public_asset_url(slug, reference) for reference in section.audio_refs
            ],
            "audio_status": section.audio_status.value,
            "audio_available": bool(section.audio_refs),
        }
        for section in manifest.narrative.sections
    )


def _build_terms(
    manifest: ReportManifest, slug: str, sections: tuple[dict[str, object], ...]
) -> tuple[dict[str, object], ...]:
    headings = {section["section_id"]: section["heading"] for section in sections}
    return tuple(
        {
            "term": term.term,
            "ipa": term.ipa,
            "pronunciation_note": term.pronunciation_note,
            "part_of_speech": term.part_of_speech,
            "definition_zh": term.definition_zh,
            "definition_en": term.definition_en,
            "context_sentence": term.context_sentence,
            "why_it_matters": term.why_it_matters,
            "category": term.category.value,
            "category_label": CATEGORY_LABELS.get(
                term.category.value, term.category.value
            ),
            "section_id": term.section_id,
            "section_heading": headings.get(term.section_id, ""),
            "audio_ref": _public_asset_url(slug, term.audio_ref),
            "audio_source": term.audio_source.value,
            "audio_available": term.audio_ref != "unavailable",
        }
        for term in manifest.terms
    )


def load_public_report(
    store: ReportStore,
    repository: ReportRepository,
    slug: str,
) -> PublicReport:
    bundle = repository.get_current_bundle(slug, include_unpublished=True)
    if bundle is None:
        raise ReportNotFound(slug)
    if bundle.report.status != "published":
        raise ReportGone(slug)
    version_prefix = bundle.version.object_prefix
    try:
        manifest = ReportManifest.model_validate_json(
            store.read_manifest(version_prefix).decode("utf-8")
        )
    except (ObjectStoreError, UnicodeDecodeError, ValueError) as exc:
        raise ReportNotFound(slug) from exc

    sections = _build_sections(manifest, slug)
    terms = _build_terms(manifest, slug, sections)
    return PublicReport(
        record=bundle.report,
        version_prefix=version_prefix,
        title=manifest.narrative.title,
        logline=manifest.narrative.logline,
        background=manifest.narrative.background,
        duration_min=round(manifest.source.duration_ms / 60_000, 1),
        sections=sections,
        terms=terms,
        attribution=(
            "Oxford Learner's Dictionaries",
            "Youdao Dictionary",
            "小米 MiMo TTS",
        ),
    )


@lru_cache(maxsize=1)
def _environment() -> Environment:
    template_dir = Path(__file__).resolve().parent / "templates"
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_report(report: PublicReport) -> str:
    template = _environment().get_template("report.html.j2")
    return template.render(report=report, page_title=report.title, page="report")


def render_chapter(report: PublicReport, section_id: str) -> str:
    section = report.section(section_id)
    template = _environment().get_template("chapter.html.j2")
    return template.render(
        report=report,
        section=section,
        page_title=str(section["heading"]),
        page="chapter",
    )


def render_vocabulary(
    report: PublicReport,
    *,
    section_filter: str | None = None,
    category_filter: str | None = None,
    query: str | None = None,
) -> str:
    terms = list(report.terms)
    if section_filter:
        terms = [term for term in terms if term["section_id"] == section_filter]
    if category_filter:
        terms = [term for term in terms if term["category"] == category_filter]
    if query:
        needle = query.casefold()
        terms = [
            term
            for term in terms
            if needle in " ".join(
                str(term[key])
                for key in ("term", "definition_zh", "definition_en", "context_sentence")
            ).casefold()
        ]
    template = _environment().get_template("vocabulary.html.j2")
    return template.render(
        report=report,
        terms=terms,
        sections=report.sections,
        categories=sorted(CATEGORY_LABELS.items(), key=lambda item: item[1]),
        selected_section=section_filter or "",
        selected_category=category_filter or "",
        query=query or "",
        page_title="词表",
        page="vocabulary",
    )
