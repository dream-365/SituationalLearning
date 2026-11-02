from __future__ import annotations

from situlearn.knowledge import (
    AudioStatus,
    NarrativeScript,
    NarrativeSection,
    TermCategory,
)
from situlearn.models import Segment
from situlearn.planning import ExtractedTerms, to_term_candidates


def _segment() -> Segment:
    return Segment(
        segment_id="seg-0001",
        cue_ids=[1, 2],
        start_ms=0,
        end_ms=10_000,
        text=(
            "The biographer Zosimus. "
            "He lived in Constantinople and wrote about the court."
        ),
    )


def _script() -> NarrativeScript:
    sections = [
        NarrativeSection(
            section_id=f"sec-{index:02d}",
            heading=f"第{index}章节标题",
            start_ms=index * 10_000,
            end_ms=(index + 1) * 10_000,
            summary="这是本节摘要，用来测试词条映射是否落在正确章节。" * 4,
            spoken_text="这是播报稿，用来测试词条映射是否落在正确章节。" * 3,
            audio_status=AudioStatus.UNAVAILABLE,
        )
        for index in range(1, 5)
    ]
    return NarrativeScript(
        title="测试叙事",
        logline="这是一句话简介，用来测试词条映射与规范化逻辑。",
        background="这是背景说明，用来测试叙事脚本的结构是否完整。" * 8,
        sections=sections,
    )


def _term(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "term": "Zosimus",
        "lemma": "Zosimus",
        "surface_forms": ["Zosimus"],
        "category": "proper_noun",
        "context_sentence": "Zosimus.",
        "segment_id": "seg-0001",
        "why_it_matters": "这是理解后文引用来源的关键人名。",
        "confidence": 0.9,
    }
    payload.update(overrides)
    return payload


def test_short_context_is_expanded_to_the_containing_sentence() -> None:
    extracted = ExtractedTerms.model_validate({"terms": [_term()]})

    candidates = to_term_candidates(extracted, [_segment()], _script())

    assert len(candidates) == 1
    assert candidates[0].context_sentence == "The biographer Zosimus."
    assert candidates[0].section_id == "sec-01"


def test_lenient_payload_is_normalised() -> None:
    payload = _term(
        surface_forms="Zosimus",
        category="Proper_Noun",
        confidence=3.7,
    )

    extracted = ExtractedTerms.model_validate({"terms": [payload]})
    candidates = to_term_candidates(extracted, [_segment()], _script())

    assert len(candidates) == 1
    assert candidates[0].surface_forms == ["Zosimus"]
    assert candidates[0].category is TermCategory.PROPER_NOUN
    assert candidates[0].confidence == 1.0


def test_malformed_confidence_and_forms_do_not_fail() -> None:
    extracted = ExtractedTerms.model_validate(
        {"terms": [_term(confidence="high", surface_forms=["Zosimus", 42])]}
    )

    candidates = to_term_candidates(extracted, [_segment()], _script())

    assert len(candidates) == 1
    assert candidates[0].confidence == 0.5
    assert candidates[0].surface_forms == ["Zosimus"]


def test_unknown_category_falls_back_instead_of_failing() -> None:
    extracted = ExtractedTerms.model_validate(
        {"terms": [_term(category="idiomatic_expression")]}
    )

    candidates = to_term_candidates(extracted, [_segment()], _script())

    assert len(candidates) == 1
    assert candidates[0].category is TermCategory.COMMON_ADVANCED


def test_unusable_terms_are_skipped_individually() -> None:
    extracted = ExtractedTerms.model_validate(
        {
            "terms": [
                _term(term=None),
                _term(term="Plotinus", segment_id="seg-9999"),
                _term(term="Aurelius", why_it_matters="太短"),
                _term(),
            ]
        }
    )

    candidates = to_term_candidates(extracted, [_segment()], _script())

    assert [candidate.term for candidate in candidates] == ["Zosimus"]


def test_non_dict_entries_are_dropped_without_failing() -> None:
    extracted = ExtractedTerms.model_validate(
        {"terms": ["Zosimus", None, _term()]}
    )

    candidates = to_term_candidates(extracted, [_segment()], _script())

    assert [candidate.term for candidate in candidates] == ["Zosimus"]


def test_duplicate_lemmas_keep_the_first_item() -> None:
    extracted = ExtractedTerms.model_validate(
        {"terms": [_term(), _term(term="Zosimus of Tyre", confidence=0.4)]}
    )

    candidates = to_term_candidates(extracted, [_segment()], _script())

    assert len(candidates) == 1
    assert candidates[0].term == "Zosimus"
