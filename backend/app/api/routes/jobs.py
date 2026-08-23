"""Job description CRUD endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import JobDescription
from app.schemas import JobCreate, JobListRead, JobRead, JobRequirements, JobUpdate
from app.services.job_parser import extract_job_requirements

router = APIRouter(prefix="/jobs", tags=["Job Descriptions"])


def _get_job_or_404(job_id: int, db: Session) -> JobDescription:
    job = db.get(JobDescription, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job description not found.")
    return job


@router.post(
    "",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job description",
)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> JobDescription:
    requirements = extract_job_requirements(payload.description_text)
    job = JobDescription(
        title=payload.title.strip(),
        description_text=payload.description_text.strip(),
        requirements=requirements,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobListRead], summary="List job descriptions")
def list_jobs(db: Session = Depends(get_db)) -> list[JobDescription]:
    return (
        db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
    )


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDescription:
    return _get_job_or_404(job_id, db)


@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: int, payload: JobUpdate, db: Session = Depends(get_db)
) -> JobDescription:
    job = _get_job_or_404(job_id, db)
    if payload.title is not None:
        job.title = payload.title.strip()
    if payload.description_text is not None:
        job.description_text = payload.description_text.strip()
        # Re-extract requirements whenever the text changes.
        job.requirements = extract_job_requirements(job.description_text)
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: int, db: Session = Depends(get_db)) -> None:
    job = _get_job_or_404(job_id, db)
    db.delete(job)
    db.commit()


@router.get("/{job_id}/requirements", response_model=JobRequirements)
def get_requirements(job_id: int, db: Session = Depends(get_db)) -> JobRequirements:
    job = _get_job_or_404(job_id, db)
    return JobRequirements.model_validate(job.requirements or {})
