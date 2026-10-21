"""Retry, timeout and circuit-breaker behaviour of the LLM gateway."""
import asyncio

from pydantic import BaseModel

from config import settings
from services import llm
from services.llm import CircuitBreaker


class Echo(BaseModel):
    value: str


class ScriptedBackend:
    model_name = "scripted"

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    async def generate(self, **kwargs):
        self.calls += 1
        step = self.script.pop(0)
        if isinstance(step, Exception):
            raise step
        if step == "sleep":
            await asyncio.sleep(10)
        return step


def call():
    return asyncio.run(llm.generate_structured(
        "test", system_instruction="s", prompt="p", schema=Echo
    ))


def test_transient_errors_are_retried_then_succeed():
    backend = ScriptedBackend([llm.TransientLLMError("server_error_503"), '{"value": "ok"}'])
    llm.set_llm_backend(backend)
    assert call().value == "ok"
    assert backend.calls == 2


def test_non_retryable_errors_fail_fast():
    backend = ScriptedBackend([PermissionError("bad key"), '{"value": "never"}'])
    llm.set_llm_backend(backend)
    try:
        call()
        raise AssertionError("expected LLMUnavailableError")
    except llm.LLMUnavailableError as exc:
        assert exc.reason == "error_PermissionError"
    assert backend.calls == 1


def test_timeout_is_bounded():
    # Settings is a frozen dataclass; override the field for this test only.
    original = settings.llm_timeout_seconds
    object.__setattr__(settings, "llm_timeout_seconds", 0.05)
    try:
        backend = ScriptedBackend(["sleep", "sleep", "sleep"])
        llm.set_llm_backend(backend)
        try:
            call()
            raise AssertionError("expected timeout")
        except llm.LLMUnavailableError as exc:
            assert exc.reason == "timeout"
    finally:
        object.__setattr__(settings, "llm_timeout_seconds", original)


def test_circuit_breaker_opens_and_recovers():
    now = [0.0]
    breaker = CircuitBreaker(failure_threshold=3, reset_seconds=30, clock=lambda: now[0])

    for _ in range(3):
        assert breaker.allow_request()
        breaker.record_failure()
    assert breaker.state == "open"
    assert not breaker.allow_request()

    now[0] = 31
    assert breaker.state == "half_open"
    assert breaker.allow_request()       # one trial request
    assert not breaker.allow_request()   # others wait for the trial
    breaker.record_success()
    assert breaker.state == "closed"


def test_failed_half_open_trial_reopens():
    now = [0.0]
    breaker = CircuitBreaker(failure_threshold=1, reset_seconds=10, clock=lambda: now[0])
    breaker.record_failure()
    now[0] = 11
    assert breaker.allow_request()
    breaker.record_failure()
    assert breaker.state == "open"


def test_open_circuit_short_circuits_calls():
    backend = ScriptedBackend(['{"value": "ok"}'])
    llm.set_llm_backend(backend)
    for _ in range(settings.llm_breaker_failure_threshold):
        llm.breaker.record_failure()
    try:
        call()
        raise AssertionError("expected circuit_open")
    except llm.LLMUnavailableError as exc:
        assert exc.reason == "circuit_open"
    assert backend.calls == 0
