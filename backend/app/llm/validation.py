"""Strict validation of LLM output.

The application never trusts raw model output: every response is parsed and
validated against an explicit schema. Malformed responses trigger a safe
recovery path (retry / heuristic fallback) instead of crashing.
"""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

logger = logging.getLogger("app.llm")

VALID_RECOMMENDATIONS = {"strong_yes", "yes", "maybe", "no"}
VALID_CONFIDENCE = {"low", "medium", "high"}


class MatchResult(BaseModel):
    """Validated schema for the resume/job matching output."""

    model_config = ConfigDict(extra="ignore")

    match_score: float = Field(ge=1.0, le=10.0)
    explanation: str = Field(min_length=1)
    strengths: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    experience_alignment: str = ""
    education_alignment: str = ""
    recommendation: str = "maybe"
    confidence: str | None = None

    @field_validator("match_score", mode="before")
    @classmethod
    def _coerce_score(cls, value: Any) -> float:
        if isinstance(value, str):
            value = value.strip().replace("/10", "").strip()
        try:
            return float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            raise ValueError("match_score must be a number between 1 and 10")

    @field_validator("recommendation", mode="before")
    @classmethod
    def _normalise_recommendation(cls, value: Any) -> str:
        text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "strong_yes": "strong_yes",
            "strongly_recommend": "strong_yes",
            "yes": "yes",
            "recommend": "yes",
            "maybe": "maybe",
            "no": "no",
            "not_recommended": "no",
        }
        return aliases.get(text, "maybe")

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalise_confidence(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip().lower()
        return text if text in VALID_CONFIDENCE else "medium"

    @field_validator("strengths", "missing_skills", mode="before")
    @classmethod
    def _coerce_string_lists(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            value = [part.strip() for part in re.split(r"[;]", value) if part.strip()]
        if not isinstance(value, list):
            return []
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned[:10]


def parse_llm_json(text: str) -> dict[str, Any]:
    """Parse JSON from raw model text with best-effort recovery.

    Raises:
        LLMValidationError: if no JSON object can be recovered.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Recovery strategy 1: grab the outermost {...} block.
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise LLMValidationError("Model returned no JSON object.")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMValidationError(f"Model returned malformed JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LLMValidationError("Model JSON was not an object.")
    return data


class LLMValidationError(ValueError):
    """Raised when model output cannot be recovered into a valid schema."""


def validate_match_result(data: dict[str, Any]) -> MatchResult:
    """Validate a parsed match payload against the MatchResult schema."""
    try:
        return MatchResult.model_validate(data)
    except ValidationError as exc:
        logger.warning("LLM match payload failed validation: %s", exc.errors()[:3])
        raise LLMValidationError(
            f"LLM output did not match the required schema: {exc.error_count()} error(s)"
        ) from exc


def parse_match_response(raw_text: str) -> MatchResult:
    """Full pipeline: raw text -> JSON -> validated MatchResult."""
    return validate_match_result(parse_llm_json(raw_text))
