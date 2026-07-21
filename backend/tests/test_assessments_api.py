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


def _create_child(client: TestClient, headers: dict[str, str], age: int = 2) -> str:
    today = date.today()
    dob = date(today.year - age, today.month, min(today.day, 28)).isoformat()
    response = client.post(
        "/api/v1/children",
        json={
            "name": "Layla",
            "date_of_birth": dob,
            "gender": "female",
            "home_language": "ar",
        },
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_start_assessment_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/children/does-not-exist/assessments")
    assert response.status_code == 401


def test_start_assessment_returns_in_progress(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers, age=2)

    response = client.post(f"/api/v1/children/{child_id}/assessments", headers=headers)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["age_at_assessment"] == 2
    assert body["total_questions"] == 20


def test_start_assessment_rejects_ineligible_age(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers, age=8)

    response = client.post(f"/api/v1/children/{child_id}/assessments", headers=headers)
    assert response.status_code == 400


def test_get_assessment_questions(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers, age=3)
    assessment = client.post(
        f"/api/v1/children/{child_id}/assessments", headers=headers
    ).json()

    response = client.get(
        f"/api/v1/assessments/{assessment['id']}/questions", headers=headers
    )
    assert response.status_code == 200
    questions = response.json()
    assert len(questions) == 20
    assert all(q["age"] == 3 for q in questions)


def test_standalone_question_lookup_by_age(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    response = client.get("/api/v1/assessment-questions", params={"age": 4}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 20


def test_standalone_question_lookup_rejects_out_of_range_age(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    response = client.get("/api/v1/assessment-questions", params={"age": 10}, headers=headers)
    assert response.status_code == 422


def test_full_assessment_flow(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers, age=2)
    assessment = client.post(
        f"/api/v1/children/{child_id}/assessments", headers=headers
    ).json()
    assessment_id = assessment["id"]

    questions = client.get(
        f"/api/v1/assessments/{assessment_id}/questions", headers=headers
    ).json()

    submit = client.post(
        f"/api/v1/assessments/{assessment_id}/answers",
        json={"answers": [{"question_id": q["id"], "response": "always"} for q in questions]},
        headers=headers,
    )
    assert submit.status_code == 200
    assert submit.json()["answered_count"] == 20

    complete = client.post(f"/api/v1/assessments/{assessment_id}/complete", headers=headers)
    assert complete.status_code == 200
    body = complete.json()
    assert body["status"] == "completed"
    assert body["overall_severity"] == "طبيعي"
    assert len(body["domain_results"]) == 4
    assert body["strengths"]

    result = client.get(f"/api/v1/assessments/{assessment_id}", headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "completed"


def test_complete_fails_with_missing_answers(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers, age=2)
    assessment = client.post(
        f"/api/v1/children/{child_id}/assessments", headers=headers
    ).json()

    response = client.post(
        f"/api/v1/assessments/{assessment['id']}/complete", headers=headers
    )
    assert response.status_code == 400
    assert "missing_question_ids" in response.json()["error"]["details"]


def test_assessment_history_lists_all_attempts(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers, age=2)
    client.post(f"/api/v1/children/{child_id}/assessments", headers=headers)
    client.post(f"/api/v1/children/{child_id}/assessments", headers=headers)

    response = client.get(f"/api/v1/children/{child_id}/assessments", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_assessment_ownership_isolation(client: TestClient) -> None:
    headers_a = _auth_headers(client, "a@example.com")
    headers_b = _auth_headers(client, "b@example.com")
    child_id = _create_child(client, headers_a, age=2)
    assessment = client.post(
        f"/api/v1/children/{child_id}/assessments", headers=headers_a
    ).json()

    assert (
        client.get(f"/api/v1/assessments/{assessment['id']}", headers=headers_b).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/assessments/{assessment['id']}/questions", headers=headers_b
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/assessments/{assessment['id']}/answers",
            json={"answers": [{"question_id": "Q001", "response": "always"}]},
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.get(f"/api/v1/children/{child_id}/assessments", headers=headers_b).status_code
        == 404
    )


def test_submit_invalid_response_value_returns_422(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers, age=2)
    assessment = client.post(
        f"/api/v1/children/{child_id}/assessments", headers=headers
    ).json()

    response = client.post(
        f"/api/v1/assessments/{assessment['id']}/answers",
        json={"answers": [{"question_id": "Q001", "response": "maybe"}]},
        headers=headers,
    )
    assert response.status_code == 422
