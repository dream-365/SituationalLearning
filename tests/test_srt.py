from __future__ import annotations

from pathlib import Path

import pytest

from situlearn.srt import SubtitleParseError, parse_srt


def test_parse_bom_crlf_and_multiline(tmp_path: Path) -> None:
    content = (
        "﻿1\r\n"
        "00:00:01,000 --> 00:00:03,000\r\n"
        "This may look like an ordinary door in\r\n"
        "Florence, but it isn't.\r\n"
        "\r\n"
        "2\r\n"
        "00:00:04,000 --> 00:00:06,000\r\n"
        "<i>Look</i> at the detail.\r\n"
    )
    path = tmp_path / "sample.srt"
    path.write_bytes(content.encode("utf-8"))

    cues = parse_srt(path)

    assert [cue.cue_id for cue in cues] == [1, 2]
    assert cues[0].text == "This may look like an ordinary door in Florence, but it isn't."
    assert cues[1].text == "Look at the detail."
    assert cues[0].start_ms == 1_000
    assert cues[0].end_ms == 3_000


def test_rejects_empty_file(tmp_path: Path) -> None:
    path = tmp_path / "empty.srt"
    path.write_bytes(b"")

    with pytest.raises(SubtitleParseError):
        parse_srt(path)


def test_rejects_block_without_timestamp(tmp_path: Path) -> None:
    path = tmp_path / "broken.srt"
    path.write_text("1\nnot a timestamp\nhello\n", encoding="utf-8")

    with pytest.raises(SubtitleParseError):
        parse_srt(path)


def test_real_sample_if_present() -> None:
    sample = Path("samples/renaissance-unchained-p01.en.srt")
    if not sample.exists():
        pytest.skip("local sample not present")

    cues = parse_srt(sample)

    assert len(cues) == 1_186
    assert cues[0].start_ms == 10_450
    assert cues[-1].end_ms == 3_594_830
