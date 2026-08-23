"""ORM models: candidates/resumes, job descriptions, screening results."""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Candidate(Base):
    """A uploaded resume plus its structured extraction result."""

    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Structured representations (never a single unstructured blob).
    skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    experience: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    education: Mapped[list] = mapped_column(JSON, default=list, nullable=False)

    resume_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | txt
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Full parser output (summary, certifications, extra metadata, ...).
    parsed_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    parse_provider: Mapped[str] = mapped_column(String(20), default="heuristic", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    screening_results: Mapped[list["ScreeningResult"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class JobDescription(Base):
    """A job posting candidates can be screened against."""

    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Extracted requirements:
    # {required_skills, preferred_skills, experience_expectations,
    #  education_expectations, responsibilities}
    requirements: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    screening_results: Mapped[list["ScreeningResult"]] = relationship(
        back_populates="job_description", cascade="all, delete-orphan"
    )


class ScreeningResult(Base):
    """Outcome of matching one candidate against one job description."""

    __tablename__ = "screening_results"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_description_id", name="uq_candidate_job"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), nullable=False)
    job_description_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id"), nullable=False
    )

    match_score: Mapped[float] = mapped_column(Float, nullable=False)  # 1..10
    shortlisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    explanation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    strengths: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    experience_alignment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    education_alignment: Mapped[str] = mapped_column(Text, default="", nullable=False)
    recommendation: Mapped[str] = mapped_column(String(40), default="maybe", nullable=False)
    confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)  # low|medium|high

    shortlist_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    llm_provider: Mapped[str] = mapped_column(String(20), default="mock", nullable=False)
    llm_model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    candidate: Mapped["Candidate"] = relationship(back_populates="screening_results")
    job_description: Mapped["JobDescription"] = relationship(back_populates="screening_results")
