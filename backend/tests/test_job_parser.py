"""Tests for job-description requirement extraction."""

from app.services.job_parser import extract_job_requirements

SAMPLE_JD = """Senior Python Developer

We are hiring a Senior Python Developer to build scalable backend services.

Responsibilities:
- Design and ship REST APIs
- Mentor junior engineers

Requirements:
- 5+ years of professional software engineering experience
- Strong Python and FastAPI skills
- Experience with PostgreSQL and Docker

Nice-to-have:
- Kubernetes experience
- Terraform exposure
"""


class TestJobParsing:
    def test_required_skills_found(self):
        reqs = extract_job_requirements(SAMPLE_JD)
        required = {s.lower() for s in reqs["required_skills"]}
        assert {"python", "fastapi", "postgresql", "docker"} <= required

    def test_preferred_skills_separated(self):
        reqs = extract_job_requirements(SAMPLE_JD)
        preferred = {s.lower() for s in reqs["preferred_skills"]}
        assert "kubernetes" in preferred
        assert not ({"python"} & preferred)

    def test_experience_expectations(self):
        reqs = extract_job_requirements(SAMPLE_JD)
        assert reqs["experience_expectations"] is not None
        assert "5" in reqs["experience_expectations"]

    def test_responsibilities_extracted(self):
        reqs = extract_job_requirements(SAMPLE_JD)
        assert any("REST APIs" in r or "mentor" in r.lower() for r in reqs["responsibilities"])

    def test_empty_description_safe(self):
        text = (
            "This role involves general duties around the office and support "
            "tasks for the wider team on a day to day basis. Nothing technical."
        )
        reqs = extract_job_requirements(text)
        assert isinstance(reqs["required_skills"], list)
        assert reqs["experience_expectations"] is None

    def test_no_invented_requirements(self):
        reqs = extract_job_requirements(SAMPLE_JD)
        # Skills absent from the JD must never appear.
        all_skills = {s.lower() for s in reqs["required_skills"]} | {
            s.lower() for s in reqs["preferred_skills"]
        }
        assert "cobol" not in all_skills
