"""Heuristic structured resume parser.

This parser runs deterministically on every resume (no network required) and
produces the canonical structured representation stored on the Candidate
model. When an LLM provider is configured, `resume_parser_llm.py` can enrich
this output, but the heuristics remain the reliable baseline.
"""

import re
from typing import Any

SECTION_PATTERNS = {
    "summary": re.compile(
        r"^(professional\s+)?(summary|profile|objective|about\s+me)\b", re.I
    ),
    "skills": re.compile(r"^(technical\s+)?(skills|core\s+competencies|technologies)\b", re.I),
    "experience": re.compile(
        r"^(work\s+|professional\s+|relevant\s+)?(experience|employment|career\s+history)\b", re.I
    ),
    "education": re.compile(r"^(education|academic\s+(background|qualifications?))\b", re.I),
    "projects": re.compile(r"^(projects?|key\s+projects)\b", re.I),
    "certifications": re.compile(r"^(certifications?|licenses?)\b", re.I),
}

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}"
)

DATE_RANGE_RE = re.compile(
    r"(?P<start>(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}"
    r"|\d{1,2}/\d{4}|\d{4}[-/]\d{1,2}|\d{4})"
    r"\s*(?:-|–|—|to|until)\s*"
    r"(?P<end>Present|Current|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s*\d{4}"
    r"|\d{1,2}/\d{4}|\d{4}[-/]\d{1,2}|\d{4})",
    re.I,
)
YEAR_RE = re.compile(r"(?:19|20)\d{2}")

# Curated skill catalogue used for structured skill detection.
SKILL_CATALOGUE = [
    # Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
    "Kotlin", "Swift", "Ruby", "PHP", "Scala", "R", "SQL", "Bash", "HTML", "CSS",
    # Frontend
    "React", "Angular", "Vue.js", "Next.js", "Svelte", "Redux", "Tailwind CSS",
    "Bootstrap", "GraphQL Client", "Webpack", "Vite",
    # Backend / frameworks
    "Node.js", "Express.js", "Django", "Flask", "FastAPI", "Spring Boot", ".NET",
    "Laravel", "Rails", "ASP.NET", "REST APIs", "GraphQL", "gRPC", "WebSockets",
    # Data / ML
    "Machine Learning", "Deep Learning", "NLP", "Computer Vision", "TensorFlow",
    "PyTorch", "scikit-learn", "Keras", "XGBoost", "Pandas", "NumPy", "SciPy",
    "OpenCV", "Hugging Face Transformers", "LangChain", "LLM Fine-Tuning",
    "Prompt Engineering", "Retrieval-Augmented Generation", "Vector Databases",
    "Data Analysis", "Data Visualization", "Tableau", "Power BI",
    "Apache Spark", "Apache Kafka", "Airflow", "dbt",
    # Data stores
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Elasticsearch",
    "DynamoDB", "Snowflake", "BigQuery", "Cassandra",
    # Cloud / DevOps
    "AWS", "Azure", "GCP", "Google Cloud Platform", "Docker", "Kubernetes",
    "Terraform", "Ansible", "Jenkins", "GitHub Actions", "GitLab CI/CD",
    "CircleCI", "CI/CD", "Linux", "Nginx", "Prometheus", "Grafana",
    "Serverless", "Lambda", "Microservices Architecture", "System Design",
    # Practices
    "Agile", "Scrum", "Kanban", "TDD", "Unit Testing", "Integration Testing",
    "Code Review", "Git", "Jira", "Figma", "Accessibility", "Responsive Design",
]

DEGREE_KEYWORDS = re.compile(
    r"(b\.?tech|b\.?e\.?|b\.?sc|bachelor(?:'s)?|master(?:'s)?|m\.?tech|m\.?sc|m\.?e\.?"
    r"|mba|ph\.?d|doctorate|associate(?:'s)?|diploma)", re.I
)


def _split_sections(lines: list[str]) -> tuple[dict[str, int], list[str]]:
    """Return mapping of section name -> start line index."""
    starts: dict[str, int] = {}
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or len(stripped) > 60:
            continue
        cleaned = stripped.rstrip(":").strip()
        for name, pattern in SECTION_PATTERNS.items():
            if pattern.match(cleaned) and cleaned.lower() == re.sub(r"[^a-z]", "", cleaned.lower()) or pattern.match(cleaned):
                if len(cleaned.split()) <= 4:
                    starts.setdefault(name, idx)
                break
    return starts, lines


def _extract_name(lines: list[str], email: str | None) -> str | None:
    """Best-effort candidate name: the first plausible personal-name line."""
    for line in lines[:12]:
        stripped = line.strip().rstrip(",")
        if not stripped or EMAIL_RE.search(stripped):
            continue
        if any(ch.isdigit() for ch in stripped):
            continue
        words = stripped.split()
        if not 1 < len(words) <= 5:
            continue
        if all(re.fullmatch(r"[A-Za-z][A-Za-z'.\-]*\.?", w) for w in words):
            title = stripped.title() if stripped.isupper() else stripped
            return title
    if email:
        local = email.split("@")[0]
        guess = re.sub(r"[._\-0-9]+", " ", local).strip()
        parts = [p.capitalize() for p in guess.split() if p.isalpha()]
        if len(parts) >= 2:
            return " ".join(parts[:3])
    return None


