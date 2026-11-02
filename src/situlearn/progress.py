"""Human-readable stage and item progress for long-running builds."""

from __future__ import annotations

import time
from typing import TextIO


class Progress:
    """Write timestamped progress lines, or stay silent when stream is None."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream = stream
        self._started = time.monotonic()
        self._inline_len = 0

    def stage(self, message: str) -> None:
        """Report a new stage, ending any inline counter line first."""
        self._end_line()
        self._write(f"{self._stamp} {message}")

    def counter(self, label: str, index: int, total: int) -> None:
        """Report item ``index`` of ``total`` inside the current stage."""
        if self._stream is None:
            return
        text = f"{self._stamp} {label} {index}/{total}"
        if self._stream.isatty():
            padding = " " * max(0, self._inline_len - len(text))
            self._stream.write(f"\r{text}{padding}")
            self._stream.flush()
            self._inline_len = len(text)
            return
        self._write(text)

    def finish(self) -> None:
        """End an inline counter line so later output starts on a new line."""
        self._end_line()

    @property
    def _stamp(self) -> str:
        return f"[{time.monotonic() - self._started:5.1f}s]"

    def _write(self, text: str) -> None:
        if self._stream is None:
            return
        print(text, file=self._stream, flush=True)

    def _end_line(self) -> None:
        if self._stream is None or not self._inline_len:
            return
        self._stream.write("\n")
        self._stream.flush()
        self._inline_len = 0
