"""Sandbox execution service: `uvicorn judge.sandbox_server:app --port 8090`.

Deploy only inside the hardened `sandbox` container (see docker-compose.yml):
read-only root filesystem, tmpfs /tmp, all capabilities dropped, no-new-privileges,
pids/memory/CPU limits, unprivileged user, and an `internal: true` network so the
executed code has no route to the internet. Only the judge worker can reach it.

Every request must carry an HMAC signature over the timestamp and body made with
SANDBOX_SHARED_SECRET. Requested limits are clamped to this server's maxima.
"""
from __future__ import annotations

import asyncio
import hmac
import json
import os
import time
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Request

from judge.signing import sign_sandbox_request
from judge.process_runner import Limits, run_harness

SECRET = os.getenv("SANDBOX_SHARED_SECRET", "")
MAX_BODY_BYTES = 200_000
MAX_SKEW_SECONDS = 60
SERVER_MAX = Limits(
    cpu_seconds=float(os.getenv("SANDBOX_MAX_CPU_SECONDS", "4")),
    wall_seconds=float(os.getenv("SANDBOX_MAX_WALL_SECONDS", "10")),
    memory_mb=int(os.getenv("SANDBOX_MAX_MEMORY_MB", "512")),
    max_processes=int(os.getenv("SANDBOX_MAX_PROCESSES", "32")),
    max_output_bytes=int(os.getenv("SANDBOX_MAX_OUTPUT_BYTES", "512000")),
)
_slots = asyncio.Semaphore(int(os.getenv("SANDBOX_CONCURRENCY", "2")))

app = FastAPI(title="ConceptViva Sandbox", docs_url=None, redoc_url=None, openapi_url=None)


def _clamp(requested: dict) -> Limits:
    def pick(name, cast):
        try:
            value = cast(requested.get(name, getattr(SERVER_MAX, name)))
        except (TypeError, ValueError):
            value = getattr(SERVER_MAX, name)
        return max(cast(1), min(value, getattr(SERVER_MAX, name)))

    return Limits(
        cpu_seconds=pick("cpu_seconds", float),
        wall_seconds=pick("wall_seconds", float),
        memory_mb=pick("memory_mb", int),
        max_processes=pick("max_processes", int),
        max_output_bytes=pick("max_output_bytes", int),
    )


def verify_signature(secret: str, timestamp: str, signature: str, body: bytes, now: float | None = None) -> bool:
    if not secret or not timestamp or not signature:
        return False
    try:
        skew = abs((now or time.time()) - int(timestamp))
    except ValueError:
        return False
    if skew > MAX_SKEW_SECONDS:
        return False
    return hmac.compare_digest(sign_sandbox_request(secret, timestamp, body), signature)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/execute")
async def execute(request: Request):
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")
    if not verify_signature(
        SECRET,
        request.headers.get("x-sandbox-timestamp", ""),
        request.headers.get("x-sandbox-signature", ""),
        body,
    ):
        raise HTTPException(status_code=401, detail="bad signature")

    try:
        data = json.loads(body)
        stdin_payload = str(data["stdin"])
        limits = _clamp(data.get("limits") or {})
    except (ValueError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="bad request")

    async with _slots:
        outcome = await asyncio.to_thread(run_harness, stdin_payload, limits)
    return asdict(outcome)
