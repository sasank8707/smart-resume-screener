"""Tests for LLM output validation and safe-recovery behaviour."""

import pytest
from pydantic import ValidationError

from app.llm.validation import (
    LLMValidationError,
    MatchResult,
    parse_llm_json,
    parse_match_response,
    validate_match_result,
)


class TestJsonRecovery:
    def test_plain_json(self):
        data = parse_llm_json('{"match_score": 8}')
        assert data == {"match_score": 8}

    def test_code_fenced_json(self):
        text = '```json\n{"match_score": 7}\n```'
        assert parse_llm_json(text)["match_score"] == 7

    def test_json_with_surrounding_prose(self):
        text = 'Here is my analysis:\n{"match_score": 5, "explanation": "ok"}\nDone.'
        assert parse_llm_json(text)["explanation"] == "ok"

    def test_malformed_raises(self):
        with pytest.raises(LLMValidationError):
            parse_llm_json("no json at all")

    def test_non_object_raises(self):
        with pytest.raises(LLMValidationError):
            parse_llm_json("[1, 2, 3]")


class TestMatchResultValidation:
    def test_valid_payload(self):
        payload = {
            "match_score": 8,
            "explanation": "Strong fit.",
            "strengths": ["Python", "FastAPI"],
            "missing_skills": ["Kubernetes"],
            "experience_alignment": "6 years vs 5 expected.",
            "education_alignment": "Matches.",
            "recommendation": "yes",
            "confidence": "high",
        }
        result = validate_match_result(payload)
        assert result.match_score == 8.0
        assert result.recommendation == "yes"

    def test_missing_explanation_rejected(self):
        with pytest.raises((LLMValidationError, ValidationError)):
            validate_match_result({"match_score": 8})

    def test_out_of_range_score_rejected(self):
        with pytest.raises((LLMValidationError, ValidationError)):
            validate_match_result(
                {"match_score": 11, "explanation": "x"}
            )

    def test_string_score_coerced(self):
        result = validate_match_result({"match_score": "8/10", "explanation": "ok"})
        assert result.match_score == 8.0

    def test_invalid_recommendation_normalised(self):
        result = validate_match_result(
            {"match_score": 4, "explanation": "ok", "recommendation": "STRONG NO"}
        )
        assert result.recommendation == "maybe"

    def test_null_lists_become_empty(self):
        result = validate_match_result(
            {"match_score": 5, "explanation": "ok", "strengths": None,
             "missing_skills": None}
        )
        assert result.strengths == []
        assert result.missing_skills == []


class TestFullPipeline:
    def test_parse_match_response_end_to_end(self):
        raw = '''Based on my analysis:
```json
{"match_score": "9", "explanation": "Excellent alignment.",
 "strengths": ["Deep Python"], "missing_skills": [],
 "experience_alignment": "Exceeds bar.", "education_alignment": "Meets.",
 "recommendation": "strong yes", "confidence": "high"}
```
Let me know if you need anything else.'''
        result = parse_match_response(raw)
        assert isinstance(result, MatchResult)
        assert result.match_score == 9.0
        assert result.recommendation == "strong_yes"
