"""Dashboard statistics and health endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import engine, get_db
from app.models import Candidate, JobDescription, ScreeningResult, User
from app.api.routes.auth import get_current_user
from app.schemas import DashboardStats, HealthRead

router = APIRouter(tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats, summary="Dashboard statistics")
def dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardStats:
    total_resumes = (
        db.query(func.count(Candidate.id))
        .filter(Candidate.user_id == current_user.id)
        .scalar()
        or 0
    )
    total_jobs = (
        db.query(func.count(JobDescription.id))
        .filter(JobDescription.user_id == current_user.id)
        .scalar()
        or 0
    )
    screened_count = (
        db.query(func.count(ScreeningResult.candidate_id.distinct()))
        .filter(ScreeningResult.user_id == current_user.id)
        .scalar()
        or 0
    )
    avg_score = (
        db.query(func.avg(ScreeningResult.match_score))
        .filter(ScreeningResult.user_id == current_user.id)
        .scalar()
        or 0.0
    )
    shortlisted = (
        db.query(func.count(ScreeningResult.id))
        .filter(
            ScreeningResult.user_id == current_user.id,
            ScreeningResult.shortlisted.is_(True),
        )
        .scalar()
        or 0
    )

    recent_rows = (
        db.query(ScreeningResult)
        .filter(ScreeningResult.user_id == current_user.id)
        .order_by(ScreeningResult.updated_at.desc())
        .limit(10)
        .all()
    )
    recent_activity = [
        {
            "id": r.id,
            "candidate_id": r.candidate_id,
            "candidate_name": r.candidate.candidate_name,
            "job_title": r.job_description.title,
            "match_score": r.match_score,
            "shortlisted": r.shortlisted,
            "screened_at": (r.updated_at or r.created_at).isoformat(),
        }
        for r in recent_rows
    ]

    return DashboardStats(
        total_resumes=total_resumes,
        candidates_screened=screened_count,
        average_match_score=round(float(avg_score), 2),
        shortlisted_count=shortlisted,
        total_jobs=total_jobs,
        recent_activity=recent_activity,
    )



def _provider_status() -> tuple[str, str | None]:
    """Resolve the effective LLM provider without ever raising."""
    settings = get_settings()
    if settings.llm_provider == "mock":
        return "mock", None
    try:
        from app.llm.provider import get_llm_provider

        provider = get_llm_provider(settings)
        return provider.name, provider.model
    except Exception:  # noqa: BLE001 - e.g. missing API key
        return f"{settings.llm_provider} (unconfigured: missing credentials)", None


@router.get("/health", response_model=HealthRead, summary="Health check")
def health(db: Session = Depends(get_db)) -> HealthRead:
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        database_status = "error"

    provider_name, model = _provider_status()
    return HealthRead(
        status="ok" if database_status == "ok" else "degraded",
        database=database_status,
        llm_provider=provider_name,
    )


@router.get("/health/db", include_in_schema=False)
def health_db() -> dict[str, str]:
    try:
        conn = engine.connect()
        conn.close()
        return {"database": "ok"}
    except Exception:  # noqa: BLE001
        return {"database": "error"}
