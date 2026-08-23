# Prompt 2 — Job-Description Requirement Extraction

**Location in code:** `backend/app/prompts.py` → `JOB_DESCRIPTION_EXTRACTION_PROMPT`
**Used by:** the job description workflow (requirement extraction).

## Why this prompt exists

Screening quality depends on comparing a candidate against a *structured* view of
the job: what is mandatory, what is preferred, how much experience is expected and
what the person will actually do. This prompt converts a pasted job description
into that structured form (`required_skills`, `preferred_skills`,
`experience_expectations`, `education_expectations`, `responsibilities`).

The application currently extracts these requirements with a deterministic
parser (`backend/app/services/job_parser.py`) so the product works offline; when
an LLM provider is configured, this prompt is used to extract richer, more
faithful requirements from unstructured postings.

## Design decisions

- **Separate required vs preferred skills**: the matcher weights must-haves far
  above nice-to-haves; conflating them would corrupt scores.
- **No invented requirements**: if a posting never mentions Kubernetes, it must
  not appear in the requirements just because it is common for similar roles.
- **Experience as one concise sentence** (e.g. "5+ years of professional software
  engineering experience") — easy for the matching prompt to consume and easy for
  recruiters to verify.
- **Strict JSON output shape** declared inline; validated by
  `app/llm/validation.py` before use.

## Template

```
{JOB_DESCRIPTION_EXTRACTION_PROMPT}
```

(See `backend/app/prompts.py` for the live template.)
