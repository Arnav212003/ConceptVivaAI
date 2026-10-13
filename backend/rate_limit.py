"""Small in-memory rate limiter for demo use."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds

        with self._lock:
            queue = self._hits[key]
            while queue and queue[0] <= cutoff:
                queue.popleft()

            if len(queue) >= limit:
                retry_after = max(1, int(window_seconds - (now - queue[0])))
                raise HTTPException(
                    status_code=429,
                    detail=f"Too many requests. Try again in about {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)},
                )

            queue.append(now)


_limiter = SlidingWindowLimiter()

AI_REQUESTS_PER_MINUTE = int(os.getenv("AI_REQUESTS_PER_MINUTE", "20"))
GENERAL_REQUESTS_PER_MINUTE = int(os.getenv("GENERAL_REQUESTS_PER_MINUTE", "120"))
SESSION_STARTS_PER_MINUTE = int(os.getenv("SESSION_STARTS_PER_MINUTE", "20"))


def _client_ip(request: Request) -> str:
    # Trust only the direct socket peer.
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    session_id: str = "",
) -> None:
    if os.getenv("DISABLE_RATE_LIMITING", "false").lower() == "true":
        return

    if bucket == "session_start":
        key = f"session:{_client_ip(request)}"
        limit = SESSION_STARTS_PER_MINUTE
    elif bucket == "ai":
        identity = session_id or _client_ip(request)
        key = f"ai:{identity}"
        limit = AI_REQUESTS_PER_MINUTE
    else:
        identity = session_id or _client_ip(request)
        key = f"general:{identity}"
        limit = GENERAL_REQUESTS_PER_MINUTE

    _limiter.check(key, max(1, limit), 60)
