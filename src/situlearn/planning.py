"""Intermediate models for narrative planning and term extraction."""

from __future__ import annotations

import math
import re

from pydantic import BaseModel, Field, field_validator

from situlearn.knowledge import (
    AudioStatus,
    NarrativeScript,
    NarrativeSection,
    TermCandidate,
    TermCategory,
)
from situlearn.models import Segment


class PlannedSection(BaseModel):
    """Lenient transport model for one planned narrative section.

    Prose lengths are prompt guidance, not schema integrity: a summary a few
    characters under target must not abort a multi-minute build. Values are
    trimmed and clamped to the canonical maxima in ``to_narrative_script``.
    """

    heading: str | None = None
    summary: str | None = None
    spoken_text: str | None = None
    segment_ids: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)

    @field_validator("segment_ids", "key_terms", mode="before")
    @classmethod
    def _keep_strings(cls, value: object) -> object:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
        return []


class PlannedNarrative(BaseModel):
    title: str | None = None
    logline: str | None = None
    background: str | None = None
    sections: list[PlannedSection] = Field(min_length=4, max_length=12)

    @field_validator("sections", mode="before")
    @classmethod
    def _drop_malformed_sections(cls, value: object) -> object:
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, (dict, PlannedSection))]


class ExtractedTerm(BaseModel):
    """Lenient transport model for raw LLM output.

    Field constraints are intentionally loose. A single out-of-range value must
    not fail the whole extraction run, so canonical constraints live in
    ``TermCandidate`` and are enforced after normalisation in
    ``to_term_candidates``.
    """

    term: str | None = None
    lemma: str | None = None
    surface_forms: list[str] | None = None
    category: str | None = None
    context_sentence: str | None = None
    segment_id: str | None = None
    why_it_matters: str | None = None
    confidence: float | str | None = None

    @field_validator("surface_forms", mode="before")
    @classmethod
    def _wrap_single_form(cls, value: object) -> object:
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [form for form in value if isinstance(form, str)]
        return []


class ExtractedTerms(BaseModel):
    terms: list[ExtractedTerm] = Field(default_factory=list)

    @field_validator("terms", mode="before")
    @classmethod
    def _drop_malformed_entries(cls, value: object) -> object:
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, (dict, ExtractedTerm))]


def to_narrative_script(planned: PlannedNarrative, segments: list[Segment]) -> NarrativeScript:
    """Resolve segment references into timestamps and section ids.

    Prose is trimmed and clamped to the canonical maxima here. Short prose is
    kept as-is: the prompt asks for 150/80 characters, but a near miss is
    usable content and must not fail the build.
    """

    index = {segment.segment_id: segment for segment in segments}
    sections: list[NarrativeSection] = []

    for ordinal, item in enumerate(planned.sections, start=1):
        selected = [
            index[segment_id]
            for segment_id in dict.fromkeys(item.segment_ids)
            if segment_id in index
        ]
        if not selected:
            continue
        heading = _clamp(item.heading, 20) or f"第{ordinal}节"
        spoken_text = _clamp(item.spoken_text, 1_200)
        summary = _clamp(item.summary, 300)
        if not spoken_text:
            spoken_text = summary
        if not summary:
            summary = _clamp(spoken_text, 300) or heading
        if not spoken_text:
            spoken_text = heading
        sections.append(
            NarrativeSection(
                section_id=f"sec-{ordinal:02d}",
                heading=heading,
                start_ms=min(segment.start_ms for segment in selected),
                end_ms=max(segment.end_ms for segment in selected),
                summary=summary,
                key_terms=_key_terms(item.key_terms),
                spoken_text=spoken_text,
                audio_refs=[],
                audio_status=AudioStatus.UNAVAILABLE,
            )
        )

    title = _clamp(planned.title, 30) or "学习报告"
    logline = _clamp(planned.logline, 120) or title
    return NarrativeScript(
        title=title,
        logline=logline,
        background=_clamp(planned.background, 600) or logline,
        sections=sections,
    )


