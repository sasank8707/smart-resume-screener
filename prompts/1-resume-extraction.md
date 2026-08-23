# Prompt 1 — Resume Extraction

**Location in code:** `backend/app/prompts.py` → `RESUME_EXTRACTION_PROMPT`
**Used by:** the LLM enrichment step of the resume parsing pipeline.

## Why this prompt exists

The heuristic parser (`backend/app/services/resume_parser.py`) produces a reliable,
deterministic structured extraction for every resume without any network calls.
When an LLM provider is configured, this prompt lets the model enrich/correct that
structure. Its job is to turn messy free-form resume text into the canonical
candidate JSON schema (name, contact, skills, experience entries with
organization/role/duration/responsibilities/technologies, education, certifications).

## Design decisions

- **Anti-hallucination rules first**: the model may only use information explicitly
  present in the resume; missing fields must be `null` / empty arrays. Resumes are
  personal data — inventing an employer or a skill is worse than leaving a blank.
- **Skills as atomic items**, never sentences, so they can be compared with job
  requirements structurally.
- **Experience as objects** preserving organization, role, duration as written,
  responsibilities and technologies, matching the database schema exactly.
- **Strict JSON-only output shape** declared inline so responses can be validated
  programmatically; malformed output is retried/recovered by `app/llm/validation.py`.
- Input is truncated to a safe token budget (~12k chars) before sending.

## Template

```
{RESUME_EXTRACTION_PROMPT}
```

(See `backend/app/prompts.py` for the live template — it is the single source of
truth; this file documents its purpose.)
