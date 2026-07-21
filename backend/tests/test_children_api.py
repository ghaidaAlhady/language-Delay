from __future__ import annotations

from fastapi.testclient import TestClient

CHILD_PAYLOAD = {
    "name": "Layla",
    "date_of_birth": "2023-01-01",
    "gender": "female",
    "home_language": "ar",
}


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Parent"},
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_create_child_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/children", json=CHILD_PAYLOAD)
    assert response.status_code == 401


def test_create_and_get_child(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    response = client.post("/api/v1/children", json=CHILD_PAYLOAD, headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Layla"
    assert body["age_years"] == 3
    assert body["is_assessment_age_eligible"] is True

    response = client.get(f"/api/v1/children/{body['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == body["id"]


def test_list_children_returns_only_mine(client: TestClient) -> None:
    headers_a = _auth_headers(client, "a@example.com")
    headers_b = _auth_headers(client, "b@example.com")

    client.post("/api/v1/children", json=CHILD_PAYLOAD, headers=headers_a)
    client.post(
        "/api/v1/children", json={**CHILD_PAYLOAD, "name": "Omar"}, headers=headers_b
    )

    response = client.get("/api/v1/children", headers=headers_a)
    assert response.status_code == 200
    names = [child["name"] for child in response.json()]
    assert names == ["Layla"]


def test_ownership_isolation_between_two_users(client: TestClient) -> None:
    headers_a = _auth_headers(client, "a@example.com")
    headers_b = _auth_headers(client, "b@example.com")

    created = client.post("/api/v1/children", json=CHILD_PAYLOAD, headers=headers_a).json()
    child_id = created["id"]

    # User B must not be able to read, update, or delete user A's child.
    assert client.get(f"/api/v1/children/{child_id}", headers=headers_b).status_code == 404
    assert (
        client.patch(
            f"/api/v1/children/{child_id}", json={"name": "Hacked"}, headers=headers_b
        ).status_code
        == 404
    )
    assert client.delete(f"/api/v1/children/{child_id}", headers=headers_b).status_code == 404

    # The child must be untouched and still visible to its real owner.
    response = client.get(f"/api/v1/children/{child_id}", headers=headers_a)
    assert response.status_code == 200
    assert response.json()["name"] == "Layla"


def test_update_child_partial(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    created = client.post("/api/v1/children", json=CHILD_PAYLOAD, headers=headers).json()

    response = client.patch(
        f"/api/v1/children/{created['id']}",
        json={"has_hearing_problems": True},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["has_hearing_problems"] is True
    assert body["name"] == "Layla"


def test_delete_child(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    created = client.post("/api/v1/children", json=CHILD_PAYLOAD, headers=headers).json()

    response = client.delete(f"/api/v1/children/{created['id']}", headers=headers)
    assert response.status_code == 204

    response = client.get(f"/api/v1/children/{created['id']}", headers=headers)
    assert response.status_code == 404


def test_create_child_rejects_future_date_of_birth(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    response = client.post(
        "/api/v1/children", json={**CHILD_PAYLOAD, "date_of_birth": "2999-01-01"}, headers=headers
    )
    assert response.status_code == 422


def test_get_nonexistent_child_returns_404(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    response = client.get("/api/v1/children/does-not-exist", headers=headers)
    assert response.status_code == 404
