"""Distributed (Redis) and in-process rate limiting."""
import fakeredis
import pytest
from fastapi import HTTPException
from starlette.requests import Request

import rate_limit
from rate_limit import RedisSlidingWindowLimiter, SlidingWindowLimiter


def make_request(peer="10.0.0.1", forwarded=""):
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": (peer, 1234), "method": "GET", "path": "/"})


def test_redis_limiter_allows_up_to_limit_then_blocks():
    limiter = RedisSlidingWindowLimiter(fakeredis.FakeRedis(decode_responses=True))
    assert [limiter.hit("k", 3, 60) for _ in range(3)] == [0, 0, 0]
    retry_after = limiter.hit("k", 3, 60)
    assert 1 <= retry_after <= 61


def test_rejected_hits_do_not_consume_quota():
    redis = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisSlidingWindowLimiter(redis)
    for _ in range(2):
        limiter.hit("k", 2, 60)
    for _ in range(5):
        assert limiter.hit("k", 2, 60) > 0
    assert redis.zcard("cv:rl:k") == 2


def test_limit_is_shared_across_api_instances():
    shared = fakeredis.FakeRedis(decode_responses=True)
    instance_a, instance_b = RedisSlidingWindowLimiter(shared), RedisSlidingWindowLimiter(shared)
    assert instance_a.hit("user", 2, 60) == 0
    assert instance_b.hit("user", 2, 60) == 0
    # A third request on either instance is rejected: the window is global.
    assert instance_a.hit("user", 2, 60) > 0


def test_window_slides(monkeypatch):
    redis = fakeredis.FakeRedis(decode_responses=True)
    limiter = RedisSlidingWindowLimiter(redis)
    clock = [1_000.0]
    monkeypatch.setattr(rate_limit.time, "time", lambda: clock[0])
    assert limiter.hit("k", 1, 60) == 0
    assert limiter.hit("k", 1, 60) > 0
    clock[0] += 61
    assert limiter.hit("k", 1, 60) == 0


def test_memory_limiter_still_works():
    limiter = SlidingWindowLimiter()
    limiter.check("k", 1)
    with pytest.raises(HTTPException) as exc:
        limiter.check("k", 1)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_enforce_uses_redis_and_falls_back_when_it_fails(override_settings, fake_redis, monkeypatch):
    override_settings(disable_rate_limiting=False)
    monkeypatch.setattr(rate_limit, "AI_REQUESTS_PER_MINUTE", 1)
    request = make_request()
    rate_limit.enforce_rate_limit(request, bucket="ai", session_id="cv_a")
    with pytest.raises(HTTPException):
        rate_limit.enforce_rate_limit(request, bucket="ai", session_id="cv_a")
    assert fake_redis.zcard("cv:rl:ai:cv_a") == 1

    class BrokenRedis:
        def pipeline(self, **_):
            raise ConnectionError("redis down")

    from redis_client import set_redis

    set_redis(BrokenRedis())
    monkeypatch.setattr(rate_limit, "_limiter", SlidingWindowLimiter())
    rate_limit.enforce_rate_limit(request, bucket="ai", session_id="cv_b")  # fallback allows
    with pytest.raises(HTTPException):
        rate_limit.enforce_rate_limit(request, bucket="ai", session_id="cv_b")


def test_client_ip_uses_trusted_proxy_hops(monkeypatch):
    monkeypatch.setattr(rate_limit, "TRUSTED_PROXY_HOPS", 0)
    assert rate_limit._client_ip(make_request("10.0.0.1", "1.2.3.4")) == "10.0.0.1"

    monkeypatch.setattr(rate_limit, "TRUSTED_PROXY_HOPS", 1)
    assert rate_limit._client_ip(make_request("10.0.0.1", "1.2.3.4")) == "1.2.3.4"
    # A client cannot spoof its IP by prepending fake entries.
    assert rate_limit._client_ip(make_request("10.0.0.1", "6.6.6.6, 1.2.3.4")) == "1.2.3.4"
