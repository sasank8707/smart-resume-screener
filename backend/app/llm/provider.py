"""Provider-agnostic LLM abstraction.

Supported providers (configured via environment variables, never hard-coded):
- ``mock``      : deterministic offline scorer used for development/tests.
- ``openai``    : OpenAI or any OpenAI-compatible endpoint (Groq, Together,
                  Ollama, LM Studio...) via the chat completions API.
- ``anthropic`` : Anthropic Claude via the Messages API.

All providers implement ``complete_json(system, user) -> dict`` and raise
``LLMError`` on transport/format failures so callers can retry safely.
"""

from __future__ import annotations

import json
import logging
import re
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import Settings
from app.llm.validation import parse_llm_json

logger = logging.getLogger("app.llm")


class LLMError(RuntimeError):
    """Raised when an LLM request fails at transport or format level."""


class BaseLLMProvider(ABC):
    name: str = "base"
    model: str | None = None

    @abstractmethod
    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        """Send a prompt and return a validated JSON object."""


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences some models wrap JSON in."""
    text = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.S)
    if fence:
        return fence.group(1).strip()
    return text


class MockLLMProvider(BaseLLMProvider):
    """Deterministic rule-based provider.

    Produces a genuine semantic-overlap score between candidate data and job
    requirements so the whole product works end-to-end without an API key
    (demos, CI, local development). Clearly labelled as "mock" everywhere.
    """

    name = "mock"

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        # The mock provider implements scoring directly; see services/screening.py
        raise LLMError(
            "MockLLMProvider does not implement generic completion; "
            "use screening.mock_match_candidate() instead."
        )


class OpenAICompatibleProvider(BaseLLMProvider):
    """OpenAI Chat Completions-compatible provider (also Groq/Ollama/Together)."""

    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise LLMError(
                "OPENAI_API_KEY is not configured. Set it in your .env file."
            )
        self.api_key = settings.openai_api_key
        self.base_url = settings.openai_base_url.rstrip("/")
        self.model = settings.openai_model
        self.timeout = settings.llm_timeout_seconds
        self.max_retries = max(1, settings.llm_max_retries)
        self.name = "openai"

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):  # initial try + retries
            try:
                response = httpx.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    last_error = LLMError(
                        f"LLM endpoint returned HTTP {response.status_code}"
                    )
                    time.sleep(0.8 * attempt)
                    continue
                response.raise_for_status()
                body = response.json()
                content = body["choices"][0]["message"]["content"]
                return parse_llm_json(_strip_code_fences(content))
            except LLMError:
                raise
            except httpx.HTTPStatusError as exc:
                last_error = LLMError(f"LLM HTTP error: {exc.response.status_code}")
                break  # non-retryable client error
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                last_error = LLMError(f"LLM request failed: {type(exc).__name__}")
                time.sleep(0.8 * attempt)

        logger.error("LLM completion failed after retries: %s", last_error)
        raise last_error or LLMError("LLM request failed.")


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude via the Messages API."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, settings: Settings):
        if not settings.anthropic_api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY is not configured. Set it in your .env file."
            )
        self.api_key = settings.anthropic_api_key
        self.model = settings.anthropic_model
        self.timeout = settings.llm_timeout_seconds
        self.max_retries = max(1, settings.llm_max_retries)
        self.name = "anthropic"

    def complete_json(self, system: str, user: str) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "max_tokens": 2000,
            "temperature": 0.1,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                response = httpx.post(
                    self.API_URL, json=payload, headers=headers, timeout=self.timeout
                )
                if response.status_code in (429, 500, 502, 503, 504):
                    last_error = LLMError(
                        f"LLM endpoint returned HTTP {response.status_code}"
                    )
                    time.sleep(0.8 * attempt)
                    continue
                response.raise_for_status()
                body = response.json()
                content = "".join(
                    block.get("text", "") for block in body.get("content", [])
                )
                return parse_llm_json(_strip_code_fences(content))
            except LLMError:
                raise
            except httpx.HTTPStatusError as exc:
                last_error = LLMError(f"LLM HTTP error: {exc.response.status_code}")
                break
            except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
                last_error = LLMError(f"LLM request failed: {type(exc).__name__}")
                time.sleep(0.8 * attempt)

        logger.error("LLM completion failed after retries: %s", last_error)
        raise last_error or LLMError("LLM request failed.")


def get_llm_provider(settings: Settings | None = None) -> BaseLLMProvider:
    """Factory returning the configured provider instance."""
    from app.core.config import get_settings

    cfg = settings or get_settings()
    if cfg.llm_provider == "openai":
        return OpenAICompatibleProvider(cfg)
    if cfg.llm_provider == "anthropic":
        return AnthropicProvider(cfg)
    return MockLLMProvider()


def safe_parse_json_text(text: str) -> Any:
    """Best-effort recovery of JSON objects embedded in model output."""
    cleaned = _strip_code_fences(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    raise LLMError("Unable to parse JSON from model output.")
