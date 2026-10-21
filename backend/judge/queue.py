"""Redis-backed judge job queue (reliable-queue pattern).

Keys
  cv:judge:queue            LIST  submission ids waiting for a worker
  cv:judge:processing       LIST  ids a worker has claimed (LMOVE from queue)
  cv:judge:sub:<id>         HASH  status, owner session, payload, result, timestamps
  cv:judge:heartbeat        STRING set by live workers with a short TTL

A worker claims a job atomically with BLMOVE queue -> processing. If a worker dies
mid-job, `recover_stale` moves the job back to the queue after the visibility
timeout (at most MAX_ATTEMPTS times). The solution source is deleted from Redis as
soon as a verdict is stored, and every submission hash expires after RETENTION_SECONDS.
"""
from __future__ import annotations

import json
import secrets
import time
from typing import Optional

QUEUE_KEY = "cv:judge:queue"
PROCESSING_KEY = "cv:judge:processing"
HEARTBEAT_KEY = "cv:judge:heartbeat"
SUBMISSION_PREFIX = "cv:judge:sub:"

RETENTION_SECONDS = 60 * 60
HEARTBEAT_TTL_SECONDS = 30
MAX_ATTEMPTS = 2
MAX_QUEUE_LENGTH = 500

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_FINISHED = "finished"
STATUS_ERROR = "error"


class QueueFullError(RuntimeError):
    pass


def submission_key(submission_id: str) -> str:
    return f"{SUBMISSION_PREFIX}{submission_id}"


def enqueue(redis, *, session_id: str, question_id: str, runner: dict, solution: str) -> str:
    if redis.llen(QUEUE_KEY) >= MAX_QUEUE_LENGTH:
        raise QueueFullError("judge queue is full")
    submission_id = "sub_" + secrets.token_hex(12)
    key = submission_key(submission_id)
    pipe = redis.pipeline()
    pipe.hset(key, mapping={
        "status": STATUS_QUEUED,
        "session_id": session_id,
        "question_id": question_id,
        "payload": json.dumps({"runner": runner, "solution": solution}),
        "total_tests": len(runner.get("tests", [])),
        "attempts": 0,
        "created_at": time.time(),
    })
    pipe.expire(key, RETENTION_SECONDS)
    pipe.lpush(QUEUE_KEY, submission_id)
    pipe.execute()
    return submission_id


def claim(redis, block_seconds: float = 5.0) -> Optional[str]:
    if block_seconds > 0:
        return redis.blmove(QUEUE_KEY, PROCESSING_KEY, block_seconds, "RIGHT", "LEFT")
    return redis.lmove(QUEUE_KEY, PROCESSING_KEY, "RIGHT", "LEFT")


def load_job(redis, submission_id: str) -> Optional[dict]:
    data = redis.hgetall(submission_key(submission_id))
    if not data or "payload" not in data:
        return None
    redis.hset(submission_key(submission_id), mapping={
        "status": STATUS_RUNNING,
        "started_at": time.time(),
        "attempts": int(data.get("attempts", 0)) + 1,
    })
    return {
        "submission_id": submission_id,
        "total_tests": int(data.get("total_tests", 0)),
        **json.loads(data["payload"]),
    }


def complete(redis, submission_id: str, result: dict) -> None:
    key = submission_key(submission_id)
    pipe = redis.pipeline()
    pipe.hset(key, mapping={
        "status": STATUS_FINISHED if result.get("status") == "finished" else STATUS_ERROR,
        "result": json.dumps(result),
        "finished_at": time.time(),
    })
    pipe.hdel(key, "payload")  # do not keep submitted code longer than needed
    pipe.expire(key, RETENTION_SECONDS)
    pipe.lrem(PROCESSING_KEY, 1, submission_id)
    pipe.execute()


def get_submission(redis, submission_id: str) -> Optional[dict]:
    data = redis.hgetall(submission_key(submission_id))
    if not data:
        return None
    result = json.loads(data["result"]) if data.get("result") else None
    return {
        "submission_id": submission_id,
        "status": data.get("status", STATUS_QUEUED),
        "session_id": data.get("session_id", ""),
        "question_id": data.get("question_id", ""),
        "created_at": float(data.get("created_at", 0) or 0),
        "finished_at": float(data.get("finished_at", 0) or 0),
        "result": result,
    }


def recover_stale(redis, visibility_timeout: float) -> int:
    """Requeue jobs whose worker vanished. Returns how many were recovered or failed."""
    recovered = 0
    now = time.time()
    for submission_id in redis.lrange(PROCESSING_KEY, 0, -1):
        data = redis.hgetall(submission_key(submission_id))
        started = float(data.get("started_at", 0) or 0) if data else 0
        if data and data.get("status") == STATUS_RUNNING and now - started < visibility_timeout:
            continue
        redis.lrem(PROCESSING_KEY, 1, submission_id)
        recovered += 1
        if not data or "payload" not in data:
            continue
        if int(data.get("attempts", 0)) >= MAX_ATTEMPTS:
            complete(redis, submission_id, {
                "status": "error", "verdict": "Internal Error", "passed": 0,
                "total": int(data.get("total_tests", 0)), "test_cases": [],
                "error": "Judge worker stopped repeatedly while running this submission.",
            })
        else:
            redis.hset(submission_key(submission_id), "status", STATUS_QUEUED)
            redis.rpush(QUEUE_KEY, submission_id)
    return recovered


def beat(redis, worker_id: str) -> None:
    redis.set(HEARTBEAT_KEY, worker_id, ex=HEARTBEAT_TTL_SECONDS)


def worker_alive(redis) -> bool:
    return bool(redis.exists(HEARTBEAT_KEY))
