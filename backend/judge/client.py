"""Judge client used by the API process. It only enqueues jobs and reads results;
it never executes submitted code."""
from __future__ import annotations

import asyncio
import time

from fastapi.concurrency import run_in_threadpool

from config import settings
from judge import queue
from judge.executors import executor_configured
from redis_client import get_redis

_AVAILABILITY_TTL = 5.0
_availability_cache: dict = {"checked_at": 0.0, "value": False}


def judge_available() -> bool:
    """True only when the judge is enabled, an isolated executor is configured,
    Redis is reachable, and at least one worker has sent a recent heartbeat."""
    if not settings.judge_enabled:
        return False
    redis = get_redis()
    if redis is None or not executor_configured():
        return False
    now = time.monotonic()
    if now - _availability_cache["checked_at"] < _AVAILABILITY_TTL:
        return _availability_cache["value"]
    try:
        value = queue.worker_alive(redis)
    except Exception:
        value = False
    _availability_cache.update(checked_at=now, value=value)
    return value


def reset_availability_cache() -> None:
    _availability_cache.update(checked_at=0.0, value=False)


async def submit(question: dict, solution: str, *, session_id: str) -> str:
    redis = get_redis()
    return await run_in_threadpool(
        queue.enqueue,
        redis,
        session_id=session_id,
        question_id=question.get("id", ""),
        runner=question["runner"],
        solution=solution,
    )


async def get_status(submission_id: str, *, session_id: str) -> dict | None:
    submission = await run_in_threadpool(queue.get_submission, get_redis(), submission_id)
    # Submissions are private to the session that created them.
    if submission is None or submission["session_id"] != session_id:
        return None
    return submission


async def wait_for_result(submission_id: str, *, session_id: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    delay = 0.05
    while True:
        submission = await get_status(submission_id, session_id=session_id)
        if submission and submission["status"] in (queue.STATUS_FINISHED, queue.STATUS_ERROR):
            return submission["result"]
        if time.monotonic() >= deadline:
            return {"status": "pending", "submission_id": submission_id, "verdict": "Pending",
                    "passed": 0, "total": 0, "test_cases": []}
        await asyncio.sleep(delay)
        delay = min(0.25, delay * 1.5)


async def judge_and_wait(question: dict, solution: str, *, session_id: str = "") -> dict | None:
    """Enqueue and wait up to JUDGE_WAIT_SECONDS. Returns None when the judge is off."""
    if not judge_available():
        return None
    try:
        submission_id = await submit(question, solution, session_id=session_id)
    except queue.QueueFullError:
        return {"status": "error", "verdict": "Internal Error", "error": "Judge is busy. Try again shortly.",
                "passed": 0, "total": 0, "test_cases": []}
    result = await wait_for_result(submission_id, session_id=session_id, timeout=settings.judge_wait_seconds)
    result.setdefault("submission_id", submission_id)
    return result
