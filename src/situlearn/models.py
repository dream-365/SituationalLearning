"""Core data models shared across the pipeline."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Cue(BaseModel):
    """A single subtitle cue normalized from an .srt file."""

    cue_id: int = Field(ge=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_time_range(self) -> Cue:
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be less than end_ms")
        return self


class Segment(BaseModel):
    """A sentence or paragraph built from one or more cues."""

    segment_id: str = Field(min_length=1)
    cue_ids: list[int] = Field(min_length=1)
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_time_range(self) -> Segment:
        if self.start_ms >= self.end_ms:
            raise ValueError("start_ms must be less than end_ms")
        return self
