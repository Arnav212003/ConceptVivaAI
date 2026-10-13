# ConceptVivaAI

ConceptVivaAI is my full-stack practice platform for technical interview preparation. I built it to practice topic-wise interviews while learning ML, DSA, system design basics, FastAPI, Next.js, and AI API integration.

The project is still evolving, but the current version supports AI-based practice, DSA coding practice, voice interview rounds, project challenge reviews, dashboard tracking, and session handling.

## What It Does

- Generates ML and interview questions based on a selected topic or an AI-selected topic.
- Evaluates answers using Gemini and gives feedback, missing points, corrected answers, and follow-up questions.
- Provides DSA practice with a curated question bank and AI-generated practice questions.
- Supports a DSA mock set with mixed difficulty questions.
- Includes a voice interview mode using browser speech recognition and speech synthesis.
- Generates project challenges and reviews submitted source folders.
- Tracks saved attempts in SQLite locally, with PostgreSQL support for deployment.
- Uses signed session tokens so each browser session has its own history without a login page.

## Why I Built It

I wanted one project that connects multiple things I am learning as a BTech CSE student:

- backend APIs with FastAPI
- frontend development with Next.js and React
- database models with SQLAlchemy
- AI integration with Gemini
- basic security improvements such as signed sessions and server-side score handling
- practical interview-preparation workflows

This is not meant to be a big-company product. It is a student portfolio project with real features, simple architecture, and enough production-style thinking to discuss in interviews.

## Tech Stack

**Frontend**

- Next.js App Router
- React
- Tailwind CSS
- Monaco Editor for the DSA code editor
- Web Speech API for voice interview mode

**Backend**

- FastAPI
- SQLAlchemy
- SQLite for local development
- PostgreSQL support for deployment
- Alembic migrations
- Pydantic
- Google Gemini API
- HMAC-signed session tokens

## Main Features

### ML Practice

- Topic-wise AI-generated questions
- Answer evaluation with score, feedback, missing points, and corrected answer
- Optional AI-selected topic when the user leaves the topic blank
- Saved practice attempts shown on the dashboard

### DSA Practice

- Curated DSA question bank
- AI practice mode for custom topics like Segment Trees, Tries, or Graphs
- Monaco-based Python editor
- AI feedback with optimized approach, explanation, and complexity
- Tier tracking for verified-bank questions vs AI-generated questions

### Voice Interview

- Browser speech recognition for spoken answers
- AI-generated interview questions and follow-ups
- Round-wise scoring
- Final report with strong points, weak points, and recommendation
- Signed evaluation receipts so final reports are based on backend-generated scores

### Project Challenge

- AI-generated mini project challenges
- Full source-folder submission from the browser
- Backend review for architecture, bugs, missing requirements, and security issues
- Project attempts saved to database history

### Dashboard

- Total attempts across ML, DSA, project, and voice interview modes
- Average score tracking
- Topic-wise readiness
- Recent activity history
- DSA stats split by verified and AI-generated tiers

## Folder Structure

```text
backend/
  main.py                 FastAPI app setup and router registration
  config.py               Environment variable loading
  database.py             SQLAlchemy engine and session setup
  models.py               Database tables
  alembic/                Database migrations
  alembic.ini             Alembic configuration
  schemas.py              Pydantic request models
  crud.py                 Database helper functions
  security.py             Session tokens, logout, and score receipts
  rate_limit.py           Simple in-memory rate limiting
  dsa_runner.py           Local DSA runner for supported curated questions
  routes/                 FastAPI route files
  services/               Gemini and feature logic
  data/                   Curated question data
  tests/                  Backend tests

src/
  app/                    Next.js pages and API proxy routes
  components/             Reusable UI components
  utils/session.js        Frontend session helper
```

## Environment Setup

The project reads backend environment variables from the root `.env.local` file. Backend-only overrides can also be placed in `backend/.env`.

Do not commit real API keys. Use dummy values in examples and keep real values only in local env files.

Create this file in the project root:

