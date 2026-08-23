"""Screening endpoints: run screening, list/filter/sort results."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Candidate, JobDescription, ScreeningResult, User
from app.api.routes.auth import get_current_user
from app.schemas import (
    ScreeningRequest,
    ScreeningResultRead,
    ScreeningRunResponse,
)
from app.services.screening import run_screening

router = APIRouter(prefix="/screening", tags=["Screening"])


@router.post(
    "/run",
    response_model=ScreeningRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Screen selected candidates against a job description",
)
def run_screening_endpoint(
    payload: ScreeningRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScreeningRunResponse:
    job = db.query(JobDescription).filter(
        JobDescription.id == payload.job_description_id,
        JobDescription.user_id == current_user.id
    ).first()
    if job is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Job description not found."
        )

    candidates = (
        db.query(Candidate).filter(
            Candidate.id.in_(payload.candidate_ids),
            Candidate.user_id == current_user.id
        ).all()
    )
    if len(candidates) != len(payload.candidate_ids):
        found_ids = {c.id for c in candidates}
        missing = [i for i in payload.candidate_ids if i not in found_ids]
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Candidate(s) not found: {missing}",
        )

    threshold = payload.threshold
    results = run_screening(db, job, candidates, threshold)

    provider_used = results[0].llm_provider if results else "unknown"
    return ScreeningRunResponse(
        job=job,
        threshold=(
            threshold
            if threshold is not None
            else (results[0].shortlist_threshold if results else 7.0)
        ),
        provider_used=provider_used,
        results=[
            _to_result_read(r, rank) for rank, r in enumerate(results, start=1)
        ],
    )



def _to_result_read(result: ScreeningResult, rank: int) -> ScreeningResultRead:
    read = ScreeningResultRead.model_validate(result)
    read.rank = rank
    read.candidate_name = result.candidate.candidate_name
    read.candidate_email = result.candidate.email
    read.candidate_skills = list(result.candidate.skills or [])
    read.candidate_experience = list(result.candidate.experience or [])
    read.candidate_education = list(result.candidate.education or [])
    return read


@router.get(
    "/results",
    response_model=list[ScreeningResultRead],
    summary="List screening results with filtering and sorting",
)
def list_results(
    job_id: int | None = Query(default=None),
    min_score: float | None = Query(default=None, ge=1.0, le=10.0),
    shortlisted_only: bool = Query(default=False),
    skill: str | None = Query(default=None, description="Filter by candidate skill"),
    q: str | None = Query(default=None, description="Search candidate name/email"),
    sort_by: str = Query(
        default="score",
        pattern="^(score|name|date)$",
        description="score | name | date",
    ),
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScreeningResultRead]:
    query = db.query(ScreeningResult).filter(ScreeningResult.user_id == current_user.id).join(Candidate)

    if job_id is not None:
        query = query.filter(ScreeningResult.job_description_id == job_id)
    if min_score is not None:
        query = query.filter(ScreeningResult.match_score >= min_score)
    if shortlisted_only:
        query = query.filter(ScreeningResult.shortlisted.is_(True))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Candidate.candidate_name.ilike(like)) | (Candidate.email.ilike(like))
        )
    if skill:
        # JSON array text search keeps this portable across SQLite/Postgres.
        query = query.filter(
            Candidate.skills.cast(__import__("sqlalchemy").String).ilike(
                f'%"{skill.strip()}"%'
            )
        )

    desc = order == "desc"
    name_col = case(
        (Candidate.candidate_name.is_(None), "~zzz"),
        else_=Candidate.candidate_name,
    )
    if sort_by == "name":
        query = query.order_by(name_col.desc() if desc else name_col.asc())
    elif sort_by == "date":
        col = ScreeningResult.created_at
        query = query.order_by(col.desc() if desc else col.asc())
    else:
        score_col = ScreeningResult.match_score
        name_tiebreak = name_col.asc()
        query = query.order_by(
            score_col.desc() if desc else score_col.asc(), name_tiebreak
        )

    rows = query.all()

    ranked: list[ScreeningResultRead] = []
    for position, row in enumerate(rows, start=1):
        read = _to_result_read(row, position)
        ranked.append(read)
    if skill:
        needle = skill.lower()
        ranked = [
            r for r in ranked
            if any(needle in str(s).lower() for s in r.candidate_skills)
        ]
    return ranked


@router.delete("/results/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_result(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = db.query(ScreeningResult).filter(ScreeningResult.id == result_id, ScreeningResult.user_id == current_user.id).first()
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Screening result not found.")
    db.delete(result)
    db.commit()

