"""Executors run the harness somewhere isolated and report an ExecutionOutcome.

- Judge0Executor  (recommended): Judge0 CE runs the program in an isolate sandbox with
  CPU/wall/memory/process limits and `enable_network=false`.
- SandboxExecutor: our own sandbox service (judge/sandbox_server.py) inside a locked-down
  container on an internal-only Docker network. Requests are HMAC-signed.
- LocalExecutor (development/tests only): resource-limited subprocess on the worker host.
  Refused unless JUDGE_ALLOW_UNSAFE_LOCAL=true, because a subprocess on a developer
  machine is not a security boundary.

None of these run inside the FastAPI process; the API only enqueues jobs.
"""
from __future__ import annotations

import asyncio
import base64
import json
import time
from dataclasses import asdict

import httpx

from config import settings
from judge.process_runner import Limits, harness_source, run_harness
from judge.signing import sign_sandbox_request
from judge.verdicts import ExecutionOutcome


def default_limits() -> Limits:
    return Limits(
        cpu_seconds=settings.judge_cpu_seconds,
        wall_seconds=settings.judge_wall_seconds,
        memory_mb=settings.judge_memory_mb,
        max_processes=settings.judge_max_processes,
        max_output_bytes=settings.judge_max_output_bytes,
    )


class LocalExecutor:
    name = "local"

    async def execute(self, stdin_payload: str, limits: Limits) -> ExecutionOutcome:
        return await asyncio.to_thread(run_harness, stdin_payload, limits)


class SandboxExecutor:
    name = "sandbox"

    def __init__(self, url: str, secret: str):
        if not secret:
            raise ValueError("SANDBOX_SHARED_SECRET is required for the sandbox executor")
        self.url = url
        self.secret = secret

    async def execute(self, stdin_payload: str, limits: Limits) -> ExecutionOutcome:
        body = json.dumps({"stdin": stdin_payload, "limits": asdict(limits)}).encode()
        timestamp = str(int(time.time()))
        headers = {
            "Content-Type": "application/json",
            "X-Sandbox-Timestamp": timestamp,
            "X-Sandbox-Signature": sign_sandbox_request(self.secret, timestamp, body),
        }
        try:
            async with httpx.AsyncClient(timeout=limits.wall_seconds + 10) as client:
                response = await client.post(f"{self.url}/execute", content=body, headers=headers)
            response.raise_for_status()
            return ExecutionOutcome(**response.json())
        except (httpx.HTTPError, TypeError, ValueError) as exc:
            return ExecutionOutcome(status="internal_error", detail=f"sandbox: {type(exc).__name__}")


# Judge0 status ids: https://github.com/judge0/judge0/blob/master/docs/api/statuses.md
_JUDGE0_PENDING = {1, 2}
_JUDGE0_TIMEOUT = {5}
_JUDGE0_OUTPUT_LIMIT = {8}          # SIGXFSZ
_JUDGE0_RUNTIME = {6, 7, 9, 10, 11, 12}
_JUDGE0_INTERNAL = {13, 14}


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _unb64(value) -> str:
    if not value:
        return ""
    try:
        return base64.b64decode(value).decode("utf-8", errors="replace")
    except ValueError:
        return ""


