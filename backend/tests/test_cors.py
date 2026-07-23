"""CORS configuration: the frontend dev server must be an allowed origin,
and the configuration must never combine a wildcard origin with credentials.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings


def test_configured_origin_is_allowed(client: TestClient, settings: Settings) -> None:
    assert settings.cors_origins, "CORS_ORIGINS must be configured for the frontend to work."
    origin = settings.cors_origins[0]

    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_unconfigured_origin_is_not_echoed_back(client: TestClient) -> None:
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://not-an-allowed-origin.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("access-control-allow-origin") != "https://not-an-allowed-origin.example"


def test_cors_never_combines_wildcard_with_credentials(settings: Settings) -> None:
    assert "*" not in settings.cors_origins
