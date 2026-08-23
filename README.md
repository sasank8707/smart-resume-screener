# Smart Resume Screener

A production-quality resume screening platform: upload resumes (PDF/TXT), parse them
into structured candidate profiles, match them against job descriptions with an LLM,
and review **ranked, explainable 1–10 match scores** in a clean web dashboard.

## Live Demo

- **Frontend Application**: [https://smart-resume-screener-nu.vercel.app](https://smart-resume-screener-nu.vercel.app)
- **Backend API**: [https://smart-resume-screener-api-bpfh.onrender.com](https://smart-resume-screener-api-bpfh.onrender.com)

---

## Table of contents

1. [Overview](#overview)
2. [Problem statement](#problem-statement)
3. [Features](#features)
4. [Architecture](#architecture)
5. [Technology stack](#technology-stack)
6. [Project structure](#project-structure)
7. [Installation](#installation)
8. [Environment variables](#environment-variables)
9. [Database setup](#database-setup)
10. [Running the backend](#running-the-backend)
11. [Running the frontend](#running-the-frontend)
12. [Running tests](#running-tests)
13. [LLM configuration](#llm-configuration)
14. [LLM prompts](#llm-prompts)
15. [API documentation](#api-documentation)
16. [Example workflow](#example-workflow)
17. [Screenshots](#screenshots)
18. [Demo video script](#demo-video-script)
19. [Deployment](#deployment)
20. [Future improvements](#future-improvements)

---

## Overview

Recruiters and hiring teams receive dozens of resumes per opening. Reading each one
manually against the job description is slow, inconsistent and hard to justify.
Smart Resume Screener automates the first pass: it extracts structured data from
every resume, semantically compares candidates against the role's requirements using
an LLM, scores the fit from 1–10 with a written justification, ranks candidates and
shortlists everyone at or above a configurable threshold.

## Problem statement

Manual screening suffers from three concrete problems:

| Problem | Consequence | How this project helps |
| --- | --- | --- |
| Resume formats are unstructured | Key facts (skills, experience, education) are buried in free text | Reliable PDF/TXT text extraction + structured parsing pipeline |
| Human screening is inconsistent | Similar candidates get different treatment; reasoning isn't recorded | Consistent rubric-based scoring; every score stored with its justification |
| No audit trail of decisions | "Why was this candidate rejected?" has no answer | Every screening result persists strengths, missing requirements and full explanation |

## Features

- 📄 **Resume ingestion** — batch upload PDF and TXT resumes with validation
  (file type, size limit), robust text extraction, and explicit per-file error
  reporting (scanned/corrupt PDFs never fail silently).
- 🔍 **Structured extraction** — name, email, phone, atomic skills,
  experience entries (organization, role, duration, responsibilities, technologies),
  education entries (institution, degree, field, years), certifications.
  Missing data stays `null` — nothing is invented.
- ☰ **Job description workflow** — create/edit/delete roles; required vs preferred
  skills, experience expectations and responsibilities are extracted automatically.
- 🧠 **LLM semantic matching** — provider abstraction (OpenAI / any OpenAI-compatible
  endpoint / Anthropic Claude / built-in offline scorer) behind one interface;
  API keys only via environment variables.
- ✅ **Output validation** — every LLM response is parsed and schema-validated with
  safe recovery + retry + deterministic fallback; malformed output can't crash a run.
- ★ **Explainable ranking** — 1–10 score, justification, strengths, missing
  requirements, experience/education alignment, recommendation and confidence;
  shortlist threshold configurable (default 7).
- 🗃 **Persistence** — relational models for candidates/resumes, job descriptions
  and screening results (SQLite locally, PostgreSQL-compatible design) with Alembic
  migrations.
- 📊 **Dashboard & filtering** — stats cards, recent activity, search/filter by
  score, shortlist status, skill, job or candidate name; sorting by score/name/date.
- 🔒 **Security basics** — no secrets in code, `.env.example` provided, filename
  sanitisation, upload limits, generic error envelopes that never leak internals.
- 🌐 **Responsive UI** — modern SaaS-style dashboard usable on desktop and mobile.

## Architecture

```mermaid
flowchart LR
    A[Resume upload\nPDF / TXT] --> B[Text extraction\npypdf]
    B --> C[Structured parsing\nheuristic pipeline]
    C --> D[(candidates\ntable)]
    E[Job description\ncreate / edit] --> F[Requirement extraction\nrequired vs preferred]
    F --> G[(job_descriptions\ntable)]
    D --> H[Screening pipeline]
    G --> H
    H --> I{LLM provider\nopenai / anthropic / mock}
    I --> J[JSON validation\nretry + fallback]
    J --> K[Score 1-10 + justification\nranking + shortlist]
    K --> L[(screening_results\ntable)]
    L --> M[Dashboard\nstats · filters · detail views]
```

### Data flow

```
Resume → Text Extraction → Structured Parsing → Candidate Data
       → Job Description  → LLM Matching      → Score + Justification
       → Ranking          → Shortlist         → Database → Dashboard
```

The frontend (React SPA) talks only to the FastAPI backend via `/api/*`; the backend
is the sole owner of database access and LLM credentials.

## Technology stack

| Layer | Technology | Why |
| --- | --- | --- |
| Frontend | React 19 + TypeScript + Vite | Fast DX, typed API layer, small bundle |
| Routing | React Router 7 | Standard SPA navigation |
| Styling | Hand-rolled CSS design system | Zero dependency weight, consistent look |
| Backend | Python 3.12+ / FastAPI + Uvicorn | Typed endpoints, automatic OpenAPI docs |
| ORM | SQLAlchemy 2 + Alembic | Portable SQLite→PostgreSQL, migrations |
| PDF extraction | pypdf | Pure-python, reliable text-layer extraction |
| LLM access | `httpx` against provider REST APIs | One abstraction, no SDK lock-in |
| Validation | Pydantic v2 | Schemas for both HTTP I/O and LLM output |
| Tests | pytest (+ Vitest/RTL on frontend) | Fast, isolated, meaningful coverage |

## Project structure

```
smart-resume-screener/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, error envelope
│   │   ├── api/routes/           # candidates, jobs, screening, stats
│   │   ├── core/                 # settings (.env), database engine
│   │   ├── llm/                  # provider abstraction + output validation
│   │   ├── models/__init__.py    # Candidate, JobDescription, ScreeningResult
│   │   ├── schemas/__init__.py   # request/response schemas
│   │   ├── services/             # extraction, parsers, screening pipeline
│   │   └── prompts.py            # canonical LLM prompt templates
│   ├── alembic/                  # migrations (env + versions)
│   ├── tests/                    # pytest suite (69 tests)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/client.ts         # typed fetch wrapper (single place for /api)
│   │   ├── components/           # sidebar, toasts, score bars, empty states
│   │   ├── pages/                # Dashboard, Upload, Jobs, Candidates,
│   │   │                         # ScreeningResults, Settings
│   │   └── styles.css            # design system
│   └── package.json
├── prompts/                      # human-readable prompt documentation
├── sample-data/
│   ├── resumes/                  # fictional strong/medium/weak resumes (txt+pdf)
│   └── job-descriptions/
├── scripts/generate_sample_pdfs.py
├── render.yaml                   # backend deploy blueprint (Render)
├── frontend/vercel.json          # frontend deploy config (Vercel)
├── DEPLOYMENT.md                 # step-by-step deployment guide
└── README.md
```

## Installation

Prerequisites: **Python 3.12+**, **Node.js 18+**, git.

```bash
git clone https://github.com/sasank8707/smart-resume-screener.git
cd smart-resume-screener

# Backend
python -m venv .venv
.\.venv\Scripts\activate              # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

## Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in what you need
(**never commit `.env`**):

| Variable | Default | Purpose |
| --- | --- | --- |
| `LLM_PROVIDER` | `mock` | `mock`, `openai` or `anthropic` |
| `OPENAI_API_KEY` | — | key for OpenAI-compatible providers |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | point at Groq/Ollama/etc. |
| `OPENAI_MODEL` | `gpt-4o-mini` | chat model name |
| `ANTHROPIC_API_KEY` | — | key for Anthropic |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-...` | model id |
| `SHORTLIST_THRESHOLD` | `7` | default shortlist cutoff (1–10) |
| `MAX_UPLOAD_SIZE_MB` | `10` | per-file upload cap |
| `DATABASE_URL` | SQLite file | use PostgreSQL URL in production |
| `CORS_ORIGINS` | localhost:5173 | comma-separated allowed origins |

The frontend optionally takes `VITE_API_URL` at build time (defaults to `/api`
with the Vite dev proxy → `http://localhost:8000`).

## Database setup

Local development needs **zero setup**: on startup the backend creates
`backend/smart_resume_screener.db` automatically (SQLite).

For schema evolution use Alembic:

```bash
cd backend
alembic upgrade head        # apply all migrations
alembic downgrade base      # roll back everything
```

Production simply points `DATABASE_URL` at a PostgreSQL instance
(e.g. `postgresql+psycopg://user:pass@host:5432/db`) — the models use only
portable column types.

## Running the backend

```bash
# from the repo root
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

- API root: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/api/docs>

(Windows note: if you activated the venv you can drop the path prefix.)

## Running the frontend

```bash
cd frontend
npm run dev
```

Open <http://localhost:5173> — the dev server proxies `/api/*` to port 8000.

## Running tests

```bash
# Backend (from repo root)
.\.venv\Scripts\python.exe -m pytest backend/tests -q

# Frontend
cd frontend && npm test
```

Backend coverage includes extraction (valid/corrupt/scanned PDFs, encodings),
resume parsing, JD requirement extraction, LLM JSON recovery + schema validation,
screening logic (ranking, shortlisting, upserts) and every API endpoint.
Frontend tests cover navigation, dashboard data rendering, error states and
upload validation.

## LLM configuration

Out of the box the app runs fully offline: `LLM_PROVIDER=mock` activates a
deterministic rubric scorer (skill overlap, experience-vs-expectation ratio,
education signal) so uploads/screening work without any API key. The Settings
page always shows which provider is active.

To enable real LLM matching, set in `backend/.env`:

```ini
LLM_PROVIDER=openai                      # OpenAI, Groq, Together, Ollama...
OPENAI_API_KEY=sk-...                    # your key — keep it out of Git
OPENAI_MODEL=gpt-4o-mini

# or
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Restart the backend. Screening results will then be labelled with the provider
and model used (`mock-fallback` means the LLM failed validation and the offline
scorer produced the result instead).

## LLM prompts

All prompts live in [`backend/app/prompts.py`](backend/app/prompts.py) (single
source of truth) and are documented with rationale in [`prompts/`](prompts/):

1. **Resume extraction** ([prompts/1-resume-extraction.md](prompts/1-resume-extraction.md)) —
   converts raw resume text into the canonical candidate JSON; anti-hallucination
   rules force `null`s over invented data.
2. **Job-description extraction** ([prompts/2-job-description-extraction.md](prompts/2-job-description-extraction.md)) —
   separates required vs preferred skills, experience/education expectations.
3. **Semantic matching** ([prompts/3-resume-job-matching.md](prompts/3-resume-job-matching.md)) —
   the core screener: anchored 1–10 rubric, required/preferred weighting, strict
   evidence-only reasoning, structured JSON verdict.

Every response passes through `MatchResult` validation with retry and a
deterministic fallback before anything touches the database.

## API documentation

Interactive docs are auto-generated at **`/api/docs`** (Swagger) and `/api/redoc`.
Main endpoints:

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/auth/register` | Register a new user account |
| POST | `/api/auth/login` | Log in and obtain JWT access token |
| GET | `/api/auth/me` | Fetch authenticated user details |
| POST | `/api/candidates/upload` | Batch-upload PDF/TXT resumes (Private to user) |
| GET | `/api/candidates?q=&skill=` | List/search candidates (Private to user) |
| GET | `/api/candidates/{id}` | Full candidate detail incl. raw text (Private to user) |
| DELETE | `/api/candidates/{id}` | Delete candidate + their results (Private to user) |
| POST/GET/PATCH/DELETE | `/api/jobs[...]` | Job description CRUD (Private to user) |
| POST | `/api/screening/run` | Screen candidates against a job (Private to user) |
| GET | `/api/screening/results?min_score=&shortlisted_only=&skill=&q=&sort_by=&order=` | Filter/sort results (Private to user) |
| GET | `/api/stats` | Dashboard statistics (Private to user) |
| GET | `/api/health` | Health + active LLM provider (Public) |

Errors return a uniform envelope:
`{"error": {"message": "...", "status": 422}}` — internal exceptions are logged
server-side but never exposed to clients.

## Example workflow

```bash
# 1. Register a user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepassword"}'

# 2. Login to get token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepassword"}'
# Keep the token for subsequent requests

# 3. Upload resumes
curl -H "Authorization: Bearer <token>" \
     -F "files=@sample-data/resumes/resume_strong_aarav_sharma.pdf" \
     http://localhost:8000/api/candidates/upload

# 4. Create a job description (paste any posting ≥30 chars)
curl -X POST http://localhost:8000/api/jobs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Senior Python Backend Engineer","description_text":"<paste>"}'

# 5. Screen candidates 1 against job 1
curl -X POST http://localhost:8000/api/screening/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"job_description_id":1,"candidate_ids":[1]}'
```

Or do the same in the UI: **Register/Sign In → Upload Resumes → Job Descriptions → Screening Results → Run → inspect the ranked table.**

Sample data: `sample-data/resumes/` contains fictional strong (Aarav Sharma),
medium (Priya Nair) and weak (Rohan Mehta) candidates as TXT *and* generated PDFs,
plus a matching job description under `sample-data/job-descriptions/`.

## Screenshots

> _Add screenshots here after your first local run._

| Page | What to capture |
| --- | --- |
| Dashboard | Stat cards + recent activity table |
| Upload Resumes | Dropzone with parsed-candidate chips |
| Job Descriptions | Extracted requirement tags |
| Screening Results | Ranked table with expanded justification |

## Demo video script (2–3 minutes)

Record with the sample dataset pre-loaded (or load it live — it's fast):

1. **0:00–0:20 — Problem & product intro.** Dashboard open. “Recruiters read dozens
   of resumes per role. This app parses them, matches them to the job with an LLM,
   and explains every score.”
2. **0:20–0:50 — Upload.** Go to *Upload Resumes*. Drag in the three sample resumes
   (PDF + TXT). Point out per-file success/error feedback and the parsed skill counts.
3. **0:50–1:15 — Job description.** Open *Job Descriptions* → show the extracted
   **required vs preferred skills** and experience bar for the Senior Python role.
4. **1:15–2:00 — Screening run.** On *Screening Results*: pick the job, select all
   candidates, set the threshold slider to 7, hit **Run**. Walk the ranked table:
   Aarav shortlisted (strong match), Rohan not shortlisted — expand his row to show
   **missing requirements and the justification**.
5. **2:00–2:30 — Explainability & wrap-up.** Show candidate detail view (structured
   experience/education), then Settings showing the active LLM provider. Close with:
   “Every decision is persisted and explainable.”

## Deployment

The project is fully configured and live in production:

- **Live Frontend Application**: [https://smart-resume-screener-nu.vercel.app](https://smart-resume-screener-nu.vercel.app) (Deploys static build to Vercel via [`frontend/vercel.json`](frontend/vercel.json) with `VITE_API_URL` pointing to the Render endpoint).
- **Live Backend API**: [https://smart-resume-screener-api-bpfh.onrender.com](https://smart-resume-screener-api-bpfh.onrender.com) (Deploys FastAPI web service to Render via [`render.yaml`](render.yaml)).
- **Database**: PostgreSQL database provisioned on Render, persistent database migrations executed via Alembic on startup.
- All secrets and API keys are stored securely in platform dashboards — never in the repository.

## Future improvements

- Async background screening (task queue) for large batches with live progress.
- OCR fallback (e.g. Tesseract) for scanned-image PDFs.
- Role-based access controls (RBAC) for recruiter teams.
- Score calibration reports: compare LLM recommendations vs recruiter outcomes.
- Resume–job keyword highlighting in the UI for faster human verification.
- Docker Compose file for one-command self-hosting.

