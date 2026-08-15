# ConceptVivaAI - Topic-wise AI Mock Interview Platform

ConceptVivaAI is a full-stack platform for practicing technical interviews and coding problems with AI-generated feedback. It covers topic-wise ML interview practice, a two-tier DSA practice system, project/hackathon-style challenges, and a voice-based mock interview mode.

## Features

- **ML Topic Practice** - AI generates topic-wise interview questions (or picks a topic automatically), evaluates answers semantically, and gives feedback with a corrected answer and follow-up question.
- **Voice Mock Interview** - AI speaks the question out loud, listens to a spoken answer using the browser's speech recognition, evaluates it, and asks a natural follow-up. Ends with a final performance report (strong points, weak points, recommendation).
- **DSA Coding Practice — Two-Tier system:**
  - **Verified Bank** - 90 curated LeetCode-style questions (exactly 3 Easy / 4 Medium / 3 Hard per topic, across 9 topics), each with hidden test cases. When `ENABLE_CODE_EXECUTION=true`, submissions run against those hidden tests for deterministic scoring.
  - **AI Practice** - the student types any topic (e.g. "Segment Trees", "Tries"), and Gemini generates a fresh question on demand with its own proper method signature. Scored by AI review, not hidden tests, since there's no fixed answer key.
  - Every generated question and every evaluation response carries an explicit `tier` (`verified` / `ai_generated`), and the dashboard reports the two separately instead of averaging a hidden-test score together with an AI-review score.
- **DSA Mock Set** - 10-question mixed mock set (3 Easy / 4 Medium / 3 Hard) pulled from the curated bank.
- **Project Challenge Mode — Full Source Submission** - AI generates a hackathon-style project challenge (problem statement, dataset schema, tasks, evaluation metrics, hints) across Machine Learning, Data Analytics, DSA, and System Design domains. The student selects their complete project folder (not just a text description); the backend does a real cross-file code review — architecture, concrete bugs with file/severity, security issues, and missing requirements — and persists the full review (and the actual submitted source) so it's still there after a refresh or in History, not just in the one-time response.
- **Dashboard** - Tracks attempts, average scores, and topic-wise readiness across all four modes, pulling data from the backend database. DSA stats are further split by tier (Verified vs AI Generated).
- **Session-based auth** - No login required; each browser gets a signed session token used to scope saved attempts.

## Tech Stack

**Backend**
- FastAPI (Python), layered as routes → services → models (no business logic in route handlers)
- SQLAlchemy + SQLite (swappable via `DATABASE_URL`)
- Google Gemini API (`gemini-2.5-flash`) for question generation and evaluation
- HMAC-signed session tokens

**Frontend**
- Next.js (App Router)
- React
- Tailwind CSS
- Monaco Editor (for the DSA code editor)
- Web Speech API (speech recognition + speech synthesis) for the voice interview mode

## Project Structure

```
backend/
  main.py            Thin FastAPI entrypoint: app setup, CORS, router registration
  config.py          Env loading and constants (GEMINI_API_KEY, ENABLE_CODE_EXECUTION, ...)
  schemas.py         Pydantic request models for every route
  serializers.py      ORM row -> JSON response converters
  utils.py            Small stateless helpers (extract_json, format_datetime, ...)
  models.py           SQLAlchemy models
  crud.py             Database helper functions + dashboard stats (tier-split for DSA)
  database.py         DB engine/session setup
  security.py         Session creation, verification, revocation
  dsa_runner.py        Local hidden-test judge for curated DSA questions
  rate_limit.py        Per-session request rate limiting
  routes/              HTTP layer - one router per feature area
    session_routes.py, dsa_routes.py, interview_routes.py, ml_routes.py,
    project_routes.py, dashboard_routes.py, translate_routes.py
  services/            Business logic / Gemini layer, called by routes
    gemini_client.py    Single shared Gemini client (load-once)
    dsa_bank.py          Curated question bank loader
    dsa_service.py       DSA generation, evaluation, tier logic (both tiers)
    interview_service.py ML/interview question generation + evaluation
    project_service.py   Project challenge generation + evaluation
    translate_service.py Hindi translation
  data/
    dsa_question.py    Curated DSA question bank (90 questions)

src/
  app/
    page.js          Home page (domain selector)
    ml/page.js        ML practice + voice interview + project challenge
    dsa/page.js        DSA practice page
    dashboard/page.js  Dashboard (with tier-split DSA stats)
    api/               Next.js API routes that proxy to the FastAPI backend
  components/          DSAPracticeCard (Two-Tier UI), InterviewCard, MLPracticeCard,
                       ProjectChallengeCard, ResultCard, Navbar
  utils/session.js      Session management (create/refresh/logout)
```

## Setup

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env.local` file in the `backend` folder:

```
GEMINI_API_KEY=your_gemini_api_key_here
SESSION_SECRET_KEY=some_random_secret_string
SESSION_TTL_SECONDS=2592000
DATABASE_URL=sqlite:///./conceptviva.db
FRONTEND_URL=http://localhost:3000
ENABLE_CODE_EXECUTION=false
```

Run the backend:

```bash
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
npm install
```

Create a `.env.local` file in the project root:

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Run the frontend:

```bash
npm run dev
```

The app will be available at `http://localhost:3000`.

## Notes on the Two-Tier DSA system

- **`ENABLE_CODE_EXECUTION`** controls whether submitted DSA solutions actually run against hidden tests, or are evaluated by Gemini alone. It defaults to `false` because raw subprocess execution of student-submitted Python is not a security boundary — only enable it in a trusted/sandboxed environment. When it's `false`, the frontend shows an explicit warning in Verified mode instead of silently claiming hidden-test scoring it isn't performing.
- **`tier`** is computed server-side, never assumed by the frontend: `"verified"` only when a question resolves to a real curated-bank question *and* `ENABLE_CODE_EXECUTION` is true; otherwise `"ai_generated"`. This is stored per-attempt (`DSAAttempt.tier`) so the dashboard never averages a hidden-test score together with an AI-review score.
- **AI Practice repeat-avoidance**: the frontend keeps the last 15 generated titles per topic (in memory, per browser session) and sends them back on the next generation call so Gemini is told not to repeat them, alongside a random variation key on every call.
- If `GEMINI_API_KEY` is missing or the API call fails, every endpoint falls back to a canned response (or the curated bank, where relevant) instead of crashing, so the app stays usable.