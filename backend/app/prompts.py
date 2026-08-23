"""Canonical LLM prompt templates for the Smart Resume Screener.

These templates are the single source of truth used by the application.
Human-readable copies with rationale live in the repository's /prompts/
directory and are referenced from the README.

Design principles shared by every prompt:
- The model must never invent facts that are not present in the input.
- Output must be strict JSON matching a documented schema (no markdown fences).
- Missing information is represented as null/empty, never fabricated.
"""

SYSTEM_PROMPT = """\
You are an expert technical recruiter and hiring analyst working for a \
professional recruiting platform. You analyse resumes and job descriptions \
with objectivity, precision and fairness. You follow instructions exactly and \
always respond with valid minified JSON only — no prose, no markdown fences.
"""

# ---------------------------------------------------------------------------
# Prompt 1 — Resume extraction (LLM enrichment of the heuristic parse)
# ---------------------------------------------------------------------------
RESUME_EXTRACTION_PROMPT = """\
Extract structured information from the resume text below.

Rules:
1. Use ONLY information explicitly present in the resume. Never invent or \
guess employers, dates, skills or credentials.
2. If a field is not present in the resume, return null (or an empty array \
for lists).
3. Skills must be individual technology/tool/domain items (e.g. "Python", \
"Kubernetes"), not sentences.
4. Each experience entry must include organization, role, duration (as \
written), responsibilities (short bullet strings) and technologies used.
5. Each education entry must include institution, degree, field and years \
when available.

Return JSON with EXACTLY this shape:
{"candidate_name": string|null,
 "email": string|null,
 "phone": string|null,
 "summary": string|null,
 "skills": string[],
 "experience": [{"organization": string|null, "role": string|null,
   "duration": string|null, "responsibilities": string[],
   "technologies": string[]}],
 "education": [{"institution": string|null, "degree": string|null,
   "field": string|null, "start_year": number|null, "end_year": number|null}],
 "certifications": string[]}

RESUME TEXT:
---
{resume_text}
---
"""

# ---------------------------------------------------------------------------
# Prompt 2 — Job-description requirement extraction
# ---------------------------------------------------------------------------
JOB_DESCRIPTION_EXTRACTION_PROMPT = """\
Analyse the job description below and extract its requirements.

Rules:
1. Base every item strictly on the job description text. Do not add typical \
requirements for this role that are not stated.
2. required_skills: technologies/tools/domains explicitly demanded as \
mandatory ("must have", listed under Requirements).
3. preferred_skills: nice-to-have / bonus skills ("preferred", "plus").
4. experience_expectations: concise sentence summarising years/seniority \
demanded, e.g. "3+ years of professional software engineering experience".
5. education_expectations: degrees or fields demanded (empty array if none).
6. responsibilities: short strings summarising what the person will do.

Return JSON with EXACTLY this shape:
{"required_skills": string[],
 "preferred_skills": string[],
 "experience_expectations": string|null,
 "education_expectations": string[],
 "responsibilities": string[]}

JOB DESCRIPTION:
---
{job_text}
---
"""

# ---------------------------------------------------------------------------
# Prompt 3 — Resume ↔ Job semantic matching (the core screening prompt)
# ---------------------------------------------------------------------------
MATCHING_PROMPT = """\
You are screening one candidate against one job description. Compare them \
objectively and rate the fit on a 1-10 scale.

SCORING RUBRIC (apply consistently):
- 9-10  Exceptional: meets all required skills and experience expectations, \
with relevant achievements beyond the bar.
- 7-8   Strong: meets nearly all required skills and the experience bar; \
gaps are minor and covered by adjacent experience.
- 5-6   Partial: meets some required skills or falls short on experience; \
clear potential but noticeable gaps.
- 3-4   Weak: meets few required skills or significantly under-experienced.
- 1-2   Poor: fundamental mismatch with the role's core requirements.

RULES:
1. Judge ONLY from the candidate data and job description provided. Never \
assume unlisted qualifications, and never penalise absence of information \
that resumes normally do not contain.
2. Required skills weigh substantially more than preferred skills. Preferred \
skills are tie-breakers and bonus signals.
3. Reward directly relevant experience and progression; do not inflate raw \
years without relevance.
4. Penalise major missing requirements (a must-have skill with no evidence).
5. Education matters only as stated in the job description; equivalent \
practical experience may offset it when the JD allows.
6. Be consistent: similar evidence levels must yield similar scores across \
candidates.
7. missing_skills must list required/preferred skills with no supporting \
evidence in the resume (empty array if none).

Return JSON with EXACTLY this shape:
{"match_score": number,            // integer 1-10
 "explanation": string,            // 2-4 sentence justification citing specifics
 "strengths": string[],            // 2-5 concrete strengths vs this job
 "missing_skills": string[],       // required/preferred skills lacking evidence
 "experience_alignment": string,   // 1-2 sentences comparing experience to the bar
 "education_alignment": string,    // 1-2 sentences comparing education to the bar
 "recommendation": "strong_yes" | "yes" | "maybe" | "no",
 "confidence": "low" | "medium" | "high"}

JOB DESCRIPTION:
---
Title: {job_title}
{job_requirements}

Full description:
{job_text}
---

CANDIDATE:
---
Name: {candidate_name}
Skills: {candidate_skills}
Experience: {candidate_experience}
Education: {candidate_education}
Certifications: {candidate_certifications}
---
"""


def build_resume_extraction_messages(resume_text: str) -> tuple[str, str]:
    return SYSTEM_PROMPT, RESUME_EXTRACTION_PROMPT.format(
        resume_text=resume_text[:12000]
    )


def build_job_extraction_messages(job_text: str) -> tuple[str, str]:
    return SYSTEM_PROMPT, JOB_DESCRIPTION_EXTRACTION_PROMPT.format(
        job_text=job_text[:8000]
    )


def build_matching_messages(
    job_title: str,
    job_text: str,
    job_requirements: str,
    candidate_name: str,
    candidate_skills: str,
    candidate_experience: str,
    candidate_education: str,
    candidate_certifications: str,
) -> tuple[str, str]:
    return SYSTEM_PROMPT, MATCHING_PROMPT.format(
        job_title=job_title,
        job_requirements=job_requirements,
        job_text=job_text[:6000],
        candidate_name=candidate_name or "Unknown candidate",
        candidate_skills=candidate_skills[:1500],
        candidate_experience=candidate_experience[:4000],
        candidate_education=candidate_education[:1200],
        candidate_certifications=candidate_certifications[:600],
    )
