"""Pydantic request/response schemas for the API layer."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Candidates / resumes
# ---------------------------------------------------------------------------
class ExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    organization: str | None = None
    role: str | None = None
    duration: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    responsibilities: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    institution: str | None = None
    degree: str | None = None
    field: str | None = None
    start_year: int | None = None
    end_year: int | None = None


class CandidateBase(BaseModel):
    candidate_name: str | None = None
    email: str | None = None
    phone: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)


class CandidateRead(CandidateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    resume_filename: str
    file_type: str
    parse_provider: str
    summary: str | None = None
    certifications: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("summary", mode="before")
    @classmethod
    def _summary_from_parsed(cls, value: Any) -> Any:
        return value


class CandidateDetailRead(CandidateRead):
    raw_text: str
    parsed_data: dict[str, Any]


class UploadErrorItem(BaseModel):
    filename: str
    error: str


class UploadResponse(BaseModel):
    uploaded: list[CandidateRead]
    errors: list[UploadErrorItem]


# ---------------------------------------------------------------------------
# Job descriptions
# ---------------------------------------------------------------------------
class JobRequirements(BaseModel):
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_expectations: str | None = None
    education_expectations: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)


class JobCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description_text: str = Field(min_length=30, max_length=40000)


class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description_text: str | None = Field(default=None, min_length=30, max_length=40000)


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description_text: str
    requirements: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class JobListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    requirements: dict[str, Any]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Screening
# ---------------------------------------------------------------------------
class ScreeningRequest(BaseModel):
    job_description_id: int
    candidate_ids: list[int] = Field(min_length=1, max_length=100)
    threshold: float | None = Field(default=None, ge=1.0, le=10.0)

    @field_validator("candidate_ids")
    @classmethod
    def _dedupe_ids(cls, value: list[int]) -> list[int]:
        seen: list[int] = []
        for item in value:
            if item not in seen:
                seen.append(item)
        return seen


class ScreeningResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_score: float
    shortlisted: bool
    explanation: str
    strengths: list[str]
    missing_skills: list[str]
    experience_alignment: str
    education_alignment: str
    recommendation: str
    confidence: str | None
    shortlist_threshold: float
    llm_provider: str
    llm_model: str | None
    created_at: datetime
    job_description_id: int
    candidate_id: int
    candidate_name: str | None = None
    candidate_email: str | None = None
    candidate_skills: list[str] = Field(default_factory=list)
    candidate_experience: list[Any] = Field(default_factory=list)
    candidate_education: list[Any] = Field(default_factory=list)
    rank: int | None = None


class ScreeningRunResponse(BaseModel):
    job: JobListRead
    threshold: float
    provider_used: str
    results: list[ScreeningResultRead]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
class DashboardStats(BaseModel):
    total_resumes: int
    candidates_screened: int
    average_match_score: float
    shortlisted_count: int
    total_jobs: int
    recent_activity: list[dict[str, Any]]


class HealthRead(BaseModel):
    status: str
    database: str
    llm_provider: str


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    created_at: datetime
