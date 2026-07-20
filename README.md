# ConceptVivaAI - Topic-wise AI Mock Interview Platform

ConceptVivaAI is a full-stack platform for practicing technical interviews and coding problems with AI-generated feedback. It covers topic-wise ML interview practice, LeetCode-style DSA practice, project/hackathon-style challenges, and a voice-based mock interview mode.

## Features

- **ML Topic Practice** - AI generates topic-wise interview questions (or picks a topic automatically), evaluates answers semantically, and gives feedback with a corrected answer and follow-up question.
- **Voice Mock Interview** - AI speaks the question out loud, listens to a spoken answer using the browser's speech recognition, evaluates it, and asks a natural follow-up. Ends with a final performance report (strong points, weak points, recommendation).
- **DSA Coding Practice** - LeetCode-style questions (title, difficulty badge, examples, constraints, starter code) generated from a curated question bank. Supports single-question practice mode and a 10-question mixed mock set (3 Easy / 4 Medium / 3 Hard).
- **Project Challenge Mode** - AI generates a hackathon-style project challenge (problem statement, dataset schema, tasks, evaluation metrics, hints) across Machine Learning, Data Analytics, DSA, and System Design domains, then reviews the submitted approach.
- **Dashboard** - Tracks attempts, average scores, and topic-wise readiness across all four modes, pulling data from the backend database.
- **Session-based auth** - No login required; each browser gets a signed session token used to scope saved attempts.

## Tech Stack

**Backend**
- FastAPI (Python)
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
  main.py            FastAPI app, routes, Gemini prompts
  models.py          SQLAlchemy models
  crud.py            Database helper functions
  database.py        DB engine/session setup
  security.py        Session creation, verification, revocation
  data/
    dsa_question.py  Curated DSA question bank

src/
  app/
    page.js          Home page (domain selector)
    ml/page.js        ML practice + voice interview + project challenge
    dsa/page.js        DSA practice page
    dashboard/page.js  Dashboard
    api/               Next.js API routes that proxy to the FastAPI backend
  components/          DSAPracticeCard, InterviewCard, MLPracticeCard,
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

## Notes

- `ENABLE_CODE_EXECUTION` controls whether submitted DSA solutions are actually run against test cases (Arrays, Strings, Stack, Binary Search, Dynamic Programming) or evaluated by Gemini alone. Keep this `false` unless you trust the execution environment, since it runs user-submitted Python code.
- If `GEMINI_API_KEY` is missing or the API call fails, every endpoint falls back to a canned response instead of crashing, so the app stays usable.