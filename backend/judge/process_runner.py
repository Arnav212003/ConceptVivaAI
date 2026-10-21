"""Run the harness in a resource-limited child process.

Used inside the sandbox container (judge/sandbox_server.py) and by the dev-only
local executor. On Linux the child gets, before exec:
- RLIMIT_CPU (CPU seconds), RLIMIT_AS (address space = memory), RLIMIT_NPROC
  (no fork bombs), RLIMIT_FSIZE (no large files), RLIMIT_NOFILE, RLIMIT_CORE=0
- its own session (so the whole process group is killed on timeout)
- a drop to an unprivileged uid/gid when started as root
- an empty environment and an empty temporary working directory
Wall-clock time and stdout/stderr size are enforced by this parent process.
Network isolation is provided by the container network (see docker-compose.yml),
not by this module. On Windows only wall-clock and output limits apply, which is
why the local executor is refused unless JUDGE_ALLOW_UNSAFE_LOCAL=true.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from judge.verdicts import ExecutionOutcome

HARNESS_PATH = Path(__file__).resolve().parent / "harness_script.py"
NOBODY_UID = 65534


@dataclass(frozen=True)
class Limits:
    cpu_seconds: float = 2.0
    wall_seconds: float = 5.0
    memory_mb: int = 256
    max_processes: int = 16
    max_output_bytes: int = 256_000
    max_file_bytes: int = 1_000_000


def harness_source() -> str:
    return HARNESS_PATH.read_text(encoding="utf-8")


def _limit_child(limits: Limits):  # pragma: no cover - runs in the forked child on POSIX
    import resource

    cpu = max(1, int(limits.cpu_seconds + 0.999))
    memory = limits.memory_mb * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_NPROC, (limits.max_processes, limits.max_processes))
    resource.setrlimit(resource.RLIMIT_FSIZE, (limits.max_file_bytes, limits.max_file_bytes))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.setsid()
    if os.getuid() == 0:
        os.setgroups([])
        os.setgid(NOBODY_UID)
        os.setuid(NOBODY_UID)


def _drain(stream, sink: bytearray, cap: int, overflow: threading.Event):
    while True:
        chunk = stream.read(8192)
        if not chunk:
            return
        if len(sink) + len(chunk) > cap:
            sink.extend(chunk[: max(0, cap - len(sink))])
            overflow.set()
            return
        sink.extend(chunk)


def _kill(process: subprocess.Popen):
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
    except (ProcessLookupError, PermissionError, OSError):
        pass


def run_harness(stdin_payload: str, limits: Limits, python_executable: str | None = None) -> ExecutionOutcome:
    workdir = tempfile.mkdtemp(prefix="cv_judge_")
    command = [python_executable or sys.executable, "-I", "-S", "-B", str(HARNESS_PATH)]
    preexec = (lambda: _limit_child(limits)) if os.name == "posix" else None
    started = time.perf_counter()

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=workdir,
            env={"PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "0"},
            preexec_fn=preexec,  # noqa: PLW1509 - limits must be applied before exec
            close_fds=True,
        )
    except OSError as exc:
        shutil.rmtree(workdir, ignore_errors=True)
        return ExecutionOutcome(status="internal_error", detail=f"spawn failed: {type(exc).__name__}")

    stdout, stderr = bytearray(), bytearray()
    overflow = threading.Event()
    readers = [
        threading.Thread(target=_drain, args=(process.stdout, stdout, limits.max_output_bytes, overflow), daemon=True),
        threading.Thread(target=_drain, args=(process.stderr, stderr, 64_000, overflow), daemon=True),
    ]
    for reader in readers:
        reader.start()

    timed_out = False
    try:
        process.stdin.write(stdin_payload.encode("utf-8"))
        process.stdin.close()
    except (BrokenPipeError, OSError):
        pass

    deadline = started + limits.wall_seconds
    while process.poll() is None:
        if overflow.is_set():
            _kill(process)
            break
        if time.perf_counter() > deadline:
            timed_out = True
            _kill(process)
            break
        time.sleep(0.01)
    process.wait()
    for reader in readers:
        reader.join(timeout=1)
    duration_ms = (time.perf_counter() - started) * 1000
    shutil.rmtree(workdir, ignore_errors=True)

    out = stdout.decode("utf-8", errors="replace")
    err = stderr.decode("utf-8", errors="replace")
    code = process.returncode

    sigxcpu = -getattr(signal, "SIGXCPU", 24)
    sigkill = -getattr(signal, "SIGKILL", 9)
    if overflow.is_set():
        status = "output_limit"
    elif timed_out or code == sigxcpu:
        # Wall clock exceeded, or RLIMIT_CPU delivered SIGXCPU.
        status = "timeout"
    elif code == sigkill or ("MemoryError" in err and "__CV_RESULT__" not in out):
        # An unrequested SIGKILL comes from the container's OOM killer.
        status = "memory"
    else:
        status = "ok"
    return ExecutionOutcome(status=status, stdout=out, stderr=err[-4000:], exit_code=code, duration_ms=duration_ms)
