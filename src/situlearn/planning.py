"""Intermediate models for narrative planning and term extraction."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from situlearn.knowledge import (
    AudioStatus,
    NarrativeScript,
    NarrativeSection,
    TermCandidate,
    TermCategory,
)
from situlearn.models import Segment


class PlannedSection(BaseModel):
    heading: str = Field(min_length=4, max_length=20)
    summary: str = Field(min_length=80, max_length=300)
    spoken_text: str = Field(min_length=100, max_length=1_200)
    segment_ids: list[str] = Field(min_length=1)
    key_terms: list[str] = Field(default_factory=list, max_length=12)


class PlannedNarrative(BaseModel):
    title: str = Field(min_length=2, max_length=30)
    logline: str = Field(min_length=20, max_length=120)
    background: str = Field(min_length=150, max_length=600)
    sections: list[PlannedSection] = Field(min_length=4, max_length=8)


class ExtractedTerm(BaseModel):
    term: str = Field(min_length=1)
    lemma: str = Field(min_length=1)
    surface_forms: list[str] = Field(min_length=1)
    category: TermCategory
    context_sentence: str = Field(min_length=10, max_length=300)
    segment_id: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=15, max_length=120)
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedTerms(BaseModel):
    terms: list[ExtractedTerm] = Field(min_length=1)


def to_narrative_script(planned: PlannedNarrative, segments: list[Segment]) -> NarrativeScript:
    """Resolve segment references into timestamps and section ids."""

    index = {segment.segment_id: segment for segment in segments}
    sections: list[NarrativeSection] = []

    for ordinal, item in enumerate(planned.sections, start=1):
        missing = [segment_id for segment_id in item.segment_ids if segment_id not in index]
        if missing:
            raise ValueError(f"unknown segment ids: {missing}")
        selected = [index[segment_id] for segment_id in item.segment_ids]
        sections.append(
            NarrativeSection(
                section_id=f"sec-{ordinal:02d}",
                heading=item.heading,
                start_ms=min(segment.start_ms for segment in selected),
                end_ms=max(segment.end_ms for segment in selected),
                summary=item.summary,
                key_terms=item.key_terms,
                spoken_text=item.spoken_text,
                audio_refs=[],
                audio_status=AudioStatus.UNAVAILABLE,
            )
        )

    return NarrativeScript(
        title=planned.title,
        logline=planned.logline,
        background=planned.background,
        sections=sections,
    )


def to_term_candidates(
    extracted: ExtractedTerms,
    segments: list[Segment],
    script: NarrativeScript,
) -> list[TermCandidate]:
    """Map extracted terms to cues and sections, de-duplicating by lemma."""

    segment_index = {segment.segment_id: segment for segment in segments}
    section_spans = [(section.section_id, section.start_ms, section.end_ms) for section in script.sections]
    seen: set[str] = set()
    candidates: list[TermCandidate] = []

    for item in extracted.terms:
        key = item.lemma.casefold().strip()
        if key in seen:
            continue
        segment = segment_index.get(item.segment_id)
        if segment is None:
            continue
        seen.add(key)
        section_id = _section_for(segment.start_ms, section_spans)
        context = _context_in_segment(item.context_sentence, item.term, segment.text)
        candidates.append(
            TermCandidate(
                term=item.term,
                lemma=item.lemma,
                surface_forms=item.surface_forms,
                category=item.category,
                cue_ids=segment.cue_ids,
                context_sentence=context,
                section_id=section_id,
                why_it_matters=item.why_it_matters,
                confidence=item.confidence,
            )
        )

    return candidates


def _section_for(start_ms: int, spans: list[tuple[str, int, int]]) -> str:
    for section_id, section_start, section_end in spans:
        if section_start <= start_ms <= section_end:
            return section_id
    return spans[0][0] if spans else "sec-01"


def _context_in_segment(sentence: str, term: str, segment_text: str) -> str:
    cleaned = sentence.strip()
    if cleaned and cleaned in segment_text:
        return cleaned[:300]
    match = re.search(
        rf"[^.!?]*\b{re.escape(term)}\b[^.!?]*[.!?]?",
        segment_text,
        flags=re.IGNORECASE,
    )
    if match:
        return match.group(0).strip()[:300]
    return segment_text.strip()[:300]
