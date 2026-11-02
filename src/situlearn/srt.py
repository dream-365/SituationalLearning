"""Parse single-language English .srt files into normalized cues."""

from __future__ import annotations

import re
from pathlib import Path

from situlearn.models import Cue


class SubtitleParseError(ValueError):
    """Raised when an .srt file cannot be parsed safely."""


TIMESTAMP_RE = re.compile(
    r"(?P<sh>\d{1,2}):(?P<sm>\d{2}):(?P<ss>\d{2})[,.](?P<sms>\d{3})"
    r"\s*-->\s*"
    r"(?P<eh>\d{1,2}):(?P<em>\d{2}):(?P<es>\d{2})[,.](?P<ems>\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>|\{[^}]+\}")
ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5", "latin-1")


def _decode(raw: bytes) -> str:
    for encoding in ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise SubtitleParseError("unable to decode subtitle file")


def _to_ms(hours: str, minutes: str, seconds: str, millis: str) -> int:
    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(millis)


def parse_srt(path: str | Path) -> list[Cue]:
    """Parse an .srt file into a contiguous list of cues.

    Handles UTF-8 with or without BOM, CRLF/LF, multi-line cue text, and
    subtitle lines that split a sentence across cues.
    """

    raw = Path(path).read_bytes()
    if not raw.strip():
        raise SubtitleParseError("subtitle file is empty")

    text = _decode(raw).replace("\r\n", "\n").replace("\r", "\n")
    blocks = re.split(r"\n\s*\n", text.strip())
    cues: list[Cue] = []

    for block_number, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue

        timestamp_index = -1
        match: re.Match[str] | None = None
        for index, line in enumerate(lines):
            match = TIMESTAMP_RE.search(line)
            if match is not None:
                timestamp_index = index
                break

        if match is None or timestamp_index < 0:
            raise SubtitleParseError(f"block {block_number}: missing timestamp line")

        body = " ".join(lines[timestamp_index + 1 :]).strip()
        body = TAG_RE.sub("", body).strip()
        if not body:
            continue

        start_ms = _to_ms(match["sh"], match["sm"], match["ss"], match["sms"])
        end_ms = _to_ms(match["eh"], match["em"], match["es"], match["ems"])
        if start_ms >= end_ms:
            raise SubtitleParseError(f"block {block_number}: start_ms is not before end_ms")

        cues.append(
            Cue(
                cue_id=len(cues) + 1,
                start_ms=start_ms,
                end_ms=end_ms,
                text=body,
            )
        )

    if not cues:
        raise SubtitleParseError("no cues found")
    return cues
