"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

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

    google_client_id: str = ""

    knowledge_base_dir: str = "../knowledge_base"

    default_language: str = "ar"
    log_level: str = "INFO"

    #: Path to a Unicode TTF font with Arabic glyph coverage (e.g. Amiri,
    #: Noto Naskh Arabic), supplied by the deployment environment. No font
    #: file is committed to this repository (licensing); without one, PDF
    #: generation still produces a real file but Arabic text will not render
    #: legibly. See docs/DECISIONS_AND_ASSUMPTIONS.md.
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
    def knowledge_base_path(self) -> Path:
        return Path(self.knowledge_base_dir).resolve()

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
