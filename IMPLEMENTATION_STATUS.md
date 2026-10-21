# Implementation Status

Tracks the multi-phase improvement work on ConceptVivaAI. Every entry reflects what was actually
built and verified in this repository. External steps that need credentials or
infrastructure that were not available during implementation are marked **BLOCKED**.

Legend: **DONE** · **IN PROGRESS** · **BLOCKED** · **TODO**

## Baseline (before any change)

- Baseline: commit `1f2b774` (tagged before any change); all work on branch `feature/project-improvements`.
- Local SQLite database backed up to `backend/backups/` (git-ignored).
- Backend: `python -m pytest` → 28 passed.
- Frontend: `npm run lint` → clean, `npm run build` → success.
- Tooling on the implementation machine: Node 24, Python 3.11. Docker and Redis were **not** installed.

## Phase 1 — Security and AI grading

| Item | Status | Notes |
|---|---|---|
| Prompt-injection defenses | DONE | `services/grading/safety.py`: grading rules in the system instruction, user text inside nonce-delimited untrusted blocks, neutralization of fake delimiter tags, narrow heuristics (prose + code comments/strings only), model self-report, server-side score cap. Adversarial and false-positive tests in `tests/test_grading_safety.py`. |
| Structured JSON output + schema validation | DONE | `services/llm.py` sends Pydantic schemas as `response_schema` and re-validates with `model_validate_json`. Regex JSON extraction removed from all AI paths. Out-of-range rubric points are rejected, not clamped. |
| Rubric scoring computed on server | DONE | Model returns per-criterion points; `Rubric.total()` computes the 0-10 score. Extra keys such as `score` are ignored. |
| No fake fallback scores | DONE | Outages return `evaluation_status="unavailable"`, `score=None`, no receipt. Stored rows keep `score NULL`; dashboard averages count only `completed` rows with a score (`crud._attempt_summary`). Project challenges stay ACTIVE after an outage. |
| Preserve receipts / revocation | DONE | Existing HMAC sessions, receipts and revocation unchanged; receipts now issued only for completed evaluations. Original tests still pass. |
| Centralized configuration | DONE | `config.py` loads env once; model name, timeouts, CORS origins, secrets, Redis, judge and OAuth settings live there. |
| Remove hardcoded IPs / unused code | DONE | Private IP removed from CORS and `next.config.mjs` (now `NEXT_ALLOWED_DEV_ORIGINS`). Removed unused `@google/genai`, legacy `run_python_tests` / `get_optimized_solution` / `fallback_dsa_evaluation` helpers and the `main.py` re-export. |
| Additive migration `0002_evaluation_status` | DONE | Existing rows become `completed`. SQLite auto-migrates on startup (`db_bootstrap.py`); upgrade/downgrade round-trip tested. |
| Live Gemini verification of structured output | BLOCKED | Not run, to avoid billable API calls without approval. Schema conversion verified offline with the installed SDK (`google-genai 1.75.0`). |

Phase 1 tests: `python -m pytest` → 86 passed. `npm run lint` → clean.

## Phase 2 — Secure DSA code judge

