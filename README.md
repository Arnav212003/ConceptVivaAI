# ConceptVivaAI

[![CI](https://github.com/Arnav212003/ConceptVivaAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Arnav212003/ConceptVivaAI/actions/workflows/ci.yml)

An interview-preparation platform for ML concepts, DSA coding, voice mock interviews
and project reviews. Answers are graded by a rubric-based LLM grader that is hardened
against prompt injection and measured with a benchmark. Code is judged by hidden
tests in an isolated sandbox, never inside the API.

> Live demo: _not deployed yet_ (see [Deployment](#deployment)). Replace with your Vercel URL.

## Features

| Area | What you can do |
|---|---|
| ML practice | Topic-wise (or auto-selected) questions; rubric score with per-criterion rationale, missing points, model answer, follow-up. |
| DSA practice | 90 curated questions with hidden tests, or unlimited AI-generated problems on any topic. AI-generated problems come with validated sample tests that run in the same sandbox (shown with input, expected and actual output, labelled as AI-generated and not verified). Monaco editor, Run and Submit. |
| DSA mock interview | 10-question mixed sets (3 Easy / 4 Medium / 3 Hard). |
| Code judge | Accepted, Wrong Answer, Time Limit Exceeded, Memory Limit Exceeded, Output Limit Exceeded, Runtime Error, Compilation Error (with syntax errors identified). |
| Voice interview | Browser speech recognition + synthesis, follow-ups for partial answers, revision queue, final report built from server-signed round scores. |
| Explanations | "Stuck?" reveals the optimized solution and reads it aloud in English or Hindi. |
| Project challenges | AI-generated mini projects; upload a whole source folder for cross-file review (bugs, security, missing requirements). |
| Dashboard | Per-module averages, verified vs AI-scored DSA, topic readiness, streak and weekly progress, history. |
| Accounts | Works as a guest instantly; optional Google sign-in moves guest history to the account and syncs across devices. |

## Architecture

```mermaid
flowchart LR
    B["Browser"] --> N["Next.js app<br/>UI + /api proxy"]
    N -->|"guest headers / HttpOnly cookie + CSRF"| A["FastAPI API"]
    A --> P[("PostgreSQL<br/>attempts, users")]
    A --> R[("Redis<br/>rate limits, cache, judge queue")]
    A --> L["LLM gateway<br/>timeouts, retries, breaker"]
    L --> G["Gemini API"]
    A --> O["Google OAuth"]
    W["Judge worker"] --> R
    W --> X{"Executor"}
    X --> J0["Judge0"]
    X --> S["Sandbox container<br/>internal network only"]
```

The browser only talks to the Next.js origin, so auth cookies are first-party. The
API never executes submitted code: it enqueues a job in Redis, and a separate worker
sends it to an isolated executor.

```mermaid
sequenceDiagram
    participant U as Browser
    participant API as FastAPI
    participant Q as Redis queue
    participant W as Judge worker
    participant S as Sandbox / Judge0
    U->>API: POST /evaluate-dsa-solution (bank question)
    API->>Q: LPUSH submission (code, hidden tests)
    W->>Q: BLMOVE queue -> processing
    W->>S: run harness (CPU, memory, process, output limits; no network)
    S-->>W: per-test results
    W->>Q: store verdict, delete source
    API->>Q: poll result (bounded wait)
    API->>API: score = passed/total x 10, AI feedback in parallel
    API-->>U: verdict + score (tier "verified")
```

## Engineering highlights

1. **LLM grading that cannot be talked into a 10.** User text is placed in nonce-delimited
   untrusted blocks, separate from the system instruction. Gemini returns structured JSON
   validated against Pydantic schemas. The model returns rubric points and the server
   computes the score, so an injected `"score": 10` is ignored. Heuristic and model-reported
   manipulation caps the score.
   ([`services/grading/`](backend/services/grading))
2. **No fake scores.** When Gemini is down, the attempt is stored as
   `evaluation_status = "unavailable"` with a NULL score, receives no signed receipt and
   is excluded from every average. The old behaviour saved a placeholder 5/10.
3. **Isolated code judge.** Redis reliable queue (BLMOVE + processing list, stale-job
   recovery, backpressure, heartbeats) and a worker that talks to Judge0 or to a hardened
   sandbox container (rlimits, uid drop, dropped capabilities, read-only FS, internal-only
   network). Only the sample case and the first failing case are revealed.
   ([`backend/judge/`](backend/judge))
4. **Grader benchmark.** Pipeline for evaluating the grader against human labels: MAE
   (bootstrap CI), Pearson/Spearman, kappa, repeatability, human inter-rater ceiling,
   adversarial attack-success rate and false-positive rate. Synthetic and human data
   cannot be mixed. ([`backend/benchmarks/grader/`](backend/benchmarks/grader))
5. **Production backend.** Async LLM gateway with timeouts, bounded retries with backoff
   and a circuit breaker; Redis sliding-window rate limiting shared across instances;
   JSON logs with request IDs and secret redaction; Prometheus metrics; safe caching;
   Locust load tests.

## Tech stack

**Frontend:** Next.js 16 (App Router), React 19, Tailwind CSS, Monaco Editor, Web Speech API, Vitest + Testing Library, Playwright.
**Backend:** FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, PostgreSQL (SQLite for local dev), Redis, Google Gen AI SDK, google-auth, Prometheus client, pytest + fakeredis, Locust.
**Infra:** Docker Compose, GitHub Actions, Vercel (frontend), Render (API + worker + Redis), Neon (PostgreSQL), Judge0 (code execution).

## Quick start

### Option A: local, no Docker (Windows PowerShell)

```powershell
copy .env.example .env.local      # then set SESSION_SECRET_KEY (and GEMINI_API_KEY if you have one)

cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn main:app --reload --port 8000     # SQLite is migrated automatically on startup
```

In a second terminal from the project root:

```powershell
npm install
npm run dev        # http://localhost:3000
```

Without `GEMINI_API_KEY` the app still runs: questions use templates and evaluations
are shown as "Not scored". Without Redis and a judge worker, curated DSA questions are
AI-reviewed and labelled as such.

### Option B: full stack with Docker Compose

```bash
cp .env.example .env    # set SESSION_SECRET_KEY and SANDBOX_SHARED_SECRET
docker compose up --build
```

This starts PostgreSQL, Redis, migrations, the API, the judge worker, the hardened
sandbox and the frontend on http://localhost:3000, with hidden-test judging enabled.

## Testing

| Suite | Command | Result at last run |
|---|---|---|
| Backend unit/integration | `cd backend && python -m pytest` | 230 passed |
| Frontend unit/component | `npm test` | 33 passed |
| End-to-end (desktop + mobile Chromium) | `npm run test:e2e` | 14 passed |
| Lint / build | `npm run lint`, `npm run build` | clean / OK |
| Grader benchmark (offline) | `python -m benchmarks.grader.run_benchmark --dataset benchmarks/grader/data/synthetic_seed.jsonl --grader fooled_model` | see below |
| Load test | `locust -f loadtests/locustfile.py ...` | see [`loadtests/RESULTS.md`](loadtests/RESULTS.md) |

CI also runs the Alembic migrations up, down and up again on a real PostgreSQL
service, runs the judge tests on Linux (where rlimits apply), validates
`docker-compose.yml` and builds all three images.

## Security model

| Concern | Control |
|---|---|
| Guest identity | HMAC-signed session tokens, revocable (`revoked_sessions`). |
| Accounts | Google OAuth (authorization code + PKCE, state, nonce), ID token verified (signature, audience, issuer, expiry, `email_verified`). |
| Session cookies | `HttpOnly`, `SameSite=Lax`, `Secure` in production; only SHA-256 hashes stored; expiry and logout revocation. |
| CSRF | Double-submit token bound to the session with HMAC, plus Origin allowlist, on every unsafe cookie-authenticated request. |
| Score integrity | Scores computed server-side; interview reports accept only HMAC-signed evaluation receipts; unavailable evaluations get no receipt. |
| Prompt injection | Untrusted-data blocks with random boundaries, delimiter neutralization, heuristics (prose + code comments/strings), model self-report, score cap, strict output schemas. |
| Untrusted code | Never in the API process. Judge0 or a sandbox container with CPU/memory/process/file limits, uid 65534, dropped capabilities, no-new-privileges, read-only root, internal-only network, HMAC-signed requests. |
| Abuse | Redis sliding-window rate limits (AI, judge, general, session start), queue backpressure, request size limits on every field. |
| Secrets | Loaded only from env; redacted from logs; `.env*` git-ignored; metrics and analytics summaries are token-protected. |
| Privacy | Analytics are anonymous daily aggregates from an allowlist; Do-Not-Track and Global Privacy Control are honored. Submitted code is deleted from Redis after judging. |

## AI grader benchmark

The pipeline is ready for 100+ human-labelled answers. The labeling protocol and CSV
template are in [`backend/benchmarks/grader/README.md`](backend/benchmarks/grader/README.md).
So far only **synthetic** offline runs exist. With the model assumed fully fooled
(`fooled_model`), the server-side defenses blocked all 10 synthetic injection attacks
and capped 0 of 31 honest answers. The attacks and the heuristics have the same author,
so this covers known patterns only. No human-agreement numbers are claimed yet.

## Deployment

Everything below runs on free plans. The frontend goes on Vercel, the database on
Neon, and the backend and Redis on Render. The code judge is switched off here,
because there is no free Judge0 plan anymore.

1. Neon: create a project and copy the connection string. It looks like
   `postgresql://user:password@host/db?sslmode=require`.
2. Render: create a new Blueprint from this repo. It reads `render.yaml` and makes
   one free web service and a free Redis. Fill in the values it asks for: the Neon
   URL, your Gemini key, and your Vercel URL for `FRONTEND_URL` and `CORS_ORIGINS`.
   The Google and Judge0 values are optional.
3. Vercel: import the repo and set `PYTHON_BACKEND_URL` to your Render URL.
4. Google sign-in (optional): create an OAuth client in Google Cloud Console, set the
   redirect URI to `https://<your-vercel-app>/api/auth/google/callback`, and put the
   ID and secret into Render.
5. Open `https://<your-render-app>/health`. You should see `"status": "ok"`.

How the free setup works:

Render's free plan has no background workers and no pre-deploy step, so
`backend/start.sh` does everything in one container. It runs the migrations, starts
the judge worker in the background (and restarts it if it crashes), then starts the API.

With the judge off, curated DSA answers are reviewed by the AI and labelled
"AI Generated" instead of "Verified". AI practice questions work the same way.
Hidden-test judging still works locally with `docker compose up --build`, which
runs the sandbox.

To turn the judge on later, get a Judge0 endpoint (RapidAPI's Judge0 CE is pay per
use) and set `JUDGE_ENABLED=true`, `JUDGE0_URL` and `JUDGE0_API_KEY` in Render.
`JUDGE0_DAILY_LIMIT` caps how many Judge0 requests the backend makes per day.

A free Render service sleeps after about 15 minutes without traffic, so the first
request after that takes around a minute. The free Redis is not persistent, which
is fine here: it only holds the judge queue, rate limits, the cache and AI practice
questions, which expire anyway.

If you want to run the whole stack yourself instead, `docker compose up --build`
starts everything locally, including the self-hosted sandbox.

## Known limitations

- The human-labelled benchmark has not been collected; grader accuracy against humans is unmeasured.
- Each curated DSA question has 3 hidden tests; more edge cases would make verdicts stricter.
- Sample tests for AI-generated problems, and the reference solution used to cross-check them, come from the same model. Cross-checking removes inconsistent tests but cannot prove the remaining expected outputs correct, so these results are never shown as verified.
- AI-generated problems support plain-value signatures only (ints, floats, strings, booleans and lists of them); linked-list, tree and design-style problems fall back to AI review.
- A generated problem is stored for 6 hours and is tied to the session that created it; signing in mid-problem requires generating it again.
- Judge0 and the Docker sandbox have not been exercised end to end on this machine (no Docker locally); CI builds the images, and the harness is tested through a real subprocess.
- The self-hosted sandbox relies on container hardening, so on a PaaS without those controls use Judge0.
- Guest sessions still use localStorage tokens (signed accounts use HttpOnly cookies).
- In-memory fallbacks (no Redis) are per-process, which is fine for local dev but not for multiple instances.
- Load-test numbers are from a single local process; production numbers are pending deployment.

## Project structure

```text
backend/
  main.py, config.py            app setup, single source of configuration
  auth.py, security.py          Google OAuth + cookie sessions + CSRF; guest HMAC sessions, receipts
  services/llm.py               async LLM gateway (structured output, retries, circuit breaker)
  services/grading/             prompts (versioned), rubrics, schemas, injection defenses, evaluators
  judge/                        queue, worker, executors, sandbox server, harness, verdicts
  benchmarks/grader/            grader benchmark (dataset, graders, metrics, CLI)
  analytics.py                  anonymous aggregates + per-user progress
  rate_limit.py, cache.py       Redis sliding window, safe cache
  observability.py              JSON logs, request ids, Prometheus metrics
  alembic/versions/             0001 schema, 0002 evaluation status, 0003 auth, 0004 analytics
  tests/                        pytest suites
src/
  app/                          pages and /api proxy routes
  components/                   feature cards + dsa/, project/, dashboard/, ui/
  hooks/                        workspace, speech, voice explanation, local history, judge status
  lib/                          API client, backend proxy, scoring, analytics
e2e/                            Playwright tests
loadtests/                      Locust scenario and results
docker-compose.yml, render.yaml, Dockerfile, backend/Dockerfile, backend/Dockerfile.sandbox
```

Implementation progress, blockers and test history: [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md).
