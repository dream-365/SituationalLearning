from __future__ import annotations

from situlearn.models import Cue
from situlearn.segmenter import segment_cues


def cue(cue_id: int, start_ms: int, end_ms: int, text: str) -> Cue:
    return Cue(cue_id=cue_id, start_ms=start_ms, end_ms=end_ms, text=text)


def test_merges_cues_that_split_a_sentence() -> None:
    cues = [
        cue(1, 10_450, 12_750, "This may look like an ordinary door in"),
        cue(2, 12_830, 15_550, "Florence, but it isn't."),
        cue(3, 17_300, 19_550, "The man who lived here invented the"),
        cue(4, 19_600, 22_000, "modern idea of the artist."),
    ]

    segments = segment_cues(cues)

    assert len(segments) == 1
    assert segments[0].cue_ids == [1, 2, 3, 4]
    assert segments[0].text.startswith("This may look like an ordinary door in Florence")
    assert segments[0].end_ms == 22_000


def test_splits_on_large_gap() -> None:
    cues = [
        cue(1, 0, 1_000, "First sentence."),
        cue(2, 10_000, 11_000, "Second sentence."),
    ]

    segments = segment_cues(cues, max_gap_ms=2_000)

    assert [segment.cue_ids for segment in segments] == [[1], [2]]


def test_covers_every_cue_exactly_once() -> None:
    cues = [
        cue(1, 0, 1_000, "A"),
        cue(2, 1_100, 2_000, "B"),
        cue(3, 2_100, 3_000, "C"),
    ]

    segments = segment_cues(cues)
    covered = [cue_id for segment in segments for cue_id in segment.cue_ids]

    assert covered == [1, 2, 3]