def _clamp(value: str | None, limit: int) -> str:
    text = " ".join(value.split()) if isinstance(value, str) else ""
    return text[:limit]


def _key_terms(value: list[str]) -> list[str]:
    terms = [term.strip() for term in value if term.strip()]
    return list(dict.fromkeys(terms))[:12]


def to_term_candidates(
    extracted: ExtractedTerms,
    segments: list[Segment],
    script: NarrativeScript,
) -> list[TermCandidate]:
    """Map extracted terms to cues and sections, de-duplicating by lemma.

    Items that cannot be normalised into a valid ``TermCandidate`` are dropped
    individually instead of failing the whole batch.
    """

    segment_index = {segment.segment_id: segment for segment in segments}
    section_spans = [(section.section_id, section.start_ms, section.end_ms) for section in script.sections]
    seen: set[str] = set()
    candidates: list[TermCandidate] = []

    for item in extracted.terms:
        term = _text(item.term)
        lemma = _text(item.lemma) or term
        segment_id = _text(item.segment_id)
        if not term or not lemma or segment_id not in segment_index:
            continue
        key = lemma.casefold()
        if key in seen:
            continue

        segment = segment_index[segment_id]
        context = _context_in_segment(_text(item.context_sentence), term, segment.text)
        why_it_matters = _text(item.why_it_matters)[:120]
        if len(context) < 10 or len(why_it_matters) < 15:
            continue

        seen.add(key)
        candidates.append(
            TermCandidate(
                term=term,
                lemma=lemma,
                surface_forms=_surface_forms(item.surface_forms, term),
                category=_category(item.category),
                cue_ids=segment.cue_ids,
                context_sentence=context,
                section_id=_section_for(segment.start_ms, section_spans),
                why_it_matters=why_it_matters,
                confidence=_confidence(item.confidence),
            )
        )

    return candidates


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def _surface_forms(value: list[str] | None, term: str) -> list[str]:
    forms = [form.strip() for form in value or [] if isinstance(form, str) and form.strip()]
    return forms or [term]


def _category(value: str | None) -> TermCategory:
    try:
        return TermCategory(_text(value).casefold())
    except ValueError:
        return TermCategory.COMMON_ADVANCED


def _confidence(value: object) -> float:
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            return 0.5
    if not isinstance(value, (int, float)) or math.isnan(value):
        return 0.5
    return min(max(float(value), 0.0), 1.0)


def _section_for(start_ms: int, spans: list[tuple[str, int, int]]) -> str:
    for section_id, section_start, section_end in spans:
        if section_start <= start_ms <= section_end:
            return section_id
    return spans[0][0] if spans else "sec-01"


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?…])\s+")


def _context_in_segment(sentence: str, term: str, segment_text: str) -> str:
    """Return a quote that exists in the segment and is usable as context.

    The model sometimes emits a fragment such as ``"Zosimus."``. Rather than
    rejecting the term, expand the fragment to the sentence (and, if needed,
    neighbouring sentences) that contains it.
    """

    cleaned = " ".join(sentence.split())[:300]
    if len(cleaned) >= 10 and cleaned in segment_text:
        return cleaned

    sentences = [
        part.strip() for part in SENTENCE_SPLIT_RE.split(segment_text.strip()) if part.strip()
    ]
    pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
    for index, candidate in enumerate(sentences):
        if not pattern.search(candidate):
            continue
        start = end = index
        context = candidate
        while len(context) < 10 and (start > 0 or end < len(sentences) - 1):
            if start > 0:
                start -= 1
                context = f"{sentences[start]} {context}"
            if len(context) < 10 and end < len(sentences) - 1:
                end += 1
                context = f"{context} {sentences[end]}"
        return context[:300]

    fallback = " ".join(segment_text.split())[:300]
    return fallback if len(fallback) >= 10 else ""
