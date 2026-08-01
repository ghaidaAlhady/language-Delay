from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "display_name": "Parent",
        },
    )
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "supersecret1"},
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create_child(client: TestClient, headers: dict[str, str]) -> str:
    today = date.today()
    dob = date(today.year - 2, today.month, min(today.day, 28)).isoformat()
    return client.post(
        "/api/v1/children",
        json={
            "name": "Layla",
            "date_of_birth": dob,
            "gender": "female",
            "home_language": "ar",
        },
        headers=headers,
    ).json()["id"]


def _create_plan(
    client: TestClient,
    headers: dict[str, str],
    child_id: str,
    *,
    complete: bool,
) -> dict:
    assessment_id = client.post(
        f"/api/v1/children/{child_id}/assessments", headers=headers
    ).json()["id"]
    questions = client.get(
        f"/api/v1/assessments/{assessment_id}/questions", headers=headers
    ).json()
    client.post(
        f"/api/v1/assessments/{assessment_id}/answers",
        json={
            "answers": [
                {"question_id": question["id"], "response": "never"}
                for question in questions
            ]
        },
        headers=headers,
    )
    client.post(
        f"/api/v1/assessments/{assessment_id}/complete", headers=headers
    )
    plan = client.post(
        f"/api/v1/assessments/{assessment_id}/weekly-plan", headers=headers
    ).json()
    if complete:
        for slot in plan["activities"]:
            plan = client.patch(
                f"/api/v1/weekly-plan-activities/{slot['id']}",
                json={"completed": True},
                headers=headers,
            ).json()
    return plan


def _answers(context: dict, response: str = "always") -> list[dict[str, str]]:
    return [
        {"question_id": question["id"], "response": response}
        for question in context["questions"]
    ]


def test_weekly_followup_requires_authentication(client: TestClient) -> None:
    assert (
        client.get("/api/v1/weekly-plans/unknown/followup-questions").status_code
        == 401
    )
    assert client.post("/api/v1/weekly-plans/unknown/followup").status_code == 401
    assert client.get("/api/v1/followups/unknown").status_code == 401
    assert client.get("/api/v1/children/unknown/followups").status_code == 401


def test_questions_require_completed_active_plan(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers)
    plan = _create_plan(client, headers, child_id, complete=False)

    response = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions",
        headers=headers,
    )
    assert response.status_code == 400


def test_questions_available_at_70_percent_completion_not_required_at_100(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers)
    plan = _create_plan(client, headers, child_id, complete=False)
    slots = plan["activities"]
    assert len(slots) == 14

    # 9/14 = 64.3% — still below the 70% threshold.
    for slot in slots[:9]:
        plan = client.patch(
            f"/api/v1/weekly-plan-activities/{slot['id']}",
            json={"completed": True},
            headers=headers,
        ).json()
    response = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions",
        headers=headers,
    )
    assert response.status_code == 400

    # 10/14 = 71.4% — now eligible without completing all 14.
    plan = client.patch(
        f"/api/v1/weekly-plan-activities/{slots[9]['id']}",
        json={"completed": True},
        headers=headers,
    ).json()
    response = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions",
        headers=headers,
    )
    assert response.status_code == 200
    context = response.json()
    assert context["completed_count"] == 10
    assert context["total_activities"] == 14


def test_questions_are_kb06_plan_specific_and_not_kb05(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers)
    plan = _create_plan(client, headers, child_id, complete=True)

    response = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions",
        headers=headers,
    )
    assert response.status_code == 200
    context = response.json()
    assert context["child_id"] == child_id
    assert context["weekly_plan_id"] == plan["id"]
    assert context["completed_count"] == context["total_activities"] == 14
    assert 5 <= len(context["questions"]) <= 8
    assert len(context["questions"]) != 20
    assert all(
        question["source_file"] == "KB06.json"
        for question in context["questions"]
    )
    assert all(
        question["activity_id"] in question["id"]
        for question in context["questions"]
    )
    assert all(question["weekly_goal"] for question in context["questions"])

    legacy = client.post(
        f"/api/v1/assessments/{plan['assessment_id']}/followup",
        headers=headers,
    )
    assert legacy.status_code == 404


def test_submit_rejects_incomplete_and_wrong_plan_answers(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers)
    plan = _create_plan(client, headers, child_id, complete=True)
    context = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions",
        headers=headers,
    ).json()

    incomplete = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/followup",
        json={"answers": _answers(context)[:-1]},
        headers=headers,
    )
    assert incomplete.status_code == 400

    invalid_answers = _answers(context)
    invalid_answers[0]["question_id"] = "wrong-plan-id"
    invalid = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/followup",
        json={"answers": invalid_answers},
        headers=headers,
    )
    assert invalid.status_code == 400


def test_followup_submission_is_idempotent_and_replaces_plan_once(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "parent@example.com")
    child_id = _create_child(client, headers)
    plan = _create_plan(client, headers, child_id, complete=True)
    context = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions",
        headers=headers,
    ).json()
    payload = {"answers": _answers(context)}

    first = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/followup",
        json=payload,
        headers=headers,
    )
    assert first.status_code == 201
    followup = first.json()
    assert followup["weekly_plan_id"] == plan["id"]
    assert followup["current_assessment_id"] is None
    assert followup["current_score_percent"] == 100

    replacement = client.get(
        f"/api/v1/children/{child_id}/weekly-plan", headers=headers
    ).json()
    assert replacement["id"] != plan["id"]
    assert replacement["assessment_id"] == plan["assessment_id"]
    assert replacement["completed_count"] == 0

    duplicate = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/followup",
        json=payload,
        headers=headers,
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == followup["id"]
    unchanged = client.get(
        f"/api/v1/children/{child_id}/weekly-plan", headers=headers
    ).json()
    assert unchanged["id"] == replacement["id"]

    old_prompt = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions",
        headers=headers,
    )
    assert old_prompt.status_code == 409

    detail = client.get(
        f"/api/v1/followups/{followup['id']}", headers=headers
    )
    assert detail.status_code == 200
    listing = client.get(
        f"/api/v1/children/{child_id}/followups", headers=headers
    )
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [followup["id"]]


def test_wrong_parent_and_wrong_child_plan_are_hidden(client: TestClient) -> None:
    headers_a = _auth_headers(client, "a@example.com")
    headers_b = _auth_headers(client, "b@example.com")
    child_a = _create_child(client, headers_a)
    child_b = _create_child(client, headers_b)
    plan_a = _create_plan(client, headers_a, child_a, complete=True)
    _create_plan(client, headers_b, child_b, complete=True)

    assert (
        client.get(
            f"/api/v1/weekly-plans/{plan_a['id']}/followup-questions",
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/v1/weekly-plans/{plan_a['id']}/followup",
            json={
                "answers": [
                    {"question_id": f"dummy-{index}", "response": "always"}
                    for index in range(5)
                ]
            },
            headers=headers_b,
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/v1/children/{child_a}/followups", headers=headers_b
        ).status_code
        == 404
    )