| Item | Status | Notes |
|---|---|---|
| No code execution in FastAPI | DONE | Old in-process `dsa_runner.py` removed. The API only enqueues (`judge/client.py`); `judge/worker.py` is a separate process. |
| Isolated executors | DONE | `Judge0Executor` (network disabled, CPU/wall/memory/process limits), `SandboxExecutor` (HMAC-signed requests to `judge/sandbox_server.py`, limits clamped server-side), dev-only `LocalExecutor` refused unless `JUDGE_ALLOW_UNSAFE_LOCAL=true`. |
| Process limits | DONE | `judge/process_runner.py`: RLIMIT_CPU/AS/NPROC/FSIZE/NOFILE/CORE, own session + group kill, uid drop when root, empty env, temp cwd, wall clock and output caps. rlimits only apply on Linux (sandbox container); Windows dev runs have wall/output limits only. |
| Hidden tests | DONE | All 90 bank questions run their tests in `judge/harness_script.py`. Only the first sample case and the first failing case are revealed. |
| Redis queue + async workers | DONE | `judge/queue.py`: BLMOVE reliable queue, processing list, stale-job recovery (max 2 attempts), backpressure, worker heartbeat, source deleted after judging, 1 h retention. |
| Verdicts | DONE | Accepted, Wrong Answer, Time Limit Exceeded, Runtime Error, Compilation Error, plus Memory Limit Exceeded, Output Limit Exceeded and Internal Error (`judge/verdicts.py`). |
| No false "verified" labels | DONE | `verified` only when `scoring_method == "hidden_tests"`. The judge counts as available only with JUDGE_ENABLED, a configured isolated executor, Redis, and a live worker heartbeat. |
| Endpoints | DONE | `POST /dsa/run` (sync wait), `POST /dsa/submissions` (202) + `GET /dsa/submissions/{id}` (owner-only). `/evaluate-dsa-solution` uses the judge for bank questions. |
| Container hardening config | DONE in Phase 6 | See `docker-compose.yml` `sandbox` service. |
| Live Judge0 / Docker sandbox run | BLOCKED | Docker is not installed on the implementation machine, so the Judge0 executor and the containerized sandbox were not run end to end. Judge0 request/response mapping is unit tested; harness verdicts are tested through the real local subprocess. |
| Expand hidden tests beyond 3 per question | TODO | The bank currently has 3 tests per question. More edge-case tests would make verdicts stronger. |

Phase 2 tests: `python -m pytest` → 116 passed.

## Phase 3 — AI grader benchmarking

| Item | Status | Notes |
|---|---|---|
| Rubric-based evaluation with versioned prompts | DONE | `services/grading/prompts.py` (`answer_eval@2.0.0` etc.); `prompt_version` + `model_name` stored on every attempt; `tests/test_grading_prompts.py` fails if a prompt changes without a version bump. |
| Benchmark pipeline for 100 human-labelled answers | DONE | `benchmarks/grader/` (dataset schema + CSV import, graders, metrics, CLI, reports). Human and synthetic rows cannot be mixed in one dataset. |
| MAE, consistency, correlation | DONE | MAE (+ bootstrap CI), RMSE, Pearson, Spearman, within-1, Cohen's kappa, repeatability (per-item std, identical rate), human inter-rater ceiling. Unit tested against known values. |
| Repeatability + adversarial tests | DONE | Temperature-0 repeatability test; 10-item synthetic injection suite with attack-success and false-positive rates; `fooled_model` grader measures the server-side defenses alone. |
| Synthetic data labelled | DONE | `data/synthetic_seed.jsonl` rows all carry `"source": "synthetic"`; reports built from it start with a SYNTHETIC banner. |
| Offline results (synthetic only) | DONE | `fooled_model` on the seed set: attack success 0.00 (10 attacks), 0/31 honest answers capped. Attacks and heuristics have the same author, so this covers known patterns only. |
| 100 human labels | BLOCKED | Needs real human labelers. Template: `data/labeling_template.csv`; protocol in `benchmarks/grader/README.md`. No human evaluation data was invented. |
| Production (Gemini) benchmark run | BLOCKED | Requires approval for billable Gemini calls and the human dataset. Command documented; the CLI refuses without `--allow-api-calls`. |

Phase 3 tests: `python -m pytest` → 132 passed.

## Phase 4 — Production backend

| Item | Status | Notes |
|---|---|---|
| Async Gemini calls | DONE | `client.aio.models.generate_content` behind `services/llm.py`; AI routes are `async def`; DB writes inside them go through `run_in_threadpool`. |
| Timeouts, bounded retries, circuit breaker | DONE | `asyncio.wait_for` timeout, retries only for timeouts/429/5xx with exponential backoff + jitter, consecutive-failure breaker with half-open trial. Tested in `tests/test_llm_resilience.py`. |
| Redis distributed rate limiting | DONE | `rate_limit.py`: sliding log in a sorted set inside MULTI/EXEC; rejected hits don't consume quota; shared across instances; falls back to the in-process limiter if Redis fails. Dashboard/history now limited too. |
| Proxy-aware client IP | DONE | `TRUSTED_PROXY_HOPS` (Render/Railway = 1). Without it, every user behind the proxy shared one session-start limit. |
| Structured logging, request IDs, metrics | DONE | JSON logs with request id and redaction (`observability.py`); `X-Request-ID` propagated; Prometheus `/metrics` (HTTP, LLM, breaker, judge, cache, rate-limit), token-protected with `METRICS_TOKEN`, hidden in production without one. A redaction bug (Bearer tokens) was found by tests and fixed. |
| Safe caching | DONE | Hindi translations (7 days) and curated-bank problem statements (1 day) in Redis or memory, keyed by SHA-256. Evaluations and scores are never cached. |
| Load tests | DONE | `loadtests/locustfile.py` (AI endpoints behind the `ai` tag). Local run: 50 users / 60 s, 2,258 requests, 0 failures, p95 54 ms, p99 100 ms; see `loadtests/RESULTS.md` for the environment and caveats. |
| Production load test | BLOCKED | Needs the deployed environment. |
| FastAPI / PostgreSQL / Alembic / frontend compatibility | DONE | Existing endpoints and response fields are kept; new fields are additive. |

