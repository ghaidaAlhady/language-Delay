"""The application is a supportive screening tool, never a diagnostic one
(CLAUDE.md Core Principle). These tests guard that guarantee at the API
boundary: every report must carry the disclaimer, and no response may use
diagnostic language ("تشخيص") outside of the disclaimer's own denial of it.
"""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.core.constants import DISCLAIMER_AR
from app.rag.schemas import ReportStatus
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository

DIAGNOSTIC_TERM = "تشخيص"


def _auth_headers(client: TestClient, email: str = "parent@example.com") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Parent"},
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _completed_assessment_report(client: TestClient, headers: dict[str, str], response: str):
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
    return client.post(f"/api/v1/assessments/{assessment['id']}/report", headers=headers).json()


def test_report_disclaimer_matches_the_approved_core_principle_text(
    client: TestClient,
) -> None:
    headers = _auth_headers(client)
    report = _completed_assessment_report(client, headers, "always")
    assert report["disclaimer"] == DISCLAIMER_AR


def test_report_never_uses_diagnostic_language_outside_the_disclaimer(
    client: TestClient,
) -> None:
    headers = _auth_headers(client)
    # Worst-case severity is the scenario most tempting to phrase as a
    # diagnosis, so exercise it specifically.
    report = _completed_assessment_report(client, headers, "never")

    disclaimer = report.pop("disclaimer")
    assert DIAGNOSTIC_TERM in disclaimer  # the disclaimer explicitly denies diagnosing

    rest_of_report_text = " ".join(
        str(value) for value in report.values() if isinstance(value, str)
    )
    rest_of_report_text += " ".join(
        str(v)
        for summary in report.get("domain_summaries", [])
        for v in summary.values()
        if isinstance(v, str)
    )
    assert DIAGNOSTIC_TERM not in rest_of_report_text


def test_all_five_narrative_templates_avoid_diagnostic_language(
    kb_repository: KnowledgeBaseRepository,
) -> None:
    for status in ReportStatus:
        template = kb_repository.get_narrative_template(status)
        assert DIAGNOSTIC_TERM not in template.text
