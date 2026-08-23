"""Heuristic job-description requirement extractor.

Extracts required skills, preferred skills, experience expectations, education
expectations and responsibilities from free-form job description text. This is
used to pre-populate the structured `requirements` JSON on a JobDescription and
to give the LLM matcher a clean, comparable view of the job.
"""

import re
from typing import Any

from app.services.resume_parser import SKILL_CATALOGUE

REQUIRED_HEADINGS = re.compile(
    r"^(requirements|required\s+qualifications|must[-\s]?have|qualifications|what\s+you.?ll\s+need|minimum\s+qualifications)\b",
    re.I,
)
PREFERRED_HEADINGS = re.compile(
    r"^(nice[-\s]?to[-\s]?have|preferred(\s+qualifications)?|plus(es)?|bonus( points)?|good[-\s]to[-\s]have)\b",
    re.I,
)
RESPONSIBILITY_HEADINGS = re.compile(
    r"^(responsibilities|duties|what\s+you.?ll\s+do|role\s+and\s+responsibilities?|about\s+the\s+role)\b",
    re.I,
)

EXPERIENCE_RE = re.compile(
    r"(\d+\+?\s*(?:-\s*\d+\s*)?(?:to\s*\d+\s*)?years?)\s*(?:of\s+)?(?:relevant\s+|hands-?on\s+|professional\s+|proven\s+)*"
    r"(experience|work\s+experience)?", re.I)
EDUCATION_KEYWORDS_RE = re.compile(
    r"(b\.?tech|b\.?sc|bachelor(?:'s)?|m\.?tech|m\.?sc|master(?:'s)?|mba|ph\.?d)", re.I
)
BULLET_RE = re.compile(r"^[\s]*[•\-*‣◦]\s*")
NUMBERED_RE = re.compile(r"^[\s]*\d+[.)]\s*")

ALL_HEADING_RES = (REQUIRED_HEADINGS, PREFERRED_HEADINGS, RESPONSIBILITY_HEADINGS)


def _find_skill_matches(text: str) -> list[str]:
    found: list[str] = []
    haystack = text.lower()
    for skill in SKILL_CATALOGUE:
        pattern = re.escape(skill).replace(r"\ ", r"[\s./_-]?").replace(r"/", r"/?")
        if re.search(rf"(?<![A-Za-z]){pattern}(?![A-Za-z])", haystack, re.I):
            if skill.lower() not in {f.lower() for f in found}:
                found.append(skill)
    return found


def _split_into_sections(text: str) -> tuple[list[str], list[str], list[str]]:
    """Return (required_lines, preferred_lines, responsibility_lines)."""
    lines = text.splitlines()
    current: str | None = None
    required: list[str] = []
    preferred: list[str] = []
    responsibilities: list[str] = []

    def push(target: list[str], line: str) -> None:
        cleaned = BULLET_RE.sub("", line)
        cleaned = NUMBERED_RE.sub("", cleaned).strip()
        if 2 < len(cleaned) <= 220:
            target.append(cleaned)

    for line in lines:
        stripped = line.strip().rstrip(":").strip()
        if len(stripped) <= 45:
            if REQUIRED_HEADINGS.match(stripped):
                current = "required"
                continue
            if PREFERRED_HEADINGS.match(stripped):
                current = "preferred"
                continue
            if RESPONSIBILITY_HEADINGS.match(stripped):
                current = "responsibilities"
                continue
        if any(h.match(stripped) for h in ALL_HEADING_RES):
            continue
        if current == "required":
            push(required, line)
        elif current == "preferred":
            push(preferred, line)
        elif current == "responsibilities":
            push(responsibilities, line)
        else:
            # Unsectioned bullet lists are treated as general requirements.
            if BULLET_RE.match(line) or NUMBERED_RE.match(line):
                push(required, line)

    return required, preferred, responsibilities


def extract_job_requirements(description_text: str) -> dict[str, Any]:
    """Produce the structured requirements dictionary for a job description."""
    required_lines, preferred_lines, responsibilities = _split_into_sections(description_text)

    required_skills: list[str] = []
    preferred_skills: list[str] = []
    for line in required_lines:
        for skill in _find_skill_matches(line):
            if skill.lower() not in {s.lower() for s in required_skills}:
                required_skills.append(skill)
    for line in preferred_lines:
        for skill in _find_skill_matches(line):
            lower = {s.lower() for s in required_skills + preferred_skills}
            if skill.lower() not in lower:
                preferred_skills.append(skill)

    exp_matches = EXPERIENCE_RE.findall(description_text)
    experience_expectations = None
    years_re = re.compile(r"(\d+)\+?\s*(?:-\s*\d+)?(?:\s*to\s*\d+)?\s*years?", re.I)
    year_values = [int(m.group(1)) for m in years_re.finditer(description_text)]
    if year_values:
        experience_expectations = f"{max(year_values)}+ years of professional experience"

    education_expectations: list[str] = []
    for m in EDUCATION_KEYWORDS_RE.finditer(description_text):
        phrase = description_text[max(0, m.start() - 30): m.end() + 60].replace("\n", " ")
        phrase = re.sub(r"\s+", " ", phrase).strip()
        if phrase not in education_expectations and m.group(0):
            education_expectations.append(m.group(0))
    education_expectations = education_expectations[:4]

    return {
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "experience_expectations": experience_expectations,
        "education_expectations": education_expectations,
        "responsibilities": responsibilities[:12],
    }
