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


def _completed_assessment_id(client: TestClient, headers: dict[str, str], age: int = 2) -> str:
    today = date.today()
    dob = date(today.year - age, today.month, min(today.day, 28)).isoformat()
    child = client.post(
        "/api/v1/children",
        json={
            "name": "Layla",
            "date_of_birth": dob,
            "gender": "female",
            "home_language": "ar",
        },
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
        json={"answers": [{"question_id": q["id"], "response": "always"} for q in questions]},
        headers=headers,
    )
    client.post(f"/api/v1/assessments/{assessment['id']}/complete", headers=headers)
    return assessment["id"], child["id"]


def test_generate_report_requires_completed_assessment(client: TestClient) -> None:
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

    response = client.post(f"/api/v1/assessments/{assessment['id']}/report", headers=headers)
    assert response.status_code == 400


def test_generate_and_get_report(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    assessment_id, child_id = _completed_assessment_id(client, headers)

    generate = client.post(f"/api/v1/assessments/{assessment_id}/report", headers=headers)
    assert generate.status_code == 201
    body = generate.json()
    assert body["report_number"].startswith("REP-")
    assert body["disclaimer"]
    assert body["next_reassessment"] == "إعادة التقييم بعد أسبوع وتحديث الخطة"

    detail = client.get(f"/api/v1/reports/{body['id']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["id"] == body["id"]

    listing = client.get(f"/api/v1/children/{child_id}/reports", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_download_report_pdf(client: TestClient) -> None:
    headers = _auth_headers(client, "parent@example.com")
    assessment_id, _child_id = _completed_assessment_id(client, headers)
    report = client.post(
        f"/api/v1/assessments/{assessment_id}/report", headers=headers
    ).json()

    response = client.get(f"/api/v1/reports/{report['id']}/pdf", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")


def test_report_ownership_isolation(client: TestClient) -> None:
    headers_a = _auth_headers(client, "a@example.com")
    headers_b = _auth_headers(client, "b@example.com")
    assessment_id, child_id = _completed_assessment_id(client, headers_a)
    report = client.post(
        f"/api/v1/assessments/{assessment_id}/report", headers=headers_a
    ).json()

    assert (
        client.get(f"/api/v1/reports/{report['id']}", headers=headers_b).status_code == 404
    )
    assert (
        client.get(f"/api/v1/reports/{report['id']}/pdf", headers=headers_b).status_code == 404
    )
    assert (
        client.get(f"/api/v1/children/{child_id}/reports", headers=headers_b).status_code == 404
    )
    assert (
        client.post(
            f"/api/v1/assessments/{assessment_id}/report", headers=headers_b
        ).status_code
        == 404
    )
