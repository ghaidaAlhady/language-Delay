"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "Smart Guide for Children's Language Delay"
    api_v1_prefix: str = "/api/v1"

    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    database_url: str = "sqlite+aiosqlite:///./language_delay.db"

    cors_origins: list[str] = []

    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    gemini_enabled: bool = False
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = ""
    gemini_timeout_seconds: int = Field(default=15, ge=1, le=60)
    gemini_max_retries: int = Field(default=1, ge=0, le=3)
    gemini_prompt_version: Literal["v1"] = "v1"

    #: Test-only provider selection. It is ignored unless ``APP_ENV=e2e``.
    ai_test_provider: str = ""

    google_client_id: str = ""

    knowledge_base_dir: str = "../knowledge_base"

    default_language: str = "ar"
    log_level: str = "INFO"

    #: Optional override for the packaged open-licensed Tajawal TTF. The
    #: packaged font is used by default so Arabic PDFs work on another
    #: machine without relying on a private/system font.
    pdf_arabic_font_path: str = ""

    @property
    def llm_configured(self) -> bool:
        """Whether a real external LLM provider is configured.

        Deterministic knowledge-base-grounded fallbacks must be used whenever
        this is false, per the project's non-hallucination requirement.
        """
        placeholder_values = {"", "replace_me"}
        return self.llm_provider not in placeholder_values and bool(self.llm_api_key)

    @property
    def gemini_configured(self) -> bool:
        """Whether Gemini may be called for optional assisted wording."""
        placeholder_values = {"", "replace_me"}
        api_key = self.gemini_api_key.get_secret_value()
        return (
            self.gemini_enabled
            and api_key not in placeholder_values
            and self.gemini_model not in placeholder_values
        )

    @property
    def knowledge_base_path(self) -> Path:
        return Path(self.knowledge_base_dir).resolve()

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
