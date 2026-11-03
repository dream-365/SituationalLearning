"""Models for the narrative, vocabulary, audio assets, and report manifest."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, model_validator


class ContentType(StrEnum):
    DOCUMENTARY = "documentary"
    MOVIE = "movie"


class AudioStatus(StrEnum):
    READY = "ready"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class TermCategory(StrEnum):
    DOMAIN_TERM = "domain_term"
    PROPER_NOUN = "proper_noun"
    WORK_TITLE = "work_title"
    SCHOOL_GENRE = "school_genre"
    COMMON_ADVANCED = "common_advanced"


class AudioSource(StrEnum):
    DICTIONARY = "dictionary"
    TTS = "tts"
    UNAVAILABLE = "unavailable"


class SourceRef(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl


class NarrativeSection(BaseModel):
    # Prose length ranges live in the prompt as quality targets. The schema
    # only rejects empty/oversized text so a near miss stays renderable.
    section_id: str = Field(min_length=1)
    heading: str = Field(min_length=1, max_length=20)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    summary: str = Field(min_length=1, max_length=300)
    key_terms: list[str] = Field(default_factory=list, max_length=12)
    spoken_text: str = Field(min_length=1)
    audio_refs: list[str] = Field(default_factory=list)
    audio_status: AudioStatus = AudioStatus.UNAVAILABLE

    @model_validator(mode="after")
    def _validate(self) -> NarrativeSection:
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be less than end_ms")
        if self.audio_status is AudioStatus.READY and not self.audio_refs:
            raise ValueError("ready sections must have at least one audio_ref")
        return self


class NarrativeScript(BaseModel):
    title: str = Field(min_length=1, max_length=30)
    logline: str = Field(min_length=1, max_length=120)
    background: str = Field(min_length=1, max_length=600)
    # 4-12 is the union of content-type profiles (documentary 4-8, movie
    # 6-12). The pipeline validates against the active profile.
    sections: list[NarrativeSection] = Field(min_length=4, max_length=12)

    @model_validator(mode="after")
    def _sections_are_ordered(self) -> NarrativeScript:
        starts = [section.start_ms for section in self.sections]
        if starts != sorted(starts):
            raise ValueError("narrative sections must be ordered by start_ms")
        return self


class TermCandidate(BaseModel):
    term: str = Field(min_length=1)
    lemma: str = Field(min_length=1)
    surface_forms: list[str] = Field(min_length=1)
    category: TermCategory
    cue_ids: list[int] = Field(min_length=1)
    context_sentence: str = Field(min_length=10, max_length=300)
    section_id: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=15, max_length=120)
    confidence: float = Field(ge=0.0, le=1.0)


class TermEntry(BaseModel):
    term: str = Field(min_length=1)
    ipa: str | None = None
    pronunciation_note: str | None = None
    part_of_speech: str = Field(min_length=1)
    definition_zh: str = Field(min_length=10, max_length=300)
    definition_en: str = Field(min_length=10, max_length=300)
    audio_ref: str = "unavailable"
    audio_source: AudioSource = AudioSource.UNAVAILABLE
    context_sentence: str = Field(min_length=10, max_length=300)
    why_it_matters: str = Field(min_length=15, max_length=120)
    section_id: str = Field(min_length=1)
    category: TermCategory
    sources: list[SourceRef] = Field(min_length=1)


class AudioAsset(BaseModel):
    asset_id: str = Field(min_length=1)
    path: str = Field(min_length=1)
    duration_ms: int = Field(ge=0)
    text_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: AudioSource


class SourceInfo(BaseModel):
    filename: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    duration_ms: int = Field(ge=0)
    cue_count: int = Field(ge=1)


class ReportManifest(BaseModel):
    schema_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    source: SourceInfo
    config: dict[str, object]
    narrative: NarrativeScript
    terms: list[TermEntry] = Field(min_length=1)
    assets: list[AudioAsset] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
