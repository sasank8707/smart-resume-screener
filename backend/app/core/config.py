"""Application configuration loaded from environment variables / .env file."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent

ALLOWED_PROVIDERS = ("mock", "openai", "anthropic")


class Settings(BaseSettings):
    """Central, typed application settings.

    Every value can be overridden through environment variables or a `.env`
    file located in the `backend/` directory.  Secrets are never hard-coded.
    """

    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- LLM ---
    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 2

    # --- Screening ---
    shortlist_threshold: float = Field(default=7.0, ge=1.0, le=10.0)
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)

    # --- Server ---
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Database ---
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'smart_resume_screener.db').as_posix()}"

    @field_validator("llm_provider")
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in ALLOWED_PROVIDERS:
            raise ValueError(
                f"LLM_PROVIDER must be one of {ALLOWED_PROVIDERS}, got '{value}'"
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance (importable anywhere in the app)."""
    return Settings()
