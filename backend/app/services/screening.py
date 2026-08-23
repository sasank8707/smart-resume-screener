"""Screening pipeline: match candidates against a job description.

Flow: candidate + job -> LLM (or mock scorer) -> validated MatchResult ->
ranked, shortlisted ScreeningResult rows persisted to the database.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.llm.provider import LLMError, MockLLMProvider, get_llm_provider
from app.llm.validation import LLMValidationError, MatchResult, validate_match_result
from app.models import Candidate, JobDescription, ScreeningResult
from app.prompts import build_matching_messages

logger = logging.getLogger("app.screening")


@dataclass
class ScreeningOutcome:
    candidate_id: int
    result: MatchResult
    provider: str
    model: str | None


# ---------------------------------------------------------------------------
# Deterministic mock scoring (offline mode)
# ---------------------------------------------------------------------------
def mock_match_candidate(candidate: Candidate, job: JobDescription) -> MatchResult:
    """Rule-based semantic-overlap scorer used when no LLM is configured.

    It implements a transparent, consistent rubric so the product is fully
    functional offline; results are clearly labelled provider="mock".
    """
    reqs = job.requirements or {}
    required = [str(s).lower() for s in reqs.get("required_skills", [])]
    required_display = [str(s) for s in reqs.get("required_skills", [])]
    preferred = [str(s).lower() for s in reqs.get("preferred_skills", [])]
    preferred_display = [str(s) for s in reqs.get("preferred_skills", [])]
    candidate_skills = {str(s).lower() for s in (candidate.skills or [])}

    # Skills evidence also appears in experience/technologies blobs.
    experience_blob = json.dumps(candidate.experience or []).lower()
    full_blob = experience_blob + " " + json.dumps(candidate.education or {}).lower()

    def has_evidence(skill: str) -> bool:
        if skill in candidate_skills:
            return True
        return skill.replace(".", r"\.") in experience_blob

    required_hits = [s for s in required if has_evidence(s)]
    preferred_hits = [s for s in preferred if has_evidence(s)]
    missing = [
        required_display[required.index(s)]
        for s in required
        if not has_evidence(s)
    ]

    # --- Weighted rubric (out of 10) ---
    score = 1.0
    if required:
        coverage = len(required_hits) / len(required)
        score += 6.0 * coverage  # up to 6 points for required skills
        # Bonus for exceeding the bar on preferred skills.
        if preferred:
            score += min(1.5, 1.5 * (len(preferred_hits) / len(preferred)))
    else:
        # No explicit requirements: fall back to generic skill breadth.
        score += min(4.0, 0.25 * len(candidate_skills))

    # Experience expectation check.
    exp_text = (reqs.get("experience_expectations") or "").lower()
    years_needed = None
    for token in exp_text.split():
        cleaned = token.strip("+.,")
        if cleaned.isdigit():
            years_needed = int(cleaned)
            break
    total_years = _estimate_total_years(candidate.experience or [])
    if years_needed:
        ratio = min(1.25, total_years / max(1, years_needed))
        score += min(2.5, 2.0 * ratio)
    elif total_years >= 1:
        score += min(1.5, 0.5 * total_years)

    # Education signal (small weight).
    if candidate.education:
        score += 0.5

    final = max(1.0, min(10.0, round(score)))
    recommendation = (
        "strong_yes" if final >= 9 else "yes" if final >= 7 else "maybe" if final >= 5 else "no"
    )

    strengths = [
        f"Evidence of {', '.join(_display(required_display, required_hits)[:5])}" if required_hits else "Relevant technical background",
    ]
    if preferred_hits:
        strengths.append(f"Bonus skills present: {', '.join(_display(preferred_display, preferred_hits)[:4])}")
    strengths.append(
        f"Approximately {total_years} year(s) of professional experience detected"
        if total_years
        else "Early-career profile"
    )

    explanation = (
        f"Deterministic offline scoring: {len(required_hits)}/{len(required) or 0} "
        f"required skills evidenced ({', '.join(required_hits[:4]) or 'none'}), "
        f"~{total_years} year(s) experience vs expected '{exp_text or 'unspecified'}'. "
        "Configure a real LLM provider for richer qualitative justification."
    )
    return MatchResult(
        match_score=float(final),
        explanation=explanation,
        strengths=strengths[:5],
        missing_skills=missing[:8],
        experience_alignment=(
            f"Detected ~{total_years} year(s); job expects {exp_text or 'unspecified'}."
            if exp_text or total_years
            else "Experience expectations not specified."
        ),
        education_alignment=(
            f"{len(candidate.education)} education entr(y/ies) found."
            if candidate.education
            else "No education information detected."
        ),
        recommendation=recommendation,
        confidence="medium" if required else "low",
    )


def _display(original: list[str], lowered_hits: list[str]) -> list[str]:
    """Map lowercased skill hits back to their original casing."""
    return [
        str(skill)
        for skill in original
        if str(skill).lower() in lowered_hits
    ]


def _estimate_total_years(experience: list[dict[str, Any]]) -> int:
    """Rough total-years estimate from parsed date ranges."""
    import re

    months = 0
    month_names = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    def parse_date(text: str) -> tuple[int, int] | None:
        text = text.strip().lower().replace("present", "2026-08").replace("current", "2026-08")
        m = re.search(r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(\d{4})", text)
        if m:
            return months_from(m.group(1)[:3], int(m.group(2)))
        m = re.match(r"^(\d{4})[-/](\d{1,2})$", text)  # ISO YYYY-MM
        if m and 1 <= int(m.group(2)) <= 12:
            return int(m.group(1)), int(m.group(2))
        m = re.match(r"^(\d{1,2})/(\d{4})$", text)
        if m:
            return int(m.group(2)), int(m.group(1))
        m = re.fullmatch(r"(19|20)\d{2}", text)
        if m:
            return int(text), 1
        return None

    def months_from(mon: str, year: int) -> tuple[int, int]:
        return year, month_names[mon]

    for entry in experience:
        start, end = entry.get("start_date"), entry.get("end_date")
        if not start or not end:
            continue
        parsed_start, parsed_end = parse_date(start), parse_date(end)
        if not parsed_start or not parsed_end:
            continue
        delta = (parsed_end[0] - parsed_start[0]) * 12 + (parsed_end[1] - parsed_start[1])
        if 0 < delta <= 600:
            months += delta
    return max(0, round(months / 12))


# ---------------------------------------------------------------------------
# Core screening operations
# ---------------------------------------------------------------------------
def screen_candidate(
    db: Session,
    candidate: Candidate,
    job: JobDescription,
    threshold: float | None = None,
) -> ScreeningOutcome:
    """Run one candidate through the matching pipeline."""
    settings = get_settings()
    threshold = threshold if threshold is not None else settings.shortlist_threshold

    provider = get_llm_provider(settings)
    outcome: MatchResult | None = None
    used_provider = provider.name
    used_model = provider.model

    if isinstance(provider, MockLLMProvider):
        outcome = mock_match_candidate(candidate, job)
    else:
        system, user = build_matching_messages(
            job_title=job.title,
            job_requirements=json.dumps(job.requirements or {}, indent=1),
            job_text=job.description_text,
            candidate_name=candidate.candidate_name or "",
            candidate_skills=", ".join(candidate.skills or []),
            candidate_experience=json.dumps(candidate.experience or [], indent=1),
            candidate_education=json.dumps(candidate.education or [], indent=1),
            candidate_certifications=", ".join(
                (candidate.parsed_data or {}).get("certifications", [])
            ),
        )
        try:
            raw = provider.complete_json(system, user)
            outcome = validate_match_result(raw)
        except (LLMError, LLMValidationError) as exc:
            logger.warning(
                "LLM screening failed for candidate %s (%s); using mock fallback.",
                candidate.id,
                exc,
            )
            outcome = mock_match_candidate(candidate, job)
            used_provider = "mock-fallback"

    return ScreeningOutcome(
        candidate_id=candidate.id,
        result=outcome,
        provider=used_provider,
        model=used_model,
    )


def persist_screening_result(
    db: Session,
    candidate: Candidate,
    job: JobDescription,
    outcome: ScreeningOutcome,
    threshold: float,
) -> ScreeningResult:
    """Upsert one ScreeningResult row (re-screening overwrites the pair)."""
    existing = (
        db.query(ScreeningResult)
        .filter(
            ScreeningResult.candidate_id == candidate.id,
            ScreeningResult.job_description_id == job.id,
        )
        .one_or_none()
    )
    result = existing or ScreeningResult(
        candidate_id=candidate.id,
        job_description_id=job.id,
    )
    result.user_id = job.user_id
    result.match_score = float(outcome.result.match_score)
    result.shortlisted = result.match_score >= threshold
    result.explanation = outcome.result.explanation
    result.strengths = outcome.result.strengths
    result.missing_skills = outcome.result.missing_skills
    result.experience_alignment = outcome.result.experience_alignment
    result.education_alignment = outcome.result.education_alignment
    result.recommendation = outcome.result.recommendation
    result.confidence = outcome.result.confidence
    result.shortlist_threshold = threshold
    result.llm_provider = outcome.provider
    result.llm_model = outcome.model
    if existing is None:
        db.add(result)
    db.commit()
    db.refresh(result)
    return result


def run_screening(
    db: Session,
    job: JobDescription,
    candidates: list[Candidate],
    threshold: float | None = None,
) -> list[ScreeningResult]:
    """Screen every candidate against the job, rank, shortlist and persist."""
    settings = get_settings()
    threshold = threshold if threshold is not None else settings.shortlist_threshold
    results: list[ScreeningResult] = []
    for candidate in candidates:
        outcome = screen_candidate(db, candidate, job, threshold)
        results.append(persist_screening_result(db, candidate, job, outcome, threshold))
    results.sort(key=lambda r: (-r.match_score, (r.candidate.candidate_name or "")))
    return results
