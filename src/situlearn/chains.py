"""LangChain chains for narrative planning and vocabulary extraction."""

from __future__ import annotations

import json
import re

from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from pydantic import AliasChoices, BaseModel, Field, ValidationError

from situlearn.knowledge import NarrativeScript, TermCandidate
from situlearn.llm import invoke_with_retry, structured_output
from situlearn.models import Segment
from situlearn.planning import (
    ExtractedTerms,
    PlannedNarrative,
    to_narrative_script,
    to_term_candidates,
)
from situlearn.prompts import (
    CHINESE_REPAIR_SYSTEM,
    CHINESE_REPAIR_USER,
    NARRATIVE_SYSTEM,
    NARRATIVE_USER,
    VOCAB_SYSTEM,
    VOCAB_USER,
)

LATIN_RE = re.compile(r"[A-Za-z][A-Za-z'’-]*")


class SectionTextPatch(BaseModel):
    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1, max_length=20)
    summary: str = Field(min_length=1, max_length=300)
    spoken_text: str = Field(min_length=1, max_length=1_200)


class NarrativeTextPatch(BaseModel):
    title: str = Field(min_length=1, max_length=30)
    logline: str = Field(min_length=1, max_length=120)
    background: str = Field(min_length=1, max_length=600)
    sections: list[SectionTextPatch] = Field(
        min_length=4,
        max_length=8,
        validation_alias=AliasChoices("sections", "items"),
    )


def _format_ms(value: int) -> str:
    total_seconds = value // 1_000
    return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"


def format_transcript(segments: list[Segment]) -> str:
    blocks = [
        f"[{segment.segment_id}] {_format_ms(segment.start_ms)}-{_format_ms(segment.end_ms)}\n"
        f"{segment.text}"
        for segment in segments
    ]
    return "\n\n".join(blocks)


def _format_narrative_context(script: NarrativeScript) -> str:
    lines = []
    for section in script.sections:
        lines.append(f"[{section.section_id}] {section.heading}\n{section.summary}")
    return "\n\n".join(lines)


def plan_narrative(llm: ChatDeepSeek, segments: list[Segment]) -> NarrativeScript:
    """Produce a Chinese spoken narrative from the full transcript."""

    duration_min = (segments[-1].end_ms - segments[0].start_ms) / 60_000
    prompt = ChatPromptTemplate.from_messages(
        [("system", NARRATIVE_SYSTEM), ("user", NARRATIVE_USER)]
    )
    chain = prompt | structured_output(llm, PlannedNarrative)
    planned = invoke_with_retry(
        chain,
        {
            "transcript": format_transcript(segments),
            "duration_min": duration_min,
        },
    )
    return to_narrative_script(planned, segments)


def repair_narrative_chinese(
    llm: ChatDeepSeek,
    script: NarrativeScript,
) -> NarrativeScript:
    """Rewrite any English words in the narrative prose into Chinese."""

    texts = [script.title, script.logline, script.background]
    for section in script.sections:
        texts.extend([section.heading, section.summary, section.spoken_text])
    if not any(LATIN_RE.search(text) for text in texts):
        return script

    payload = {
        "title": script.title,
        "logline": script.logline,
        "background": script.background,
        "sections": [
            {
                "section_id": section.section_id,
                "heading": section.heading,
                "summary": section.summary,
                "spoken_text": section.spoken_text,
            }
            for section in script.sections
        ],
    }
    prompt = ChatPromptTemplate.from_messages(
        [("system", CHINESE_REPAIR_SYSTEM), ("user", CHINESE_REPAIR_USER)]
    )
    chain = prompt | structured_output(llm, NarrativeTextPatch)
    try:
        patch = chain.invoke({"narrative_json": json.dumps(payload, ensure_ascii=False)})
    except (OutputParserException, ValidationError):
        return script

    by_id = {section.section_id: section for section in patch.sections}
    updated_sections = []
    for section in script.sections:
        replacement = by_id.get(section.section_id)
        if replacement is None:
            updated_sections.append(section)
        else:
            updated_sections.append(
                section.model_copy(
                    update={
                        "heading": replacement.heading,
                        "summary": replacement.summary,
                        "spoken_text": replacement.spoken_text,
                    }
                )
            )

    updated = script.model_copy(
        update={
            "title": patch.title,
            "logline": patch.logline,
            "background": patch.background,
            "sections": updated_sections,
        }
    )
    try:
        return NarrativeScript.model_validate(updated.model_dump())
    except ValidationError:
        return script


def extract_terms(
    llm: ChatDeepSeek,
    segments: list[Segment],
    script: NarrativeScript,
) -> list[TermCandidate]:
    """Extract key blocking terms from the transcript and narrative."""

    prompt = ChatPromptTemplate.from_messages(
        [("system", VOCAB_SYSTEM), ("user", VOCAB_USER)]
    )
    chain = prompt | structured_output(llm, ExtractedTerms)
    payload = {
        "narrative_context": _format_narrative_context(script),
        "transcript": format_transcript(segments),
    }
    candidates: list[TermCandidate] = []
    for _ in range(2):
        extracted = invoke_with_retry(chain, payload)
        candidates = to_term_candidates(extracted, segments, script)
        if candidates:
            break
    if not candidates:
        raise RuntimeError("术语提取没有返回可用词条，请重试或检查提示词")
    return candidates
