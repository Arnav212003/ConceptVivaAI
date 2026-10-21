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
| Judge service | TODO | |

## Phase 3 — AI grader benchmarking

| Item | Status | Notes |
|---|---|---|
| Benchmark pipeline | TODO | |

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
