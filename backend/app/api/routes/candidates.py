"""Candidate / resume endpoints."""

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models import Candidate, User
from app.api.routes.auth import get_current_user
from app.schemas import (
    CandidateDetailRead,
    CandidateRead,
    UploadErrorItem,
    UploadResponse,
)
from app.services.extraction import ExtractionError, extract_resume_text
from app.services.resume_parser import parse_resume

router = APIRouter(prefix="/candidates", tags=["Candidates"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent.parent / "uploads"


def _sanitize_filename(filename: str) -> str:
    """Strip path components and unsafe characters from client filenames."""
    base = Path(filename.replace("\\", "/")).name
    cleaned = re.sub(r"[^A-Za-z0-9._ -]", "_", base).strip().strip(".")
    return cleaned[:180] or "resume"


def _save_upload(data: bytes, safe_name: str) -> None:
    """Persist the original file for audit purposes (best effort)."""
    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        unique = f"{uuid.uuid4().hex[:8]}-{safe_name}"
        (UPLOAD_DIR / unique).write_bytes(data)
    except OSError:  # pragma: no cover - storage issues must not block parsing
        pass


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload one or more resumes (PDF or TXT)",
)
async def upload_resumes(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UploadResponse:
    settings = get_settings()
    uploaded: list[Candidate] = []
    errors: list[UploadErrorItem] = []

    for file in files:
        safe_name = _sanitize_filename(file.filename or "unnamed")
        try:
            data = await file.read()
            if len(data) > settings.max_upload_size_bytes:
                errors.append(
                    UploadErrorItem(
                        filename=safe_name,
                        error=(
                            f"File exceeds the {settings.max_upload_size_mb} MB limit."
                        ),
                    )
                )
                continue

            raw_text, file_type = extract_resume_text(data, safe_name)
            parsed = parse_resume(raw_text)

            candidate = Candidate(
                user_id=current_user.id,
                candidate_name=parsed["candidate_name"],
                email=parsed["email"],
                phone=parsed["phone"],
                skills=parsed["skills"][:60],
                experience=parsed["experience"][:20],
                education=parsed["education"][:10],
                resume_filename=safe_name,
                file_type=file_type,
                raw_text=raw_text,
                parsed_data={
                    "summary": parsed["summary"],
                    "certifications": parsed["certifications"],
                },
                parse_provider="heuristic",
            )
            db.add(candidate)
            db.flush()
            uploaded.append(candidate)
            _save_upload(data, safe_name)
        except ValueError as exc:
            errors.append(UploadErrorItem(filename=safe_name, error=str(exc)))
            continue
        except ExtractionError as exc:
            errors.append(UploadErrorItem(filename=safe_name, error=str(exc)))
            continue
        except Exception:  # noqa: BLE001 - never leak internals to clients
            errors.append(
                UploadErrorItem(
                    filename=safe_name,
                    error="Unexpected server error while processing this file.",
                )
            )

    if not uploaded and not errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files were provided.",
        )
    db.commit()
    return UploadResponse(
        uploaded=[CandidateRead.model_validate(c) for c in uploaded],
        errors=errors,
    )


@router.get("", response_model=list[CandidateRead], summary="List all candidates")
def list_candidates(
    q: str | None = Query(default=None, description="Search name/email"),
    skill: str | None = Query(default=None, description="Filter by skill"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Candidate]:
    query = db.query(Candidate).filter(Candidate.user_id == current_user.id)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (Candidate.candidate_name.ilike(like)) | (Candidate.email.ilike(like))
        )
    candidates = query.order_by(Candidate.created_at.desc()).all()
    if skill:
        needle = skill.lower()
        candidates = [
            c for c in candidates
            if any(needle in str(s).lower() for s in (c.skills or []))
        ]
    return candidates


@router.get("/{candidate_id}", response_model=CandidateDetailRead)
def get_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Candidate:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id, Candidate.user_id == current_user.id).first()
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")
    return candidate


@router.delete("/{candidate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_candidate(
    candidate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id, Candidate.user_id == current_user.id).first()
    if candidate is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Candidate not found.")
    db.delete(candidate)
    db.commit()
