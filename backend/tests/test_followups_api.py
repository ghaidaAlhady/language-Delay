from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Parent"},
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_child(client: TestClient, headers: dict[str, str]) -> str:
    today = date.today()
    dob = date(today.year - 2, today.month, min(today.day, 28)).isoformat()
    return client.post(
        "/api/v1/children",
        json={"name": "Layla", "date_of_birth": dob, "gender": "female", "home_language": "ar"},
        headers=headers,
    ).json()["id"]


def _complete_assessment(client: TestClient, headers: dict[str, str], child_id: str, response: str):
    assessment_id = client.post(
        f"/api/v1/children/{child_id}/assessments", headers=headers
    ).json()["id"]
    questions = client.get(
        f"/api/v1/assessments/{assessment_id}/questions", headers=headers
    ).json()
    client.post(
        f"/api/v1/assessments/{assessment_id}/answers",
        json={"answers": [{"question_id": q["id"], "response": response} for q in questions]},
        headers=headers,
    )
    client.post(f"/api/v1/assessments/{assessment_id}/complete", headers=headers)
    return assessment_id


def test_followup_requires_previous_assessment(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers)
    assessment_id = _complete_assessment(client, headers, child_id, "always")

    response = client.post(f"/api/v1/assessments/{assessment_id}/followup", headers=headers)
    assert response.status_code == 400


def test_followup_flow_and_plan_regeneration(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers)

    first_assessment_id = _complete_assessment(client, headers, child_id, "never")
    first_plan = client.post(
        f"/api/v1/assessments/{first_assessment_id}/weekly-plan", headers=headers
    ).json()

    second_assessment_id = _complete_assessment(client, headers, child_id, "always")
    followup = client.post(
        f"/api/v1/assessments/{second_assessment_id}/followup", headers=headers
    )
    assert followup.status_code == 201
    body = followup.json()
    assert body["previous_assessment_id"] == first_assessment_id
    assert body["current_assessment_id"] == second_assessment_id
    assert body["improvement_percent"] > 0

    detail = client.get(f"/api/v1/followups/{body['id']}", headers=headers)
    assert detail.status_code == 200

    listing = client.get(f"/api/v1/children/{child_id}/followups", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    current_plan = client.get(f"/api/v1/children/{child_id}/weekly-plan", headers=headers).json()
    assert current_plan["id"] != first_plan["id"]
    assert current_plan["assessment_id"] == second_assessment_id


def test_followup_ownership_isolation(client: TestClient) -> None:
    headers_a = _auth_headers(client, "a@example.com")
    headers_b = _auth_headers(client, "b@example.com")
    child_id = _create_child(client, headers_a)

    first_assessment_id = _complete_assessment(client, headers_a, child_id, "never")
    client.post(f"/api/v1/assessments/{first_assessment_id}/weekly-plan", headers=headers_a)
    second_assessment_id = _complete_assessment(client, headers_a, child_id, "always")
    followup = client.post(
        f"/api/v1/assessments/{second_assessment_id}/followup", headers=headers_a
    ).json()

    assert (
        client.get(f"/api/v1/followups/{followup['id']}", headers=headers_b).status_code == 404
    )
    assert (
        client.get(f"/api/v1/children/{child_id}/followups", headers=headers_b).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/assessments/{second_assessment_id}/followup", headers=headers_b
        ).status_code
        == 404
    )
