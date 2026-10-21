# Load test results

## Run 1: local baseline (2026-10-21)

**Environment.** Developer laptop (Windows 11), 1 uvicorn worker, SQLite on local
disk, no Redis (in-process rate limiter, disabled for the run), no Gemini key (AI
endpoints excluded via `--tags core`). Locust ran on the same machine.

**Command.**
```
locust -f loadtests/locustfile.py --host http://127.0.0.1:8765 --headless -u 50 -r 10 -t 60s --tags core
```

**Result.** 2,258 requests, 0 failures, 38.8 req/s aggregate.

| Endpoint | Requests | p50 ms | p95 ms | p99 ms | Max ms |
|---|---|---|---|---|---|
| GET /dashboard-stats | 913 | 21 | 72 | 120 | 164 |
| GET /history | 449 | 14 | 42 | 84 | 150 |
| GET /dsa-question-bank/stats | 428 | 10 | 21 | 52 | 91 |
| POST /generate-dsa-mock-set | 223 | 11 | 38 | 93 | 103 |
| GET /health | 195 | 5 | 17 | 70 | 90 |
| POST /session/start | 50 | 36 | 57 | 61 | 61 |
| **Aggregated** | **2,258** | **14** | **54** | **100** | **164** |

**How to read this.**
- Throughput is limited by the simulated users' 0.5-2 s think time, not by server
  capacity; this run shows latency under 50 concurrent users, not the maximum req/s.
- AI endpoints were not exercised. Their latency is dominated by Gemini (seconds),
  which is why they run async and behind a circuit breaker.
- Production numbers (PostgreSQL, Redis, multiple workers, network latency) have not
  been measured yet; rerun the same command against the deployed URL.