```env
# Frontend
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
PYTHON_BACKEND_URL=http://127.0.0.1:8000

# Backend
GEMINI_API_KEY=your_dummy_gemini_api_key
SESSION_SECRET_KEY=replace_with_a_long_random_local_secret
SESSION_TTL_SECONDS=2592000
DATABASE_URL=sqlite:///./conceptviva.db
FRONTEND_URL=http://localhost:3000

# Local SQLite:
# DATABASE_URL=sqlite:///./conceptviva.db

# Production PostgreSQL:
# DATABASE_URL=postgresql+psycopg2://username:password@host:5432/database_name

# Keep false unless you are running code in a trusted sandbox.
ENABLE_CODE_EXECUTION=false

# Optional rate limits
AI_REQUESTS_PER_MINUTE=20
GENERAL_REQUESTS_PER_MINUTE=120
SESSION_STARTS_PER_MINUTE=20
```

## Run Backend on Windows PowerShell

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
alembic upgrade head
uvicorn main:app --reload --port 8000
```

Backend URL:

```text
http://localhost:8000
```

If PowerShell blocks virtualenv activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Run Frontend on Windows PowerShell

Open a second terminal from the project root:

```powershell
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

If PowerShell blocks `npm.ps1`, use:

```powershell
npm.cmd run dev
```

## Useful Checks

Frontend:

```powershell
npm run lint
npm run build
```

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pytest
```

## Database and Migrations

For local development, SQLite is still the simplest option:

```env
DATABASE_URL=sqlite:///./conceptviva.db
```

For deployment, use PostgreSQL through `DATABASE_URL`:

```env
DATABASE_URL=postgresql+psycopg2://username:password@host:5432/database_name
```

The backend also accepts plain `postgresql://...` URLs and normalizes them for the `psycopg2` driver.

Alembic is now included for database schema changes:

```powershell
cd backend
alembic revision --autogenerate -m "message"
alembic upgrade head
```

`Base.metadata.create_all(bind=engine)` is still kept as a small SQLite-only local fallback, so first-time users do not get stuck if they run the backend before learning migrations. For a deployed PostgreSQL backend, run `alembic upgrade head` before starting the app.

If you already have an old local SQLite database created before Alembic, either back it up and delete the local `.db` file for a fresh start, or run `alembic stamp head` after confirming the tables already match the models.

## Deployment Database Note

SQLite is useful for local learning, but it is not a good choice for deployed data on platforms with ephemeral filesystems. On Render and similar platforms, local SQLite files can be lost after redeploys or restarts.

For deployment, use PostgreSQL. Render Free Postgres is useful for demos, but it expires after 30 days. For a longer-running deployment, use paid Render Postgres or an external PostgreSQL provider such as Supabase, Neon, Railway, or Aiven.

This does not make the project a full production SaaS. It simply makes the student portfolio project easier to deploy and closer to real backend practice.

## Security Improvements Already Added

- Session IDs and tokens are signed with HMAC.
- Logout revokes the current session token.
- Interview reports use signed evaluation receipts, so the browser cannot freely choose the final average.
- Legacy save endpoints re-evaluate answers on the backend instead of trusting client-provided scores.
- Basic request size limits are added for answers, DSA solutions, and project source files.
- AI endpoints have simple in-memory rate limiting.
- `.env` files, SQLite databases, virtual environments, build folders, and dependency folders are ignored by Git.
- DSA code execution is disabled by default because raw Python subprocess execution is not a strong sandbox.

## Important Notes

- Gemini feedback is useful for practice, but it is still AI-based feedback and may not always be perfect.
- SQLite is fine for this project stage. For a deployed multi-user version, PostgreSQL would be better.
- Alembic migrations should be used for deployed database changes.
- The local DSA runner is for supported curated questions and should only be enabled in a trusted sandbox.
- Session tokens are currently stored in browser local storage. A more secure deployed version should use HttpOnly cookies.

## Future Improvements

- Expand Alembic migration coverage as the schema changes.
- Move DSA code execution to a real sandbox or external judge service.
- Use cookie-based sessions instead of local storage tokens.
- Add more FastAPI integration tests for routes, auth, dashboard, and project flow.
- Add stronger project-file secret scanning before storing submitted source.
- Improve mobile UI polish and accessibility.
- Add more curated DSA questions and topic coverage.

## Current Status

This project is built to be understandable and explainable in interviews. The architecture is intentionally simple: Next.js handles the UI and API proxy routes, FastAPI handles backend logic, SQLite/PostgreSQL stores attempts, and Gemini powers question generation and feedback.
