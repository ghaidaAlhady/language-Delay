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


def _completed_assessment(client: TestClient, headers: dict[str, str], response: str = "always"):
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
        json={"answers": [{"question_id": q["id"], "response": response} for q in questions]},
        headers=headers,
    )
    client.post(f"/api/v1/assessments/{assessment['id']}/complete", headers=headers)
    return assessment["id"], child["id"]


def test_generate_weekly_plan_requires_completed_assessment(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    today = date.today()
    dob = date(today.year - 2, today.month, 1).isoformat()
    child = client.post(
        "/api/v1/children",
        json={"name": "Layla", "date_of_birth": dob, "gender": "female", "home_language": "ar"},
        headers=headers,
    ).json()
    assessment = client.post(
        f"/api/v1/children/{child['id']}/assessments", headers=headers
    ).json()

    response = client.post(
        f"/api/v1/assessments/{assessment['id']}/weekly-plan", headers=headers
    )
    assert response.status_code == 400


def test_generate_and_get_weekly_plan(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    assessment_id, child_id = _completed_assessment(client, headers)

    generate = client.post(
        f"/api/v1/assessments/{assessment_id}/weekly-plan", headers=headers
    )
    assert generate.status_code == 201
    body = generate.json()
    assert body["total_activities"] == 14
    assert len({a["day"] for a in body["activities"]}) == 7

    current = client.get(f"/api/v1/children/{child_id}/weekly-plan", headers=headers)
    assert current.status_code == 200
    assert current.json()["id"] == body["id"]


def test_mark_activity_completed_updates_adherence(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    assessment_id, _child_id = _completed_assessment(client, headers)
    plan = client.post(
        f"/api/v1/assessments/{assessment_id}/weekly-plan", headers=headers
    ).json()
    slot_id = plan["activities"][0]["id"]

    response = client.patch(
        f"/api/v1/weekly-plan-activities/{slot_id}",
        json={"completed": True},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["completed_count"] == 1
    assert body["adherence_percent"] > 0
    completed_slot = next(a for a in body["activities"] if a["id"] == slot_id)
    assert completed_slot["completed"] is True
    assert completed_slot["completed_at"] is not None


def test_generating_new_plan_deactivates_previous(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    assessment_id, child_id = _completed_assessment(client, headers)
    first_plan = client.post(
        f"/api/v1/assessments/{assessment_id}/weekly-plan", headers=headers
    ).json()

    second_assessment_id = client.post(
        f"/api/v1/children/{child_id}/assessments", headers=headers
    ).json()["id"]
    questions = client.get(
        f"/api/v1/assessments/{second_assessment_id}/questions", headers=headers
    ).json()
    client.post(
        f"/api/v1/assessments/{second_assessment_id}/answers",
        json={"answers": [{"question_id": q["id"], "response": "always"} for q in questions]},
        headers=headers,
    )
    client.post(f"/api/v1/assessments/{second_assessment_id}/complete", headers=headers)
    second_plan = client.post(
        f"/api/v1/assessments/{second_assessment_id}/weekly-plan", headers=headers
    ).json()

    current = client.get(f"/api/v1/children/{child_id}/weekly-plan", headers=headers)
    assert current.json()["id"] == second_plan["id"]
    assert current.json()["id"] != first_plan["id"]


def test_weekly_plan_ownership_isolation(client: TestClient) -> None:
    headers_a = _auth_headers(client, "a@example.com")
    headers_b = _auth_headers(client, "b@example.com")
    assessment_id, child_id = _completed_assessment(client, headers_a)
    plan = client.post(
        f"/api/v1/assessments/{assessment_id}/weekly-plan", headers=headers_a
    ).json()
    slot_id = plan["activities"][0]["id"]

    assert (
        client.get(f"/api/v1/children/{child_id}/weekly-plan", headers=headers_b).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/weekly-plan-activities/{slot_id}",
            json={"completed": True},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/weekly-plan-activities/{slot_id}/alternative", headers=headers_b
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/assessments/{assessment_id}/weekly-plan", headers=headers_b
        ).status_code
        == 404
    )
