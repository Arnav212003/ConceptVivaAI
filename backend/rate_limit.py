"""Sliding-window rate limiting: Redis-backed (shared by all API instances) with an
in-process fallback.

Redis algorithm (sliding log, one sorted set per key, no Lua needed):
  MULTI
    ZREMRANGEBYSCORE key 0 (now - window)    drop hits outside the window
    ZADD key now <unique member>             record this hit
    ZCARD key                                count hits in the window
    PEXPIRE key window                       let idle keys disappear
  EXEC
If the count exceeds the limit the hit is removed again, so rejected requests do
not consume quota. MULTI/EXEC makes the four steps atomic per request.

Failure policy: if Redis is unreachable we fall back to the per-process limiter
(fail-open to a weaker limit, never fail-closed for every user) and count the event.
"""
from __future__ import annotations

import os
import secrets
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from config import settings
from observability import RATE_LIMITED, get_logger, log_event
from redis_client import get_redis

logger = get_logger("rate_limit")

# Number of reverse proxies in front of the API whose X-Forwarded-For entries are
# trusted (Render / Railway = 1). 0 means trust only the socket peer.
TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS", "0"))


class SlidingWindowLimiter:
    """In-process limiter used for local development and as the Redis fallback."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int = 60) -> int:
        """Record a hit and return 0 if allowed, else seconds until a slot frees."""
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            queue = self._hits[key]
            while queue and queue[0] <= cutoff:
                queue.popleft()
            if len(queue) >= limit:
                return max(1, int(window_seconds - (now - queue[0])))
            queue.append(now)
            return 0

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        retry_after = self.hit(key, limit, window_seconds)
        if retry_after:
            raise _too_many(retry_after)


class RedisSlidingWindowLimiter:
    def __init__(self, redis, prefix: str = "cv:rl:"):
        self.redis = redis
        self.prefix = prefix

    def hit(self, key: str, limit: int, window_seconds: int = 60) -> int:
        redis_key = self.prefix + key
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        member = f"{now_ms}-{secrets.token_hex(4)}"

        pipe = self.redis.pipeline(transaction=True)
        pipe.zremrangebyscore(redis_key, 0, now_ms - window_ms)
        pipe.zadd(redis_key, {member: now_ms})
        pipe.zcard(redis_key)
        pipe.pexpire(redis_key, window_ms)
        _, _, count, _ = pipe.execute()

        if count <= limit:
            return 0
        self.redis.zrem(redis_key, member)
        oldest = self.redis.zrange(redis_key, 0, 0, withscores=True)
        if not oldest:
            return 1
        return max(1, int((oldest[0][1] + window_ms - now_ms) / 1000) + 1)


def _too_many(retry_after: int) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail=f"Too many requests. Try again in about {retry_after} seconds.",
        headers={"Retry-After": str(retry_after)},
    )


_limiter = SlidingWindowLimiter()

AI_REQUESTS_PER_MINUTE = settings.ai_requests_per_minute
GENERAL_REQUESTS_PER_MINUTE = settings.general_requests_per_minute
SESSION_STARTS_PER_MINUTE = settings.session_starts_per_minute


def _client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    if TRUSTED_PROXY_HOPS <= 0:
        return peer
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    # The last N entries were appended by our own proxies; the one before is the client.
    if len(forwarded) >= TRUSTED_PROXY_HOPS:
        return forwarded[-TRUSTED_PROXY_HOPS]
    return peer


def _bucket_key(request: Request, bucket: str, session_id: str) -> tuple[str, int]:
    if bucket == "session_start":
        return f"session:{_client_ip(request)}", SESSION_STARTS_PER_MINUTE
    identity = session_id or _client_ip(request)
    if bucket in ("ai", "judge"):
        return f"{bucket}:{identity}", AI_REQUESTS_PER_MINUTE
    return f"general:{identity}", GENERAL_REQUESTS_PER_MINUTE


def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    session_id: str = "",
) -> None:
    if settings.disable_rate_limiting:
        return

    key, limit = _bucket_key(request, bucket, session_id)
    limit = max(1, limit)
    redis = get_redis()
    retry_after = 0
    if redis is not None:
        try:
            retry_after = RedisSlidingWindowLimiter(redis).hit(key, limit, 60)
        except Exception:
            RATE_LIMITED.labels("redis_unavailable_fallback").inc()
            log_event(logger, "rate_limit_redis_fallback", level=30, bucket=bucket)
            retry_after = _limiter.hit(key, limit, 60)
    else:
        retry_after = _limiter.hit(key, limit, 60)

    if retry_after:
        RATE_LIMITED.labels(bucket).inc()
        raise _too_many(retry_after)
