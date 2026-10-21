"""Small JSON cache for reusable, non-personal generated content.

Safe-to-cache rule: only content that is a pure function of public inputs, such as a
Hindi translation of a given text or the statement of a curated bank question.
User-specific evaluations, scores and anything containing a session id are never cached.
Keys are SHA-256 hashes so raw user text never appears in Redis key names.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

from observability import CACHE_EVENTS
from redis_client import get_redis

_MAX_MEMORY_ITEMS = 2000


class _MemoryCache:
    def __init__(self):
        self._items: OrderedDict[str, tuple[float, str]] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[str]:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires_at, value = item
            if expires_at < time.monotonic():
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            self._items[key] = (time.monotonic() + ttl_seconds, value)
            self._items.move_to_end(key)
            while len(self._items) > _MAX_MEMORY_ITEMS:
                self._items.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


_memory = _MemoryCache()


def make_key(namespace: str, *parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]
    return f"cv:cache:{namespace}:{digest}"


def cache_get(namespace: str, key: str) -> Optional[Any]:
    raw = None
    client = get_redis()
    try:
        raw = client.get(key) if client is not None else _memory.get(key)
    except Exception:
        raw = None  # a cache outage must never break the request
    CACHE_EVENTS.labels(namespace, "hit" if raw is not None else "miss").inc()
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return None


def cache_set(namespace: str, key: str, value: Any, ttl_seconds: int) -> None:
    raw = json.dumps(value, ensure_ascii=False)
    client = get_redis()
    try:
        if client is not None:
            client.set(key, raw, ex=ttl_seconds)
        else:
            _memory.set(key, raw, ttl_seconds)
    except Exception:
        CACHE_EVENTS.labels(namespace, "write_error").inc()


def clear_memory_cache() -> None:
    _memory.clear()
