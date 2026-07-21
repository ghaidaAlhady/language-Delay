from __future__ import annotations

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "parent@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Test Parent"},
    )
    assert response.status_code == 201
    return response.json()


def _login(client: TestClient, email: str = "parent@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    )
    assert response.status_code == 200
    return response.json()


def test_register_returns_user(client: TestClient) -> None:
    body = _register(client)
    assert body["email"] == "parent@example.com"
    assert "hashed_password" not in body


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "parent@example.com", "password": "anotherpass1", "display_name": "X"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "a@example.com", "password": "short", "display_name": "X"},
    )
    assert response.status_code == 422


def test_register_rejects_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "supersecret1", "display_name": "X"},
    )
    assert response.status_code == 422


def test_login_returns_tokens(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    _register(client)
    response = client.post(
        "/api/v1/auth/login", json={"email": "parent@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


def test_me_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "parent@example.com"


def test_me_rejects_garbage_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_full_token_lifecycle(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)

    refreshed = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    reused = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reused.status_code == 401

    logout = client.post(
        "/api/v1/auth/logout", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert logout.status_code == 204

    reused_after_logout = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}
    )
    assert reused_after_logout.status_code == 401


def test_delete_account_revokes_access(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    response = client.delete("/api/v1/auth/me", headers=headers)
    assert response.status_code == 204

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
