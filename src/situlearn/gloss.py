"""Generate bilingual glosses and merge them with dictionary data."""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from pydantic import AliasChoices, BaseModel, Field, ValidationError, field_validator

from situlearn.content import ContentProfile, profile_for
from situlearn.dictionary import DictionaryEntry
from situlearn.knowledge import AudioSource, SourceRef, TermCandidate, TermEntry
from situlearn.llm import invoke_with_retry, structured_output
from situlearn.prompts import prompts_for


class TermGloss(BaseModel):
    """Lenient transport model for raw LLM output.

    Length constraints are enforced when building ``TermEntry``, per item, so a
    single bad gloss cannot discard the whole batch.
    """

    term: str | None = None
    definition_zh: str | None = None
    definition_en: str | None = None
    part_of_speech: str | None = None
    pronunciation_note: str | None = None


class TermGlosses(BaseModel):
    glosses: list[TermGloss] = Field(
        default_factory=list,
        validation_alias=AliasChoices("glosses", "items"),
    )

    @field_validator("glosses", mode="before")
    @classmethod
    def _drop_malformed_entries(cls, value: object) -> object:
        if isinstance(value, dict):
            value = [value]
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, (dict, TermGloss))]


def gloss_terms(
    llm: ChatDeepSeek,
    terms: list[TermCandidate],
    dictionary: dict[str, DictionaryEntry],
    *,
    profile: ContentProfile | None = None,
) -> list[TermEntry]:
    """Ask the model for contextual bilingual glosses, then merge dictionary data."""

    profile = profile or profile_for()
    prompt_set = prompts_for(profile.content_type)
    payload = []
    for term in terms:
        entry = dictionary.get(term.lemma.casefold()) or dictionary.get(term.term.casefold())
        payload.append(
            {
                "term": term.term,
                "context_sentence": term.context_sentence,
                "dictionary_en": entry.definition_en if entry else "",
                "category": term.category.value,
            }
        )

    prompt = ChatPromptTemplate.from_messages(
        [("system", prompt_set.gloss_system), ("user", prompt_set.gloss_user)]
    )
    chain = prompt | structured_output(llm, TermGlosses)
    result = invoke_with_retry(chain, {"terms_json": json.dumps(payload, ensure_ascii=False)})
    by_term = {
        gloss.term.casefold(): gloss for gloss in result.glosses if gloss.term
    }

    entries: list[TermEntry] = []
    for term in terms:
        gloss = by_term.get(term.term.casefold()) or by_term.get(term.lemma.casefold())
        if gloss is None:
            continue
        entry = dictionary.get(term.lemma.casefold()) or dictionary.get(term.term.casefold())
        has_ipa = bool(entry and entry.phonetic)
        if has_ipa:
            pronunciation_note = None
        elif entry is not None and entry.audio_url:
            pronunciation_note = "词典提供真人发音，未提供音标"
        else:
            pronunciation_note = _text(gloss.pronunciation_note) or "词典未收录，使用 TTS 发音"

        definition_zh = _text(gloss.definition_zh)[:300]
        definition_en = (
            (entry.definition_en if entry and entry.definition_en else _text(gloss.definition_en))[:300]
        )
        if len(definition_zh) < 10 or len(definition_en) < 10:
            continue

        part_of_speech = (
            entry.part_of_speech
            if entry and entry.part_of_speech != "unknown"
            else _text(gloss.part_of_speech) or "unknown"
        )
        try:
            entries.append(
                TermEntry(
                    term=term.term,
                    ipa=entry.phonetic if entry else None,
                    pronunciation_note=pronunciation_note,
                    part_of_speech=part_of_speech,
                    definition_zh=definition_zh,
                    definition_en=definition_en,
                    audio_ref="unavailable",
                    audio_source=AudioSource.UNAVAILABLE,
                    context_sentence=term.context_sentence,
                    why_it_matters=term.why_it_matters,
                    section_id=term.section_id,
                    category=term.category,
                    sources=(
                        [
                            SourceRef(
                                name="Wiktionary via dictionaryapi.dev",
                                url=entry.source_url,
                            )
                        ]
                        if entry
                        else []
                    ),
                )
            )
        except ValidationError:
            continue

    return entries


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""
