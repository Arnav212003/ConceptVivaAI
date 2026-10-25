"""Judge worker process: `python -m judge.worker`.

Runs separately from the API (its own container in docker-compose). It claims jobs
from Redis, sends them to the configured isolated executor, turns the outcome into
a verdict and stores the result. Scale horizontally by running more workers.
"""
from __future__ import annotations

import asyncio
import json
import os
import signal
import socket
import time

from config import settings
from judge import queue
from judge.executors import default_limits, get_executor
from judge.verdicts import build_judge_result
from observability import JUDGE_LATENCY, JUDGE_VERDICTS, configure_logging, get_logger, log_event
from redis_client import get_redis

logger = get_logger("judge.worker")


class Worker:
    def __init__(self, redis, executor, limits=None, worker_id: str | None = None):
        self.redis = redis
        self.executor = executor
        self.limits = limits or default_limits()
        self.worker_id = worker_id or f"{socket.gethostname()}-{os.getpid()}"
        self.running = True
        self.visibility_timeout = self.limits.wall_seconds + 60

    def process(self, submission_id: str) -> dict | None:
        job = queue.load_job(self.redis, submission_id)
        if job is None:
            self.redis.lrem(queue.PROCESSING_KEY, 1, submission_id)
            return None
        stdin_payload = json.dumps({"runner": job["runner"], "solution": job["solution"]})
        outcome = asyncio.run(self.executor.execute(stdin_payload, self.limits))
        result = build_judge_result(outcome, job["total_tests"], reveal_all=bool(job.get("reveal_all")))
        result["submission_id"] = submission_id
        result["executor"] = self.executor.name
        queue.complete(self.redis, submission_id, result)

        JUDGE_VERDICTS.labels(result["verdict"]).inc()
        created = queue.get_submission(self.redis, submission_id)
        if created and created["created_at"]:
            JUDGE_LATENCY.observe(max(0.0, time.time() - created["created_at"]))
        log_event(logger, "judged", submission_id=submission_id, verdict=result["verdict"],
                  passed=result["passed"], total=result["total"], executor=self.executor.name,
                  duration_ms=result.get("duration_ms"))
        return result

    def process_one(self, block_seconds: float = queue.CLAIM_BLOCK_SECONDS) -> dict | None:
        queue.beat(self.redis, self.worker_id)
        submission_id = queue.claim(self.redis, block_seconds)
        if submission_id is None:
            return None
        return self.process(submission_id)

    def run_forever(self) -> None:
        log_event(logger, "worker_started", worker_id=self.worker_id, executor=self.executor.name)
        last_recovery = 0.0
        while self.running:
            if time.monotonic() - last_recovery > 30:
                recovered = queue.recover_stale(self.redis, self.visibility_timeout)
                if recovered:
                    log_event(logger, "recovered_stale_jobs", count=recovered)
                last_recovery = time.monotonic()
            try:
                self.process_one()
            except Exception:  # keep the worker alive; the job is recovered later
                logger.exception("job_failed")
                time.sleep(1)
        log_event(logger, "worker_stopped", worker_id=self.worker_id)

    def stop(self, *_args) -> None:
        self.running = False


def main() -> None:
    configure_logging()
    redis = get_redis()
    if redis is None:
        raise SystemExit("REDIS_URL is required for the judge worker.")
    worker = Worker(redis, get_executor())
    signal.signal(signal.SIGTERM, worker.stop)
    signal.signal(signal.SIGINT, worker.stop)
    if not settings.judge_enabled:
        log_event(logger, "judge_disabled_in_api", level=30,
                  note="JUDGE_ENABLED=false: the API will not send jobs to this worker.")
    worker.run_forever()


if __name__ == "__main__":
    main()
