"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(value: str) -> str:
    """Normalize common hosted PostgreSQL URLs for SQLAlchemy asyncpg.

    Neon and other providers commonly return ``postgres://`` or
    ``postgresql://`` URLs with libpq-only query parameters. The application
    uses SQLAlchemy's async engine, so production PostgreSQL connections must
    use the ``postgresql+asyncpg`` dialect and asyncpg-compatible SSL options.
    SQLite URLs are returned unchanged for local development and tests.
    """
    raw = value.strip()
    if not raw or raw.startswith("sqlite"):
        return raw

    if raw.startswith("postgres://"):
        raw = "postgresql://" + raw[len("postgres://") :]

    if not raw.startswith(("postgresql://", "postgresql+asyncpg://")):
        return raw

    parts = urlsplit(raw)
    query_items = parse_qsl(parts.query, keep_blank_values=True)
    normalized_query: list[tuple[str, str]] = []
    ssl_value: str | None = None
    for key, item_value in query_items:
        lowered = key.lower()
        if lowered == "sslmode":
            ssl_value = item_value
            continue
        if lowered == "channel_binding":
            # libpq option not understood by asyncpg. TLS is still enforced
            # through the translated ``ssl`` option below.
            continue
        normalized_query.append((key, item_value))

    if ssl_value and not any(key.lower() == "ssl" for key, _ in normalized_query):
        normalized_query.append(("ssl", ssl_value))

    return urlunsplit(
        (
            "postgresql+asyncpg",
            parts.netloc,
            parts.path,
            urlencode(normalized_query),
            parts.fragment,
        )
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "Smart Guide for Children's Language Delay"
    api_v1_prefix: str = "/api/v1"

    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    database_url: str = "sqlite+aiosqlite:///./language_delay.db"

    @field_validator("database_url", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: Any) -> str:
        return normalize_database_url(str(value))

    cors_origins: list[str] = []

    @field_validator("cors_origins")
    @classmethod
    def _normalize_cors_origins(cls, origins: list[str]) -> list[str]:
        normalized = [origin.strip().rstrip("/") for origin in origins if origin.strip()]
        return list(dict.fromkeys(normalized))

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

    @model_validator(mode="after")
    def _validate_production_safety(self) -> "Settings":
        if self.app_env.casefold() != "production":
            return self

        if self.is_sqlite:
            raise ValueError(
                "Production requires persistent PostgreSQL; SQLite is not allowed."
            )

        if len(self.secret_key) < 32 or self.secret_key.casefold().startswith(
            ("replace", "change", "test")
        ):
            raise ValueError(
                "Production SECRET_KEY must be a strong random value of at least 32 characters."
            )

        if not self.cors_origins:
            raise ValueError(
                "Production CORS_ORIGINS must contain the exact HTTPS frontend origin."
            )

        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme.casefold() != "https"
                or not parsed.netloc
                or parsed.username is not None
                or parsed.password is not None
                or parsed.query
                or parsed.fragment
                or parsed.path not in {"", "/"}
            ):
                raise ValueError(
                    "Production CORS_ORIGINS must contain exact HTTPS origins without "
                    "wildcards, credentials, paths, queries, or fragments."
                )
        return self

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
        configured = Path(self.knowledge_base_dir)
        if configured.is_absolute():
            return configured.resolve()
        backend_root = Path(__file__).resolve().parents[2]
        return (backend_root / configured).resolve()

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_postgresql(self) -> bool:
        return self.database_url.startswith("postgresql+asyncpg")


@lru_cache
def get_settings() -> Settings:
    return Settings()
