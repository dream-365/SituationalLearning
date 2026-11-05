"""Server-side rendering of public document reports."""

from __future__ import annotations

from dataclasses import dataclass

from situlearn.document import (
    Document,
    Section,
    SectionRole,
    WordBlock,
    iter_blocks,
)
from situlearn.render import render_document_html
from situlearn.web.objectstore import ObjectStoreError
from situlearn.web.repository import ReportRecord, ReportRepository
from situlearn.web.storage import ReportStore


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
    document: Document

    @property
    def slug(self) -> str:
        return self.record.slug

    @property
    def title(self) -> str:
        return self.document.meta.title

    @property
    def logline(self) -> str:
        return self.document.meta.subtitle or ""

    @property
    def background(self) -> str:
        return self.document.meta.description or ""

    @property
    def labels(self) -> dict[str, str]:
        return dict(self.document.meta.labels)

    @property
    def duration_min(self) -> float:
        source = self.document.meta.source
        if source and source.duration_ms:
            return round(source.duration_ms / 60_000, 1)
        return 0.0

    def section(self, section_id: str) -> Section:
        for section in self.document.sections:
            if section.id == section_id:
                return section
        raise SectionNotFound(section_id)


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
        document = Document.model_validate_json(
            store.read_document(version_prefix).decode("utf-8")
        )
    except (ObjectStoreError, UnicodeDecodeError, ValueError) as exc:
        raise ReportNotFound(slug) from exc
    return PublicReport(
        record=bundle.report,
        version_prefix=version_prefix,
        document=document,
    )


def _manifest_url(report: PublicReport) -> str:
    return f"/r/{report.slug}/manifest.webmanifest"


def _public_document(document: Document, slug: str) -> Document:
    """Point resource hrefs at the public /r/<slug>/media/ route.

    Documents store hrefs relative to their own root (``media/...``) so they
    work offline. A public page lives at ``/r/<slug>`` without a trailing
    slash, so relative hrefs would resolve to ``/r/media/...``.
    """

    resources = {
        resource_id: resource.model_copy(update={"href": f"/r/{slug}/{resource.href}"})
        for resource_id, resource in document.resources.items()
    }
    return document.model_copy(update={"resources": resources})


def render_report(report: PublicReport) -> str:
    return render_document_html(
        _public_document(report.document, report.slug),
        pwa_manifest_url=_manifest_url(report),
    )


def render_chapter(report: PublicReport, section_id: str) -> str:
    section = report.section(section_id)
    document = report.document.model_copy(update={"sections": [section]})
    return render_document_html(
        _public_document(document, report.slug),
        pwa_manifest_url=_manifest_url(report),
    )


def _word_blocks(document: Document) -> list[WordBlock]:
    return [
        block
        for section in document.sections
        for block in iter_blocks(section.blocks)
        if isinstance(block, WordBlock)
    ]


def render_vocabulary(
    report: PublicReport,
    *,
    section_filter: str | None = None,
    category_filter: str | None = None,
    query: str | None = None,
) -> str:
    words = _word_blocks(report.document)
    if section_filter:
        words = [word for word in words if word.section_id == section_filter]
    if category_filter:
        words = [word for word in words if word.category == category_filter]
    if query:
        needle = query.casefold()
        words = [
            word
            for word in words
            if needle
            in " ".join(
                [
                    word.term,
                    *word.definitions.values(),
                    word.context or "",
                ]
            ).casefold()
        ]

    vocabulary = next(
        (
            section
            for section in report.document.sections
            if section.role is SectionRole.VOCABULARY
        ),
        None,
    )
    if vocabulary is None:
        document = report.document.model_copy(update={"sections": []})
    else:
        filtered = vocabulary.model_copy(update={"blocks": words})
        document = report.document.model_copy(update={"sections": [filtered]})
    return render_document_html(
        _public_document(document, report.slug),
        pwa_manifest_url=_manifest_url(report),
    )
