"""Every recommendation the API returns must trace back to a real KB record
(CLAUDE_CODE_PROMPT.md: "Preserve traceability from every recommendation to
its source record... Never fabricate medical claims or references").
"""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.rag.schemas import Domain
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository


def _auth_headers(client: TestClient, email: str = "parent@example.com") -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Parent"},
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_assessment_report_and_plan_are_fully_traceable_to_the_kb(
    client: TestClient, kb_repository: KnowledgeBaseRepository
) -> None:
    # Age 2 specifically: its KB05 linked_milestone_id values are the only
    # ones that resolve cleanly against KB01 (see
    # docs/DECISIONS_AND_ASSUMPTIONS.md and test_scoring_service.py's
    # test_scoring_survives_unresolvable_kb01_milestone_links for the known
    # ages-3-5 gap), so this is the age that gives a clean, total check.
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

    # Every returned question must be a real KB05 row for this exact age.
    real_question_ids = {q.id for q in kb_repository.get_questions_for_age(2)}
    assert {q["id"] for q in questions} == real_question_ids
    for q in questions:
        kb_repository.get_milestone(q["linked_milestone_id"])  # raises if not real

    client.post(
        f"/api/v1/assessments/{assessment['id']}/answers",
        json={"answers": [{"question_id": q["id"], "response": "rarely"} for q in questions]},
        headers=headers,
    )
    result = client.post(
        f"/api/v1/assessments/{assessment['id']}/complete", headers=headers
    ).json()

    # Every domain result's decision-rule ID must resolve to a real KB03 row
    # whose recommendation text matches verbatim (not paraphrased/invented).
    for domain_result in result["domain_results"]:
        rule = kb_repository.get_decision_rule(
            2, Domain(domain_result["domain"]), domain_result["score_percent"]
        )
        assert rule.id == domain_result["decision_rule_id"]
        assert rule.ai_recommendation == domain_result["recommendation"]
        # Every suggested activity ID must be a real KB02 row.
        for activity_id in domain_result["suggested_activity_ids"]:
            kb_repository.get_activity(activity_id)

    report = client.post(
        f"/api/v1/assessments/{assessment['id']}/report", headers=headers
    ).json()
    for activity_id in report["recommended_activity_ids"]:
        kb_repository.get_activity(activity_id)
    # The summary narrative must be a verbatim KB04 template, not generated text.
    narrative_texts = {t.text for t in kb_repository.kb.narrative_templates}
    assert report["summary_text"] in narrative_texts

    plan = client.post(
        f"/api/v1/assessments/{assessment['id']}/weekly-plan", headers=headers
    ).json()
    for activity_slot in plan["activities"]:
        real_activity = kb_repository.get_activity(activity_slot["activity"]["id"])
        assert real_activity.name == activity_slot["activity"]["name"]
