"""Shared pytest fixtures."""

import os
import tempfile
from pathlib import Path

import pytest

# Configure a disposable SQLite database before the app is imported.
_TMP_DIR = Path(tempfile.mkdtemp(prefix="srs-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["CORS_ORIGINS"] = "http://localhost:5173"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Candidate, JobDescription  # noqa: E402
from app.services.resume_parser import parse_resume  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database():
    init_db()
    yield


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def sample_resume_text() -> str:
    return (Path(__file__).parent / "fixtures" / "sample_resume.txt").read_text(
        encoding="utf-8"
    )


@pytest.fixture()
def parsed_sample_resume(sample_resume_text) -> dict:
    return parse_resume(sample_resume_text)


@pytest.fixture()
def seeded_job(db_session) -> JobDescription:
    job = JobDescription(
        title="Senior Python Developer",
        description_text=(
            "We are hiring a Senior Python Developer to build scalable backend "
            "services.\n\nRequirements:\n"
            "- 5+ years of professional software engineering experience\n"
            "- Strong Python and FastAPI skills\n"
            "- Experience with PostgreSQL and Docker\n"
            "- Bachelor's degree in Computer Science or related field\n\n"
            "Nice-to-have:\n"
            "- Kubernetes experience\n"
            "- AWS cloud experience\n"
        ),
        requirements={
            "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "preferred_skills": ["Kubernetes", "AWS"],
            "experience_expectations": "5+ years of experience",
            "education_expectations": ["bachelor"],
            "responsibilities": ["Build scalable backend services"],
        },
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


@pytest.fixture()
def seeded_candidate(db_session, parsed_sample_resume, sample_resume_text) -> Candidate:
    candidate = Candidate(
        candidate_name=parsed_sample_resume["candidate_name"],
        email=parsed_sample_resume["email"],
        phone=parsed_sample_resume["phone"],
        skills=parsed_sample_resume["skills"],
        experience=parsed_sample_resume["experience"],
        education=parsed_sample_resume["education"],
        resume_filename="sample_resume.txt",
        file_type="txt",
        raw_text=sample_resume_text,
        parsed_data={"summary": None, "certifications": []},
    )
    db_session.add(candidate)
    db_session.commit()
    db_session.refresh(candidate)
    return candidate
