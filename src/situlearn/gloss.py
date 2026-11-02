"""Generate bilingual glosses and merge them with dictionary data."""

from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_deepseek import ChatDeepSeek
from pydantic import AliasChoices, BaseModel, Field

from situlearn.dictionary import DictionaryEntry
from situlearn.knowledge import AudioSource, SourceRef, TermCandidate, TermEntry
from situlearn.llm import structured_output
from situlearn.prompts import GLOSS_SYSTEM, GLOSS_USER


class TermGloss(BaseModel):
    term: str = Field(min_length=1)
    definition_zh: str = Field(min_length=10, max_length=300)
    definition_en: str = Field(min_length=10, max_length=300)
    part_of_speech: str = Field(min_length=1)
    pronunciation_note: str | None = None


class TermGlosses(BaseModel):
    glosses: list[TermGloss] = Field(
        min_length=1,
        validation_alias=AliasChoices("glosses", "items"),
    )


def gloss_terms(
    llm: ChatDeepSeek,
    terms: list[TermCandidate],
    dictionary: dict[str, DictionaryEntry],
) -> list[TermEntry]:
    """Ask the model for contextual bilingual glosses, then merge dictionary data."""

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
        [("system", GLOSS_SYSTEM), ("user", GLOSS_USER)]
    )
    chain = prompt | structured_output(llm, TermGlosses)
    result = chain.invoke({"terms_json": json.dumps(payload, ensure_ascii=False)})
    by_term = {gloss.term.casefold(): gloss for gloss in result.glosses}

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
            pronunciation_note = gloss.pronunciation_note or "词典未收录，使用 TTS 发音"

        entries.append(
            TermEntry(
                term=term.term,
                ipa=entry.phonetic if entry else None,
                pronunciation_note=pronunciation_note,
                part_of_speech=(
                    entry.part_of_speech
                    if entry and entry.part_of_speech != "unknown"
                    else gloss.part_of_speech
                ),
                definition_zh=gloss.definition_zh,
                definition_en=(
                    entry.definition_en
                    if entry and entry.definition_en
                    else gloss.definition_en
                ),
                audio_ref="unavailable",
                audio_source=AudioSource.UNAVAILABLE,
                context_sentence=term.context_sentence,
                why_it_matters=term.why_it_matters,
                section_id=term.section_id,
                category=term.category,
                sources=[
                    SourceRef(
                        name="Wiktionary via dictionaryapi.dev" if entry else "DeepSeek 语境释义",
                        url=entry.source_url if entry else "https://api.deepseek.com",
                    )
                ],
            )
        )

    return entries
