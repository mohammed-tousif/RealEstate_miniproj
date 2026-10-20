"""In-process sliding-window rate limits (per client per minute): the AI endpoint, and failed logins.

Fine for a single-instance deployment; several instances would need a shared store such as Redis.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def client_key(request: Request, user_id: str | None) -> str:
    if user_id:
        return f"user:{user_id}"
    if get_settings().trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return "ip:" + fwd.split(",")[0].strip()
    return "ip:" + (request.client.host if request.client else "unknown")


def check(key: str, limit: int | None = None, record: bool = True,
          what: str = "assistant requests") -> None:
    """Raise 429 when `key` already has `limit` hits in the last minute; otherwise record this hit."""
    limit = limit or get_settings().ai_rate_limit_per_minute
    now = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            retry = int(60 - (now - q[0])) + 1
            raise AppError(429, "rate_limited", f"Too many {what}. Try again in {retry} seconds.",
                           [{"field": None, "issue": f"limit {limit} per minute"}])
        if record:
            q.append(now)


def hit(key: str) -> None:
    with _lock:
        _hits[key].append(time.monotonic())


def reset() -> None:
    with _lock:
        _hits.clear()
