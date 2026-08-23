# Deployment Guide

This project deploys as two pieces:

| Piece | Recommended host (free tier) | Config in repo |
| --- | --- | --- |
| Backend API | [Render](https://render.com) Web Service + PostgreSQL | `render.yaml` |
| Frontend SPA | [Vercel](https://vercel.com) or Netlify static deploy | `frontend/vercel.json` |

> **Heads-up:** creating cloud resources requires you to log in to Render/Vercel
> with your own account (and add a card on some free tiers). The repository ships
> everything needed; the manual clicks below are the parts that can't be automated
> without your credentials.

---

## 1. Backend on Render

1. Push this repository to GitHub (already done — see below).
2. In Render: **New → Blueprint**, select the repo. Render reads `render.yaml`
   and provisions:
   - a FastAPI web service (`pip install -r backend/requirements.txt`,
     start command runs Alembic migrations then Uvicorn),
   - a free PostgreSQL instance, wired to the service via `DATABASE_URL`.
3. Add environment variables in the Render dashboard (**do not commit them**):
   - `LLM_PROVIDER` = `openai` or `anthropic` (or keep `mock`)
   - `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` = your key
   - `CORS_ORIGINS` = your frontend URL(s), e.g.
     `https://smart-resume-screener.vercel.app`
4. Deploy. Verify: `curl https://<your-service>.onrender.com/api/health`
   → `{"status":"ok","database":"ok", ...}`.

## 2. Frontend on Vercel

1. In Vercel: **Add New → Project**, import the same GitHub repo.
2. Settings:
   - Root directory: `frontend`
   - Build command: `npm run build`, output: `dist`
   - Environment variable `VITE_API_URL` =
     `https://<your-service>.onrender.com/api`
3. Deploy and open the assigned URL.

Netlify works identically: build `frontend`, publish `dist`, set
`VITE_API_URL`; use the redirects in `vercel.json` as a reference for SPA routing.

## 3. Post-deploy verification checklist

- [ ] Frontend loads at its URL.
- [ ] Dashboard shows stats (Settings page shows provider + DB status).
- [ ] Upload `sample-data/resumes/resume_strong_aarav_sharma.pdf`.
- [ ] Create the sample job description from
      `sample-data/job-descriptions/senior_python_backend_engineer.txt`.
- [ ] Run screening; confirm scores + justifications appear.
- [ ] Reload the page — results persist (database round-trip OK).
- [ ] Upload a corrupt file — a friendly error appears, nothing crashes.

## Notes

- Render free instances sleep after inactivity; first request may take ~30s.
- SQLite is only used when no `DATABASE_URL` is provided (local dev). On Render,
  the blueprint always attaches PostgreSQL.
- Never put API keys in Git history; rotate keys immediately if leaked.
