from __future__ import annotations

import pytest

import situlearn.gloss as gloss_module
from situlearn.gloss import TermGlosses, gloss_terms
from situlearn.knowledge import TermCandidate, TermCategory


def _candidate(term: str) -> TermCandidate:
    return TermCandidate(
        term=term,
        lemma=term,
        surface_forms=[term],
        category=TermCategory.PROPER_NOUN,
        cue_ids=[1],
        context_sentence=f"The biographer {term} wrote about the court.",
        section_id="sec-01",
        why_it_matters="这是理解后文引用来源的关键人名。",
        confidence=0.9,
    )


def test_non_dict_glosses_are_dropped_without_failing() -> None:
    result = TermGlosses.model_validate({"glosses": ["Zosimus", None]})

    assert result.glosses == []


def test_one_bad_gloss_does_not_discard_the_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    result = TermGlosses.model_validate(
        {
            "glosses": [
                {
                    "term": "Zosimus",
                    "definition_zh": "拜占庭史学家，片中引用他关于宫廷的记述。",
                    "definition_en": "A Byzantine historian cited in the documentary.",
                    "part_of_speech": "proper noun",
                },
                {
                    "term": "Plotinus",
                    "definition_zh": "短",
                    "definition_en": "A philosopher.",
                    "part_of_speech": "proper noun",
                },
            ]
        }
    )
    monkeypatch.setattr(
        gloss_module,
        "structured_output",
        lambda llm, schema: (lambda payload: result),
    )

    entries = gloss_terms(
        object(),
        [_candidate("Zosimus"), _candidate("Plotinus")],
        {},
    )

    assert [entry.term for entry in entries] == ["Zosimus"]
