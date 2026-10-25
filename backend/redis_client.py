"""Shared Redis connection.

`REDIS_URL` unset means single-process mode: rate limiting and caching fall back to
in-memory implementations, and the code judge is unavailable (it needs a queue
shared with a separate worker process). Tests inject fakeredis via `set_redis`.
"""
from __future__ import annotations

from typing import Optional

from config import settings

SOCKET_TIMEOUT_SECONDS = 2

_client = None
_initialized = False


def get_redis():
    global _client, _initialized
    if not _initialized:
        _initialized = True
        if settings.redis_url:
            import redis

            _client = redis.Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=SOCKET_TIMEOUT_SECONDS,
                socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
                health_check_interval=30,
            )
    return _client


def set_redis(client: Optional[object]) -> None:
    global _client, _initialized
    _client = client
    _initialized = True
