"""Async LLM gateway used by every AI feature.

Responsibilities:
- One place that knows the model name, timeouts, retry policy and breaker state.
- Structured JSON output: the Pydantic schema is sent to Gemini as `response_schema`
  and the reply is validated again with `model_validate_json`. Invalid output is
  never "repaired" with regex; it is retried once and then reported as unavailable.
- Bounded retries with exponential backoff + jitter for transient failures only
  (timeouts, HTTP 429 and 5xx). Auth/validation errors fail fast.
- A circuit breaker so a Gemini outage turns into fast "unavailable" responses
  instead of every request waiting for the full timeout.

Tests swap the backend with `set_llm_backend(...)`; no test talks to Gemini.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Optional, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from config import settings
from observability import LLM_CIRCUIT_STATE, LLM_LATENCY, LLM_REQUESTS, get_logger, log_event

T = TypeVar("T", bound=BaseModel)

logger = get_logger("llm")


class LLMUnavailableError(Exception):
    """The model could not produce a usable answer (not configured, outage, bad output)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class TransientLLMError(Exception):
    """Raised by backends for failures that are worth retrying."""


class LLMBackend(Protocol):
    model_name: str

    async def generate(
        self,
        *,
        system_instruction: str,
        prompt: str,
        response_schema: Optional[type[BaseModel]],
        temperature: float,
    ) -> str: ...


class GeminiBackend:
    def __init__(self, api_key: str, model_name: str):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model_name = model_name

    async def generate(self, *, system_instruction, prompt, response_schema, temperature) -> str:
        from google.genai import errors, types

        config_kwargs = {
            "system_instruction": system_instruction,
            "temperature": temperature,
        }
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        try:
            response = await self._client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs),
            )
        except errors.ServerError as exc:
            raise TransientLLMError(f"server_error_{getattr(exc, 'code', 'unknown')}") from exc
        except errors.ClientError as exc:
            if getattr(exc, "code", None) == 429:
                raise TransientLLMError("rate_limited_429") from exc
            raise
        except (OSError, ConnectionError) as exc:
            raise TransientLLMError("network_error") from exc

        return response.text or ""


class CircuitBreaker:
    """Consecutive-failure breaker: CLOSED -> OPEN -> HALF_OPEN -> CLOSED."""

    def __init__(self, failure_threshold: int, reset_seconds: float, clock=time.monotonic):
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: Optional[float] = None
        self._half_open_trial = False

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if self._clock() - self._opened_at >= self.reset_seconds:
            return "half_open"
        return "open"

    def allow_request(self) -> bool:
        state = self.state
        if state == "closed":
            return True
        if state == "half_open" and not self._half_open_trial:
            self._half_open_trial = True
            return True
        return False

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        self._half_open_trial = False
        LLM_CIRCUIT_STATE.set(0)

    def record_failure(self) -> None:
        self._failures += 1
        if self.state == "half_open" or self._failures >= self.failure_threshold:
            self._opened_at = self._clock()
            self._half_open_trial = False
            LLM_CIRCUIT_STATE.set(1)


_backend: Optional[LLMBackend] = None
_backend_initialized = False
breaker = CircuitBreaker(settings.llm_breaker_failure_threshold, settings.llm_breaker_reset_seconds)


def get_llm_backend() -> Optional[LLMBackend]:
    global _backend, _backend_initialized
    if not _backend_initialized:
        _backend_initialized = True
        if settings.gemini_api_key:
            try:
                _backend = GeminiBackend(settings.gemini_api_key, settings.gemini_model)
            except Exception:  # SDK missing or misconfigured
                log_event(logger, "llm_backend_init_failed", level=40)
                _backend = None
    return _backend


def set_llm_backend(backend: Optional[LLMBackend]) -> None:
    """Override the backend (tests, benchmarks with recorded outputs)."""
    global _backend, _backend_initialized
    _backend = backend
    _backend_initialized = True
    breaker.record_success()


def current_model_name() -> str:
    backend = get_llm_backend()
    return backend.model_name if backend else "unavailable"


def _backoff_delay(attempt: int) -> float:
    base = settings.llm_backoff_base_seconds
    return min(8.0, base * (2 ** attempt)) + random.uniform(0, base)


async def _call(
    operation: str,
    *,
    system_instruction: str,
    prompt: str,
    response_schema: Optional[type[BaseModel]],
    temperature: float,
    validate,
):
    backend = get_llm_backend()
    if backend is None:
        LLM_REQUESTS.labels(operation, "not_configured").inc()
        raise LLMUnavailableError("not_configured")

    if not breaker.allow_request():
        LLM_REQUESTS.labels(operation, "circuit_open").inc()
        raise LLMUnavailableError("circuit_open")

    started = time.perf_counter()
    last_reason = "unknown"
    attempts = settings.llm_max_retries + 1

    try:
        for attempt in range(attempts):
            try:
                raw = await asyncio.wait_for(
                    backend.generate(
                        system_instruction=system_instruction,
                        prompt=prompt,
                        response_schema=response_schema,
                        temperature=temperature,
                    ),
                    timeout=settings.llm_timeout_seconds,
                )
            except (asyncio.TimeoutError, TransientLLMError) as exc:
                last_reason = "timeout" if isinstance(exc, asyncio.TimeoutError) else str(exc)
                breaker.record_failure()
                if attempt + 1 < attempts and breaker.state == "closed":
                    await asyncio.sleep(_backoff_delay(attempt))
                    continue
                break
            except Exception as exc:  # non-retryable: auth, bad request, SDK bug
                last_reason = f"error_{type(exc).__name__}"
                breaker.record_failure()
                break

            # The service answered, so the infrastructure is healthy.
            breaker.record_success()
            try:
                result = validate(raw)
            except (ValidationError, ValueError) as exc:
                last_reason = "invalid_output"
                log_event(logger, "llm_invalid_output", level=30, operation=operation,
                          error_type=type(exc).__name__)
                if attempt + 1 < attempts:
                    continue
                break

            LLM_REQUESTS.labels(operation, "success").inc()
            return result
    finally:
        LLM_LATENCY.labels(operation).observe(time.perf_counter() - started)

    LLM_REQUESTS.labels(operation, last_reason.split("_")[0] if last_reason else "error").inc()
    log_event(logger, "llm_unavailable", level=30, operation=operation, reason=last_reason)
    raise LLMUnavailableError(last_reason)


async def generate_structured(
    operation: str,
    *,
    system_instruction: str,
    prompt: str,
    schema: type[T],
    temperature: float = 0.0,
) -> T:
    def validate(raw: str) -> T:
        if not raw.strip():
            raise ValueError("empty response")
        return schema.model_validate_json(raw)

    return await _call(
        operation,
        system_instruction=system_instruction,
        prompt=prompt,
        response_schema=schema,
        temperature=temperature,
        validate=validate,
    )


async def generate_text(
    operation: str,
    *,
    system_instruction: str,
    prompt: str,
    temperature: float = 0.4,
    max_chars: int = 20_000,
) -> str:
    def validate(raw: str) -> str:
        text = raw.strip()
        if not text:
            raise ValueError("empty response")
        return text[:max_chars]

    return await _call(
        operation,
        system_instruction=system_instruction,
        prompt=prompt,
        response_schema=None,
        temperature=temperature,
        validate=validate,
    )
