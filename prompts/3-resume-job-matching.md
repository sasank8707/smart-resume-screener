# Prompt 3 — Resume ↔ Job Semantic Matching (core screening prompt)

**Location in code:** `backend/app/prompts.py` → `MATCHING_PROMPT`
**Used by:** `backend/app/services/screening.py` → every candidate/job pair.

## Why this prompt exists

This is the intelligence of the product. It compares one candidate's structured
data against one job description and produces an explainable 1–10 verdict.
The prompt is engineered so that scores are **consistent across candidates**,
**grounded only in supplied evidence**, and **explainable to a recruiter**.

## Design decisions

- **Explicit scoring rubric (9–10 … 1–2)** with behavioural anchors. Without
  anchors, models drift: the same profile can score 6 or 8 depending on mood.
  Anchors keep similar evidence levels producing similar scores — essential for
  fair ranking.
- **Required vs preferred weighting**: required skills dominate; preferred skills
  act as tie-breakers/bonuses. This mirrors how real hiring bars work.
- **Anti-hallucination rules**: judge *only* from the candidate data and job text;
  never assume unlisted qualifications; never penalise absence of information that
  resumes normally do not contain.
- **Penalise major missing must-haves, reward relevant experience** — explicitly
  stated so the model's arithmetic matches recruiter intuition (raw years without
  relevance are not inflated).
- **Structured JSON output**: score, explanation, strengths, missing_skills,
  experience_alignment, education_alignment, recommendation enum and confidence —
  validated by `MatchResult` in `app/llm/validation.py`. If validation fails, the
  service retries once and otherwise falls back to the deterministic scorer, so a
  malformed response never crashes a screening run.
- The job's extracted requirements are passed alongside the raw description, and
  the candidate is passed as compact structured data rather than raw resume text —
  both reduce noise and improve consistency.

## Template

```
{MATCHING_PROMPT}
```

(See `backend/app/prompts.py` for the live template.)
