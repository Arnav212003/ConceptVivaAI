"""Redis queue + worker behaviour (fakeredis, local executor)."""
import time

import pytest

from judge import queue
from judge.executors import Judge0Executor, LocalExecutor, judge0_outcome
from judge.process_runner import Limits
from judge.sandbox_server import _clamp, verify_signature
from judge.signing import sign_sandbox_request
from judge.worker import Worker
from services.dsa_bank import get_dsa_question_by_title
from tests.test_judge_harness import TWO_SUM_OK

LIMITS = Limits(cpu_seconds=2, wall_seconds=4, memory_mb=256)


def enqueue_two_sum(redis, solution=TWO_SUM_OK, session_id="cv_owner"):
    question = get_dsa_question_by_title("Two Sum")
    return queue.enqueue(redis, session_id=session_id, question_id=question["id"],
                         runner=question["runner"], solution=solution)


def test_worker_processes_job_and_deletes_source(fake_redis):
    submission_id = enqueue_two_sum(fake_redis)
    worker = Worker(fake_redis, LocalExecutor(), LIMITS, worker_id="test-worker")

    result = worker.process_one(block_seconds=0)

    assert result["verdict"] == "Accepted"
    stored = queue.get_submission(fake_redis, submission_id)
    assert stored["status"] == queue.STATUS_FINISHED
    assert stored["result"]["passed"] == 3
    assert "payload" not in fake_redis.hgetall(queue.submission_key(submission_id))
    assert fake_redis.llen(queue.PROCESSING_KEY) == 0
    assert queue.worker_alive(fake_redis)


def test_empty_queue_returns_none(fake_redis):
    worker = Worker(fake_redis, LocalExecutor(), LIMITS)
    assert worker.process_one(block_seconds=0) is None


def test_queue_backpressure(fake_redis, monkeypatch):
    monkeypatch.setattr(queue, "MAX_QUEUE_LENGTH", 2)
    enqueue_two_sum(fake_redis)
    enqueue_two_sum(fake_redis)
    with pytest.raises(queue.QueueFullError):
        enqueue_two_sum(fake_redis)


def test_stale_job_is_requeued_then_failed_after_max_attempts(fake_redis):
    submission_id = enqueue_two_sum(fake_redis)
    for attempt in range(queue.MAX_ATTEMPTS):
        claimed = queue.claim(fake_redis, 0)
        assert claimed == submission_id
        queue.load_job(fake_redis, submission_id)  # worker "crashes" here
        fake_redis.hset(queue.submission_key(submission_id), "started_at", time.time() - 999)
        assert queue.recover_stale(fake_redis, visibility_timeout=60) == 1

    stored = queue.get_submission(fake_redis, submission_id)
    assert stored["status"] == queue.STATUS_ERROR
    assert stored["result"]["verdict"] == "Internal Error"


def test_running_job_within_visibility_is_not_recovered(fake_redis):
    submission_id = enqueue_two_sum(fake_redis)
    queue.claim(fake_redis, 0)
    queue.load_job(fake_redis, submission_id)
    assert queue.recover_stale(fake_redis, visibility_timeout=60) == 0


def test_judge0_status_mapping():
    def data(status_id, stdout="", memory=0):
        import base64
        return {"status": {"id": status_id}, "stdout": base64.b64encode(stdout.encode()).decode(),
                "time": "0.1", "memory": memory}

    assert judge0_outcome(data(3, "__CV_RESULT__{}"), LIMITS).status == "ok"
    assert judge0_outcome(data(5), LIMITS).status == "timeout"
    assert judge0_outcome(data(8), LIMITS).status == "output_limit"
    assert judge0_outcome(data(11, memory=LIMITS.memory_mb * 1024), LIMITS).status == "memory"
    assert judge0_outcome(data(13), LIMITS).status == "internal_error"


def test_judge0_submission_disables_network_and_sets_limits():
    body = Judge0Executor("http://judge0:2358").submission_body("{}", LIMITS)
    assert body["enable_network"] is False
    assert body["memory_limit"] == LIMITS.memory_mb * 1024
    assert body["cpu_time_limit"] == LIMITS.cpu_seconds
    assert body["max_processes_and_or_threads"] == LIMITS.max_processes