def _extract_skills(text: str, section_lines: list[str]) -> list[str]:
    """Detect skills from a curated catalogue plus explicit skill bullets."""
    found: list[str] = []
    haystack = text.lower()

    def add(skill: str) -> None:
        if skill.lower() not in {s.lower() for s in found}:
            found.append(skill)

    for skill in SKILL_CATALOGUE:
        pattern = re.escape(skill).replace(r"\ ", r"[\s./_-]?")
        if re.search(rf"(?<![A-Za-z]){pattern}(?![A-Za-z])", haystack, re.I):
            add(skill)

    # Also capture free-form items listed under a Skills heading.
    for line in section_lines:
        cleaned = line.strip().strip("•-*").strip()
        if not cleaned or len(cleaned) > 80:
            continue
        if ":" in cleaned and len(cleaned.split(":")[0].split()) <= 3:
            cleaned = cleaned.split(":", 1)[1]
        for item in re.split(r"[,;/|]", cleaned):
            item = item.strip(" .")
            if 2 <= len(item) <= 40 and item.lower() in haystack:
                add(item)
        break  # only the first summary-style skills line
    return found


def _parse_experience_section(section_lines: list[str]) -> list[dict[str, Any]]:
    """Parse work-experience bullets into structured entries."""
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw in section_lines:
        line = raw.strip()
        if not line:
            continue
        if SECTION_PATTERNS["education"].match(line) or SECTION_PATTERNS["projects"].match(line):
            break

        match = DATE_RANGE_RE.search(line)
        starts_with_bullet = bool(re.match(r"^[\s]*[•\-*‣◦]", raw))
        looks_like_header = (bool(match) or (
            len(line) < 110
            and not line.endswith((".", ";", ":"))
            and 3 <= len(line.split()) <= 14
        )) and not starts_with_bullet

        if looks_like_header:
            if current:
                entries.append(current)
            role_part = DATE_RANGE_RE.sub("", line).strip(" -–—|,")
            parts = [p.strip() for p in re.split(r"\s+(?:at|@|\||—|–|-)\s+", role_part, maxsplit=1)]
            role = parts[0] if parts else role_part
            org = parts[1] if len(parts) > 1 else None
            current = {
                "role": role or None,
                "organization": org,
                "duration": None,
                "start_date": None,
                "end_date": None,
                "responsibilities": [],
                "technologies": [],
            }
            if match:
                current["duration"] = match.group(0)
                current["start_date"] = match.group("start")
                current["end_date"] = match.group("end")
            elif line and DATE_RANGE_RE.search(raw):
                pass
        else:
            if current is None:
                continue
            bullet = line.strip("•*- ").strip()
            if bullet:
                current["responsibilities"].append(bullet)

    if current:
        entries.append(current)

    for entry in entries:
        joined = " ".join(entry["responsibilities"]).lower()
        entry["technologies"] = [
            s for s in SKILL_CATALOGUE
            if re.search(
                rf"(?<![A-Za-z]){re.escape(s.lower()).replace(r'\ ', r'[\s./_-]?')}(?![A-Za-z])",
                joined,
                re.I,
            )
        ]
        entry["responsibilities"] = entry["responsibilities"][:8]
    return [e for e in entries if e.get("role") or e.get("organization")]


def _parse_education_section(section_lines: list[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw in section_lines:
        line = raw.strip().strip("•*- ").strip()
        if not line:
            continue
        if DEGREE_KEYWORDS.search(line):
            years = [int(m.group(0)) for m in YEAR_RE.finditer(line)]
            degree_match = DEGREE_KEYWORDS.search(line)
            field = None
            m = re.search(
                r"in\s+([A-Z][\w\s&]+?)(?:\s+(?:from|at|,|\(|\d{4})|$)", line
            )
            if m:
                field = m.group(1).strip(" ,.")
            inst_m = re.search(
                r"(?:from|at)\s+(.+?)(?:\s*[,|]\s*(?=(?:19|20)\d{2})|\s*[(|]|$)",
                line,
            )
            institution = (
                inst_m.group(1).strip(" ,.") if inst_m else None
            )
            entries.append(
                {
                    "institution": institution,
                    "degree": degree_match.group(0).strip(),
                    "field": field,
                    "start_year": years[0] if years else None,
                    "end_year": years[-1] if len(years) > 1 else None,
                }
            )
        elif entries and len(line) > 3 and entries[-1]["institution"] is None and re.match(r"^[A-Z]", line):
            entries[-1]["institution"] = line.strip(" ,.")
    return entries


def parse_resume(raw_text: str) -> dict[str, Any]:
    """Convert raw resume text into the canonical structured dictionary."""
    lines = raw_text.splitlines()
    sections, _ = _split_sections(lines)

    def slice_section(key: str | None) -> list[str]:
        if key is None or key not in sections:
            return []
        start = sections[key] + 1
        later = [idx for name, idx in sections.items() if idx > sections[key]]
        end = min(later) if later else len(lines)
        return lines[start:end]

    email_match = EMAIL_RE.search(raw_text)
    email = email_match.group(0) if email_match else None

    phone = None
    phone_zone = raw_text.split("\n", 8)
    for zone_line in phone_zone:
        m = PHONE_RE.search(zone_line)
        if m and len(re.sub(r"\D", "", m.group(0))) >= 10:
            phone = re.sub(r"\s+", " ", m.group(0)).strip()
            break

    name = _extract_name(lines, email)

    skills_section = slice_section("skills")
    skills = _extract_skills(raw_text, skills_section)

    experience = _parse_experience_section(slice_section("experience"))
    education = _parse_education_section(slice_section("education"))

    summary_lines = [l.strip() for l in slice_section("summary") if l.strip()]
    summary = " ".join(summary_lines)[:600] or None

    certifications: list[str] = []
    cert_lines = slice_section("certifications")
    for cl in cert_lines:
        cleaned = cl.strip().strip("•*- ").strip()
        if 3 < len(cleaned) < 140:
            certifications.append(cleaned)
    certifications = certifications[:10]

    return {
        "candidate_name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "experience": experience,
        "education": education,
        "summary": summary,
        "certifications": certifications,
    }
