"""Server-side storage for AI-generated practice problems.

The browser only ever receives an opaque `practice_problem_id`. The validated tests,
signature and reference solution stay here, bound to the session that generated the
problem and expiring after PROBLEM_TTL_SECONDS. Run/Submit load the tests from this
store; any tests or execution settings sent by the browser are ignored.
"""
from __future__ import annotations

import json
import secrets
import threading
import time
from typing import Optional

from redis_client import get_redis

PROBLEM_TTL_SECONDS = 6 * 60 * 60
_PREFIX = "cv:aiq:"
_ID_LENGTH = 24

_memory: dict[str, tuple[float, str]] = {}
_lock = threading.Lock()


def new_problem_id() -> str:
    return "aip_" + secrets.token_hex(_ID_LENGTH // 2)


def valid_problem_id(value: str) -> bool:
    return isinstance(value, str) and len(value) == 4 + _ID_LENGTH and value.startswith("aip_") and \
        all(c in "0123456789abcdef" for c in value[4:])


def save_problem(problem_id: str, owner: str, data: dict) -> None:
    raw = json.dumps({"owner": owner, "created_at": time.time(), **data})
    redis = get_redis()
    if redis is not None:
        redis.set(_PREFIX + problem_id, raw, ex=PROBLEM_TTL_SECONDS)
        return
    with _lock:
        _memory[problem_id] = (time.monotonic() + PROBLEM_TTL_SECONDS, raw)
        for key in [k for k, (expires, _) in _memory.items() if expires < time.monotonic()]:
            _memory.pop(key, None)


def load_problem(problem_id: str, owner: str) -> Optional[dict]:
    """Return the problem only for the session that generated it."""
    if not valid_problem_id(problem_id):
        return None
    redis = get_redis()
    raw = None
    if redis is not None:
        raw = redis.get(_PREFIX + problem_id)
    else:
        with _lock:
            item = _memory.get(problem_id)
            if item and item[0] >= time.monotonic():
                raw = item[1]
    if not raw:
        return None
    data = json.loads(raw)
    if data.get("owner") != owner:
        return None
    return data


def clear_memory_store() -> None:
    with _lock:
        _memory.clear()
