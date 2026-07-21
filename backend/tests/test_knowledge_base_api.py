from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str = "parent@example.com") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Parent"},
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_list_activities_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/activities", params={"age": 2})
    assert response.status_code == 401


def test_list_activities_by_age(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.get("/api/v1/activities", params={"age": 2}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 25


def test_list_activities_by_age_and_domain(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.get(
        "/api/v1/activities",
        params={"age": 2, "domain": "اللغة الاستقبالية"},
        headers=headers,
    )
    assert response.status_code == 200
    activities = response.json()
    assert len(activities) > 0
    assert all(a["domain"] == "اللغة الاستقبالية" for a in activities)


def test_list_references(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.get("/api/v1/references", headers=headers)
    assert response.status_code == 200
    codes = {r["code"] for r in response.json()}
    assert "ASHA" in codes


def test_get_assessment_activities(client: TestClient) -> None:
    headers = _auth_headers(client)
    today = date.today()
    dob = date(today.year - 2, today.month, min(today.day, 28)).isoformat()
    child = client.post(
        "/api/v1/children",
        json={"name": "Layla", "date_of_birth": dob, "gender": "female", "home_language": "ar"},
        headers=headers,
    ).json()
    assessment = client.post(
        f"/api/v1/children/{child['id']}/assessments", headers=headers
    ).json()
    questions = client.get(
        f"/api/v1/assessments/{assessment['id']}/questions", headers=headers
    ).json()
    client.post(
        f"/api/v1/assessments/{assessment['id']}/answers",
        json={"answers": [{"question_id": q["id"], "response": "never"} for q in questions]},
        headers=headers,
    )
    client.post(f"/api/v1/assessments/{assessment['id']}/complete", headers=headers)

    response = client.get(
        f"/api/v1/assessments/{assessment['id']}/activities", headers=headers
    )
    assert response.status_code == 200
    activities = response.json()
    assert len(activities) > 0
    assert all("id" in a and "name" in a for a in activities)