def judge0_outcome(data: dict, limits: Limits) -> ExecutionOutcome:
    status_id = int((data.get("status") or {}).get("id", 13))
    stdout = _unb64(data.get("stdout"))
    stderr = _unb64(data.get("stderr")) or _unb64(data.get("compile_output"))
    duration_ms = float(data.get("time") or 0) * 1000
    memory_kb = int(data.get("memory") or 0)

    if status_id in _JUDGE0_INTERNAL:
        return ExecutionOutcome(status="internal_error", detail=_unb64(data.get("message")) or "judge0 internal error")
    if status_id in _JUDGE0_TIMEOUT:
        return ExecutionOutcome(status="timeout", stdout=stdout, stderr=stderr, duration_ms=duration_ms)
    if status_id in _JUDGE0_OUTPUT_LIMIT:
        return ExecutionOutcome(status="output_limit", stdout="", stderr=stderr, duration_ms=duration_ms)
    if status_id in _JUDGE0_RUNTIME and memory_kb >= limits.memory_mb * 1024 * 0.95:
        return ExecutionOutcome(status="memory", stdout=stdout, stderr=stderr, duration_ms=duration_ms)
    if len(stdout.encode()) > limits.max_output_bytes:
        return ExecutionOutcome(status="output_limit", duration_ms=duration_ms)
    # Accepted (3) and runtime errors both carry harness output when it was reached.
    return ExecutionOutcome(status="ok", stdout=stdout, stderr=stderr, duration_ms=duration_ms,
                            extra={"judge0_status": status_id, "memory_kb": memory_kb})


class Judge0Executor:
    name = "judge0"

    def __init__(self, url: str, api_key: str = "", language_id: int = 71):
        self.url = url
        self.language_id = language_id
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            # Self-hosted Judge0 uses X-Auth-Token; RapidAPI-hosted uses X-RapidAPI-Key.
            header = "X-RapidAPI-Key" if "rapidapi" in url else "X-Auth-Token"
            self.headers[header] = api_key

    def submission_body(self, stdin_payload: str, limits: Limits) -> dict:
        return {
            "source_code": _b64(harness_source()),
            "language_id": self.language_id,
            "stdin": _b64(stdin_payload),
            "cpu_time_limit": limits.cpu_seconds,
            "cpu_extra_time": 0.5,
            "wall_time_limit": limits.wall_seconds,
            "memory_limit": limits.memory_mb * 1024,
            "max_processes_and_or_threads": limits.max_processes,
            "max_file_size": limits.max_file_bytes // 1024,
            "enable_network": False,
            "redirect_stderr_to_stdout": False,
        }

    async def execute(self, stdin_payload: str, limits: Limits) -> ExecutionOutcome:
        body = self.submission_body(stdin_payload, limits)
        fields = "stdout,stderr,compile_output,status,time,memory,message"
        try:
            async with httpx.AsyncClient(timeout=limits.wall_seconds + 15, headers=self.headers) as client:
                created = await client.post(
                    f"{self.url}/submissions", params={"base64_encoded": "true", "wait": "false"}, json=body
                )
                created.raise_for_status()
                token = created.json()["token"]
                deadline = time.monotonic() + limits.wall_seconds + 20
                while time.monotonic() < deadline:
                    polled = await client.get(
                        f"{self.url}/submissions/{token}", params={"base64_encoded": "true", "fields": fields}
                    )
                    polled.raise_for_status()
                    data = polled.json()
                    if int((data.get("status") or {}).get("id", 1)) not in _JUDGE0_PENDING:
                        return judge0_outcome(data, limits)
                    await asyncio.sleep(0.25)
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            return ExecutionOutcome(status="internal_error", detail=f"judge0: {type(exc).__name__}")
        return ExecutionOutcome(status="internal_error", detail="judge0: result polling timed out")


class ExecutorNotConfigured(RuntimeError):
    pass


def get_executor():
    executor = settings.judge_executor
    if executor == "judge0" and settings.judge0_url:
        return Judge0Executor(settings.judge0_url, settings.judge0_api_key, settings.judge0_python_language_id)
    if executor == "sandbox" and settings.sandbox_url:
        return SandboxExecutor(settings.sandbox_url, settings.sandbox_shared_secret)
    if executor == "local" and settings.judge_allow_unsafe_local:
        return LocalExecutor()
    raise ExecutorNotConfigured(
        "No isolated executor configured. Set JUDGE_EXECUTOR=judge0 with JUDGE0_URL, "
        "or JUDGE_EXECUTOR=sandbox with SANDBOX_URL and SANDBOX_SHARED_SECRET."
    )


def executor_configured() -> bool:
    try:
        get_executor()
    except (ExecutorNotConfigured, ValueError):
        return False
    return True