Phase 4 tests: `python -m pytest` → 146 passed.

## Phase 5 — Authentication and frontend

| Item | Status | Notes |
|---|---|---|
| Google OAuth | DONE | Authorization code + PKCE, state/nonce in a signed 10-minute HttpOnly cookie, server-side code exchange, ID token verified with `google-auth` (signature, audience, issuer, expiry, nonce, email_verified). Open-redirect-safe `return_to`. |
| HttpOnly cookie sessions | DONE | `cv_auth` HttpOnly + SameSite=Lax (+ Secure in production); DB stores only SHA-256 token hashes; expiry and revocation on logout. Migration `0003_auth`. |
| CSRF protection | DONE | HMAC-bound double-submit token (`cv_csrf` + `X-CSRF-Token`) and Origin allowlist on unsafe cookie-authenticated requests. A planted CSRF cookie is rejected (tested). |
| Guest access + safe history migration | DONE | Guest HMAC sessions unchanged. `POST /auth/migrate-guest-history` needs a valid guest token and a CSRF-checked login; moves all history tables in one transaction, can run only once per guest session, then revokes the guest token. |
| Component refactor + custom hooks | DONE | Shared hooks (`useDsaWorkspace`, `useSolutionVoice`, `useSpeechSynthesis`, `useSpeechRecognition`, `useLocalHistory`, `useJudgeStatus`) and components (`dsa/*`, `project/*`, `dashboard/widgets`, `ui/*`). Largest files: DSAPractice 1387→227 lines, Interview 998→500, DSAMock 925→200, Project 800→271, Dashboard 653→226. One shared Next proxy (`src/lib/backendProxy.js`) replaces 7 copies. |
| Fixed during refactor | DONE | Stale-closure bug in voice-interview auto mode; scores of unavailable evaluations shown as 0/10; local averages counting failures as 0; raw error messages leaked by proxies; free-form "AI selected topic" instructions sent from the browser (now server-side `auto_topic`); `alert()` replaced by inline error states. |
| Vitest component tests | DONE | `npm test` → 25 passed (scoring, hooks, CSRF header + retry rules, verdict/hidden tests, project file filter excludes `.env`, ML practice flows incl. unavailable and 429). |
| Playwright E2E | DONE | `npm run test:e2e` → 12 passed (6 scenarios x desktop + mobile Chromium) against the production build with network-mocked APIs: navigation + no horizontal scroll, ML practice, DSA judge run + verified submit, judge-offline notice, dashboard error/retry + "Not scored", Google sign-in start. |
| Real proxy ↔ backend smoke test | DONE | Next production server + FastAPI: session, auto-topic, unavailable evaluation saved without score, dashboard counts, 400 on unknown action, 503 when judge offline, OAuth 302 + HttpOnly state cookie relayed, forged callback state rejected, security headers present. |
| Features preserved | DONE | ML practice, DSA practice (verified + AI), mock sets, project challenges, voice interviews, Hindi explanations, Monaco editor, dashboard, history. |
| Live Google sign-in | BLOCKED | Needs a Google Cloud OAuth client (client id/secret + authorized redirect URI). Flow is tested with Google mocked. |

Phase 5 tests: backend `python -m pytest` → 165 passed; `npm run lint` clean; `npm run build` OK; `npm test` → 25 passed; `npm run test:e2e` → 12 passed.

## Phase 6 — Deployment and documentation

| Item | Status | Notes |
|---|---|---|
| Docker Compose, CI, README, analytics | TODO | |
