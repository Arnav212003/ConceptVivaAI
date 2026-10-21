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
| Async LLM, resilience, Redis rate limiting, observability | TODO | |

## Phase 5 — Authentication and frontend

| Item | Status | Notes |
|---|---|---|
| Google OAuth, refactor, tests | TODO | |

## Phase 6 — Deployment and documentation

| Item | Status | Notes |
|---|---|---|
| Docker Compose, CI, README, analytics | TODO | |
