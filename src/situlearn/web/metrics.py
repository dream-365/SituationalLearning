"""In-process Prometheus-style metrics for the web service."""

from __future__ import annotations

import threading
from collections import defaultdict


class Metrics:
    """Counters and a latency summary for a single service process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._http_requests: dict[tuple[str, int], int] = defaultdict(int)
        self._duration_sum = 0.0
        self._duration_count = 0
        self._publish: dict[str, int] = defaultdict(int)

    def observe_http(self, method: str, status: int, duration_seconds: float) -> None:
        with self._lock:
            self._http_requests[(method, status)] += 1
            self._duration_sum += max(0.0, duration_seconds)
            self._duration_count += 1

    def record_publish(self, result: str) -> None:
        with self._lock:
            self._publish[result] += 1

    def render(self, *, report_count: int, storage_bytes: int) -> str:
        with self._lock:
            requests = sorted(self._http_requests.items())
            publish = sorted(self._publish.items())
            duration_sum = self._duration_sum
            duration_count = self._duration_count

        lines = [
            "# HELP http_requests_total HTTP requests by method and status.",
            "# TYPE http_requests_total counter",
        ]
        for (method, status), count in requests:
            lines.append(
                f'http_requests_total{{method="{method}",status="{status}"}} {count}'
            )

        lines.extend(
            [
                "# HELP http_request_duration_seconds Request latency summary.",
                "# TYPE http_request_duration_seconds summary",
                f"http_request_duration_seconds_sum {duration_sum:.6f}",
                f"http_request_duration_seconds_count {duration_count}",
                "# HELP publish_total Publish attempts by result.",
                "# TYPE publish_total counter",
            ]
        )
        for result, count in publish:
            lines.append(f'publish_total{{result="{result}"}} {count}')

        lines.extend(
            [
                "# HELP report_count Published reports.",
                "# TYPE report_count gauge",
                f"report_count {report_count}",
                "# HELP storage_bytes Current published report bytes.",
                "# TYPE storage_bytes gauge",
                f"storage_bytes {storage_bytes}",
            ]
        )
        return "\n".join(lines) + "\n"
