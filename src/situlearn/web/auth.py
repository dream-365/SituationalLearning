"""Publish token verification and lightweight rate limiting."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request


def verify_publish_token(authorization: str | None, expected: str) -> bool:
    if not expected or not authorization:
        return False
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return False
    return hmac.compare_digest(value.strip(), expected)


def resolve_owner(authorization: str | None, settings) -> str | None:
    if not authorization:
        return None
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    token = value.strip()
    if not token:
        return None
    if settings.publish_tokens:
        for expected, owner_id in settings.publish_tokens.items():
            if hmac.compare_digest(token, expected):
                return owner_id
        return None
    if settings.publish_token and hmac.compare_digest(token, settings.publish_token):
        return settings.default_owner_id
    return None


def require_publish_token(request: Request) -> str:
    settings = request.app.state.settings
    metrics = getattr(request.app.state, "metrics", None)
    if request.method == "POST" and not settings.publish_enabled:
        if metrics is not None:
            metrics.record_publish("rejected")
        raise HTTPException(
            status_code=503,
            detail={
                "code": "ERR_PUBLISH_DISABLED",
                "message": "publishing is temporarily disabled",
            },
        )
    owner_id = resolve_owner(request.headers.get("Authorization"), settings)
    if owner_id is None:
        if metrics is not None and request.method == "POST":
            metrics.record_publish("rejected")
        raise HTTPException(
            status_code=401,
            detail={
                "code": "ERR_PUBLISH_UNAUTHORIZED",
                "message": "a valid publish token is required",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.owner_id = owner_id
    return owner_id


def hash_client_ip(ip: str, salt: str) -> str:
    return hashlib.sha256(f"{salt or 'situlearn'}:{ip}".encode()).hexdigest()


class SlidingWindowLimiter:
    """Small in-process limiter for the single-replica deployment."""

    def __init__(
        self,
        *,
        limit: int = 5,
        window_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> tuple[bool, int]:
        now = self.clock()
        cutoff = now - self.window_seconds
        events = self._events[key]
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= self.limit:
            retry_after = max(1, int(self.window_seconds - (now - events[0])))
            return False, retry_after
        events.append(now)
        return True, 0
