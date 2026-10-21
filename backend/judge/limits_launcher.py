"""Apply resource limits to the current process, then exec the harness.

Usage: python -I -S -B limits_launcher.py '<limits-json>' <harness-path>

Run as the first program in the sandboxed child so limits are set by the child
itself before any user code is loaded. This avoids `preexec_fn`, which is unsafe in
multi-threaded parents such as the judge worker and the sandbox server.
"""
import json
import os
import resource
import sys


def main():
    limits = json.loads(sys.argv[1])
    harness = sys.argv[2]

    cpu = max(1, int(float(limits["cpu_seconds"]) + 0.999))
    memory = int(limits["memory_mb"]) * 1024 * 1024
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu + 1))
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_NPROC, (int(limits["max_processes"]),) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (int(limits["max_file_bytes"]),) * 2)
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    os.execv(sys.executable, [sys.executable, "-I", "-S", "-B", harness])


if __name__ == "__main__":
    main()
