"""Merge cues into complete sentences, then group sentences into segments."""

from __future__ import annotations

import hashlib
import itertools
import re
from dataclasses import dataclass, field

from situlearn.models import Cue, Segment

SENTENCE_END_RE = re.compile(r"[.!?…](?:[\"'’”)\]]*)$")
ABBREVIATIONS = {
    "mr.",
    "mrs.",
    "ms.",
    "dr.",
    "st.",
    "vs.",
    "etc.",
    "e.g.",
    "i.e.",
    "no.",
}


@dataclass
class _Span:
    cue_ids: list[int] = field(default_factory=list)
    start_ms: int = 0
    end_ms: int = 0
    text: str = ""

    def append(self, cue: Cue) -> None:
        self.cue_ids.append(cue.cue_id)
        self.end_ms = cue.end_ms
        self.text = f"{self.text} {cue.text}".strip()

    def absorb(self, other: _Span) -> None:
        self.cue_ids.extend(other.cue_ids)
        self.end_ms = other.end_ms
        self.text = f"{self.text} {other.text}".strip()


def _ends_sentence(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    last_token = stripped.split()[-1].lower()
    if last_token in ABBREVIATIONS:
        return False
    return bool(SENTENCE_END_RE.search(stripped))


def _starts_new_sentence(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    first = stripped[0]
    return first.isupper() or first in "\"'‘“(["


def _merge_cues_into_sentences(cues: list[Cue], max_gap_ms: int) -> list[_Span]:
    sentences: list[_Span] = []
    current = _Span([cues[0].cue_id], cues[0].start_ms, cues[0].end_ms, cues[0].text)

    for previous, cue in itertools.pairwise(cues):
        gap_ms = cue.start_ms - previous.end_ms
        boundary = _ends_sentence(current.text) and (
            _starts_new_sentence(cue.text) or gap_ms > max_gap_ms
        )
        if boundary:
            sentences.append(current)
            current = _Span([cue.cue_id], cue.start_ms, cue.end_ms, cue.text)
        else:
            current.append(cue)

    sentences.append(current)
    return sentences


def _group_sentences(
    sentences: list[_Span],
    *,
    max_gap_ms: int,
    max_chars: int,
    max_duration_ms: int,
) -> list[_Span]:
    segments: list[_Span] = []
    current = sentences[0]

    for previous, sentence in itertools.pairwise(sentences):
        gap_ms = sentence.start_ms - previous.end_ms
        too_long = len(current.text) + 1 + len(sentence.text) > max_chars
        too_slow = sentence.end_ms - current.start_ms > max_duration_ms
        if gap_ms > max_gap_ms or too_long or too_slow:
            segments.append(current)
            current = sentence
        else:
            current.absorb(sentence)

    segments.append(current)
    return segments


def _to_segment(ordinal: int, span: _Span) -> Segment:
    digest = hashlib.sha256(
        f"{span.start_ms}:{span.end_ms}:{span.text}".encode()
    ).hexdigest()[:16]
    return Segment(
        segment_id=f"seg-{ordinal:04d}-{digest}",
        cue_ids=span.cue_ids,
        start_ms=span.start_ms,
        end_ms=span.end_ms,
        text=span.text,
    )


def segment_cues(
    cues: list[Cue],
    *,
    max_gap_ms: int = 2_000,
    max_chars: int = 1_200,
    max_duration_ms: int = 60_000,
) -> list[Segment]:
    """Return semantic segments that cover every cue exactly once."""

    if not cues:
        return []

    sentences = _merge_cues_into_sentences(cues, max_gap_ms=max_gap_ms)
    spans = _group_sentences(
        sentences,
        max_gap_ms=max_gap_ms,
        max_chars=max_chars,
        max_duration_ms=max_duration_ms,
    )
    segments = [_to_segment(ordinal, span) for ordinal, span in enumerate(spans, start=1)]

    covered = [cue_id for segment in segments for cue_id in segment.cue_ids]
    expected = [cue.cue_id for cue in cues]
    if covered != expected:
        raise ValueError("segmenter must cover every cue exactly once, in order")
    return segments
