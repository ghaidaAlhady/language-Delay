from __future__ import annotations

import pytest

from app.core.config import Settings, normalize_database_url

PRODUCTION_SECRET = "x" * 48
PRODUCTION_CORS = ["https://smart-guide.example"]


def test_sqlite_database_url_is_unchanged() -> None:
    value = "sqlite+aiosqlite:///./language_delay.db"
    assert normalize_database_url(value) == value


def test_hosted_postgres_url_is_normalized_for_asyncpg() -> None:
    normalized = normalize_database_url(
        "postgresql://user:secret@example.neon.tech/app"
        "?sslmode=require&channel_binding=require&application_name=smart-guide"
    )
    assert normalized.startswith("postgresql+asyncpg://")
    assert "ssl=require" in normalized
    assert "sslmode" not in normalized
    assert "channel_binding" not in normalized
    assert "application_name=smart-guide" in normalized


def test_settings_apply_database_url_normalization() -> None:
    settings = Settings(
        secret_key="test-secret",
        database_url="postgres://user:secret@host/db?sslmode=require",
        _env_file=None,
    )
    assert settings.is_postgresql is True
    assert settings.database_url == "postgresql+asyncpg://user:secret@host/db?ssl=require"


def test_cors_origins_are_trimmed_deduplicated_and_untrailed() -> None:
    settings = Settings(
        secret_key="test-secret",
        cors_origins=[
            " https://smart-guide.example/ ",
            "https://smart-guide.example",
            "",
        ],
        _env_file=None,
    )
    assert settings.cors_origins == ["https://smart-guide.example"]


def test_production_accepts_persistent_postgres_and_exact_https_cors() -> None:
    settings = Settings(
        secret_key=PRODUCTION_SECRET,
        app_env="production",
        database_url="postgresql://user:secret@host/db?sslmode=require",
        cors_origins=PRODUCTION_CORS,
        _env_file=None,
    )
    assert settings.is_postgresql is True


def test_production_rejects_ephemeral_sqlite() -> None:
    with pytest.raises(ValueError, match="persistent PostgreSQL"):
        Settings(
            secret_key=PRODUCTION_SECRET,
            app_env="production",
            cors_origins=PRODUCTION_CORS,
            _env_file=None,
        )


def test_production_rejects_short_or_placeholder_secret() -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(
            secret_key="test-secret",
            app_env="production",
            database_url="postgresql+asyncpg://user:password@localhost/app",
            cors_origins=PRODUCTION_CORS,
            _env_file=None,
        )


def test_production_requires_cors_origin() -> None:
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        Settings(
            secret_key=PRODUCTION_SECRET,
            app_env="production",
            database_url="postgresql+asyncpg://user:password@localhost/app",
            _env_file=None,
        )


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "http://smart-guide.example",
        "https://smart-guide.example/app",
        "https://user:password@smart-guide.example",
        "https://smart-guide.example?preview=1",
    ],
)
def test_production_rejects_non_exact_https_cors(origin: str) -> None:
    with pytest.raises(ValueError, match="exact HTTPS origins"):
        Settings(
            secret_key=PRODUCTION_SECRET,
            app_env="production",
            database_url="postgresql+asyncpg://user:password@localhost/app",
            cors_origins=[origin],
            _env_file=None,
        )
