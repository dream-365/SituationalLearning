"""Small, thread-safe rate limiting and retry helpers."""

from __future__ import annotations

import random
import threading
import time


class IntervalLimiter:
    """Ensure a minimum interval between requests to one host."""

    def __init__(self, interval_s: float) -> None:
        if interval_s < 0:
            raise ValueError("interval_s must be non-negative")
        self.interval = interval_s
        self._lock = threading.Lock()
        self._next = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next - now)
            self._next = max(now, self._next) + self.interval
        if delay > 0:
            time.sleep(delay)


def backoff_delay(
    attempt: int,
    *,
    base: float = 0.4,
    max_delay: float = 5.0,
    retry_after: str | None = None,
) -> float:
    """Return an exponential backoff with jitter, honoring Retry-After seconds."""

    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except ValueError:
            pass
    return min(max_delay, base * (2**attempt)) + random.uniform(0, 0.2)
