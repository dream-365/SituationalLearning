"""Render an offline HTML study report from the manifest."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from situlearn.knowledge import ReportManifest

CATEGORY_LABELS = {
    "domain_term": "领域术语",
    "proper_noun": "专名",
    "work_title": "作品名",
    "school_genre": "流派/时期",
    "common_advanced": "低频普通词",
}


def _format_ms(value: int) -> str:
    total_seconds = value // 1_000
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def _template_dir() -> Path:
    return Path(__file__).resolve().parent / "templates"


def assemble_report(manifest: ReportManifest, out_dir: Path) -> Path:
    """Write report.html and return its path."""

    out_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=FileSystemLoader(_template_dir()),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")

    sections = [
        {
            "section_id": section.section_id,
            "heading": section.heading,
            "start": _format_ms(section.start_ms),
            "end": _format_ms(section.end_ms),
            "summary": section.summary,
            "spoken_text": section.spoken_text,
            "key_terms": section.key_terms,
            "audio_refs": section.audio_refs,
            "audio_status": section.audio_status.value,
        }
        for section in manifest.narrative.sections
    ]
    terms = [
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
            "category_label": CATEGORY_LABELS.get(term.category.value, term.category.value),
            "audio_ref": term.audio_ref,
            "section_id": term.section_id,
        }
        for term in manifest.terms
    ]

    html = template.render(
        title=manifest.narrative.title,
        logline=manifest.narrative.logline,
        background=manifest.narrative.background,
        sections=sections,
        terms=terms,
        duration_min=round(manifest.source.duration_ms / 60_000, 1),
        cue_count=manifest.source.cue_count,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        source_filename=manifest.source.filename,
    )

    destination = out_dir / "report.html"
    destination.write_text(html, encoding="utf-8")
    return destination