def test_sandbox_signature_rejects_tampering_and_replay():
    body = b'{"stdin": "{}"}'
    now = 1_700_000_000
    signature = sign_sandbox_request("secret", str(now), body)
    assert verify_signature("secret", str(now), signature, body, now=now)
    assert not verify_signature("secret", str(now), signature, body + b" ", now=now)
    assert not verify_signature("other", str(now), signature, body, now=now)
    assert not verify_signature("secret", str(now), signature, body, now=now + 3600)
    assert not verify_signature("", str(now), signature, body, now=now)


def test_sandbox_clamps_requested_limits():
    limits = _clamp({"cpu_seconds": 999, "memory_mb": 99999, "wall_seconds": "bad"})
    assert limits.cpu_seconds <= 4
    assert limits.memory_mb <= 512
    assert limits.wall_seconds <= 10


def fake_judge0(monkeypatch, responses):
    import base64
    import httpx

    seen = []

    def handler(request):
        seen.append(request)
        status_id = responses.pop(0)
        stdout = base64.b64encode(b'__CV_RESULT__{"phase": "tests", "results": []}').decode()
        return httpx.Response(200, json={"token": "t1", "status": {"id": status_id}, "stdout": stdout, "time": "0.1"})

    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))
    return seen


def test_judge0_uses_one_request_with_rapidapi_headers(monkeypatch):
    import asyncio

    seen = fake_judge0(monkeypatch, [3])
    executor = Judge0Executor("https://judge0-ce.p.rapidapi.com", "key123")
    outcome = asyncio.run(executor.execute("{}", LIMITS))
    assert outcome.status == "ok"
    assert len(seen) == 1
    assert seen[0].url.params["wait"] == "true"
    assert seen[0].headers["X-RapidAPI-Key"] == "key123"
    assert seen[0].headers["X-RapidAPI-Host"] == "judge0-ce.p.rapidapi.com"


def test_judge0_polls_only_while_still_processing(monkeypatch):
    import asyncio

    seen = fake_judge0(monkeypatch, [2, 3])
    outcome = asyncio.run(Judge0Executor("http://judge0:2358", "tok").execute("{}", LIMITS))
    assert outcome.status == "ok"
    assert [r.method for r in seen] == ["POST", "GET"]
    assert seen[0].headers["X-Auth-Token"] == "tok"


def test_judge0_daily_limit_stops_requests(monkeypatch, fake_redis, override_settings):
    import asyncio

    override_settings(judge0_daily_limit=2)
    seen = fake_judge0(monkeypatch, [3, 3, 3])
    executor = Judge0Executor("https://judge0-ce.p.rapidapi.com", "key")
    results = [asyncio.run(executor.execute("{}", LIMITS)) for _ in range(3)]
    assert [r.status for r in results] == ["ok", "ok", "internal_error"]
    assert "daily request limit" in results[2].detail
    assert len(seen) == 2


def test_judge_offline_when_judge0_budget_is_used_up(fake_redis, override_settings):
    from judge import client as judge_client
    from judge.executors import judge0_calls_key

    override_settings(judge_enabled=True, judge_executor="judge0", judge0_url="https://judge0-ce.p.rapidapi.com",
                      judge0_daily_limit=2)
    fake_redis.set("cv:judge:heartbeat", "w", ex=30)
    judge_client.reset_availability_cache()
    assert judge_client.judge_available() is True
    fake_redis.set(judge0_calls_key(), 2)
    judge_client.reset_availability_cache()
    assert judge_client.judge_available() is False
    judge_client.reset_availability_cache()


def test_idle_claim_returns_none_without_socket_timeout(fake_redis):
    import redis

    from redis_client import SOCKET_TIMEOUT_SECONDS

    class SocketTimeoutRedis:
        def set(self, *args, **kwargs):
            pass

        def blmove(self, src, dst, timeout, *args):
            if timeout >= SOCKET_TIMEOUT_SECONDS:
                raise redis.exceptions.TimeoutError("Timeout reading from socket")
            return None

    assert queue.CLAIM_BLOCK_SECONDS < SOCKET_TIMEOUT_SECONDS
    assert Worker(SocketTimeoutRedis(), LocalExecutor(), LIMITS).process_one() is None
    assert queue.claim(fake_redis) is None
