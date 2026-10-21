"""Structured logging, request IDs, and Prometheus metrics.

Logging rules:
- One JSON object per line, so log platforms (Render, Railway, Loki) can index fields.
- Never log request bodies, headers, cookies, query strings, or tokens. Only the
  route path, method, status, duration and the request id are recorded per request.
"""
from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
import time
import uuid

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from config import settings

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
_SECRET_PATTERN = re.compile(
    r"(api[_-]?key|token|secret|password|authorization|cookie)(\"?\s*[:=]\s*\"?)([^\s\",]+)",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    """Mask values that look like credentials before they reach a log line."""
    return _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "msg": redact(record.getMessage()),
            "request_id": request_id_var.get(),
        }
        for key, value in getattr(record, "fields", {}).items():
            payload[key] = redact(value) if isinstance(value, str) else value
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__ if record.exc_info[0] else "Exception"
        return json.dumps(payload, ensure_ascii=False)


_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("conceptviva")
    root.handlers = [handler]
    root.setLevel(settings.log_level)
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"conceptviva.{name}")


def log_event(logger: logging.Logger, message: str, level: int = logging.INFO, **fields) -> None:
    logger.log(level, message, extra={"fields": fields})


# ---------------------------------------------------------------- metrics

HTTP_REQUESTS = Counter(
    "conceptviva_http_requests_total",
    "HTTP requests by route template, method and status class.",
    ["route", "method", "status"],
)
HTTP_LATENCY = Histogram(
    "conceptviva_http_request_duration_seconds",
    "HTTP request latency by route template.",
    ["route", "method"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60),
)
LLM_REQUESTS = Counter(
    "conceptviva_llm_requests_total",
    "LLM calls by operation and outcome.",
    ["operation", "outcome"],
)
LLM_LATENCY = Histogram(
    "conceptviva_llm_request_duration_seconds",
    "LLM call latency (including retries) by operation.",
    ["operation"],
    buckets=(0.25, 0.5, 1, 2, 4, 8, 15, 30, 60),
)
LLM_CIRCUIT_STATE = Gauge(
    "conceptviva_llm_circuit_open",
    "1 when the LLM circuit breaker is open, else 0.",
)
JUDGE_VERDICTS = Counter(
    "conceptviva_judge_verdicts_total",
    "Code judge verdicts.",
    ["verdict"],
)
JUDGE_LATENCY = Histogram(
    "conceptviva_judge_duration_seconds",
    "Time from enqueue to finished verdict.",
    buckets=(0.1, 0.25, 0.5, 1, 2, 4, 8, 15, 30),
)
CACHE_EVENTS = Counter(
    "conceptviva_cache_events_total",
    "Cache hits and misses by namespace.",
    ["namespace", "event"],
)
RATE_LIMITED = Counter(
    "conceptviva_rate_limited_total",
    "Requests rejected by the rate limiter, by bucket.",
    ["bucket"],
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    # Unknown paths are grouped so attackers cannot explode metric cardinality.
    return path or "unmatched"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, records latency metrics, and writes one access log line."""

    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger("http")

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get("x-request-id", "")
        request_id = incoming if _REQUEST_ID_PATTERN.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            elapsed = time.perf_counter() - started
            route = _route_template(request)
            HTTP_REQUESTS.labels(route, request.method, f"{status_code // 100}xx").inc()
            HTTP_LATENCY.labels(route, request.method).observe(elapsed)
            log_event(
                self.logger,
                "request",
                method=request.method,
                route=route,
                status=status_code,
                duration_ms=round(elapsed * 1000, 1),
            )
            request_id_var.reset(token)
