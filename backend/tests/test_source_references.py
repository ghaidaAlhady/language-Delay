"""Human-readable source-reference labels (Milestone 3 §4).

Labels are resolved only from the approved `GroundingRecord`s the backend
already assembled — never from provider output.
"""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.ai.schemas import GroundingRecord
from app.ai.source_labels import build_source_references


def test_known_source_resolves_to_its_approved_title_and_category() -> None:
    sources = [
        GroundingRecord(
            source_id="A001",
            source_type="KB02_activity",
            title="أكمل الجملة",
            excerpt="نشاط لدعم اللغة التعبيرية.",
            supports_action_tip=True,
        )
    ]
    references = build_source_references(["A001"], sources)
    assert [reference.model_dump() for reference in references] == [
        {"source_id": "A001", "label_ar": "أكمل الجملة", "category": "نشاط معتمد"}
    ]


def test_unknown_source_id_gets_a_safe_neutral_label() -> None:
    references = build_source_references(["UNKNOWN-1"], approved_sources=[])
    assert len(references) == 1
    assert references[0].source_id == "UNKNOWN-1"
    assert references[0].label_ar == "مصدر معتمد"


def test_unrecognized_source_type_falls_back_to_neutral_category() -> None:
    sources = [
        GroundingRecord(
            source_id="X1",
            source_type="some_future_kb_type",
            title="عنوان",
            excerpt="نص.",
        )
    ]
    references = build_source_references(["X1"], sources)
    assert references[0].category == "مصدر معتمد"


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Parent"},
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_ai_summary_endpoint_response_includes_resolved_source_references(
    client: TestClient,
) -> None:
    """Disabled-by-default fallback still populates source_references, and
    `source_ids` is preserved unchanged for backward compatibility."""
    headers = _auth_headers(client, "src1@example.com")
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

    response = client.post(
        f"/api/v1/assessments/{assessment['id']}/ai-explanation", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["content"]["source_ids"]  # unchanged, backward-compatible
    assert len(body["source_references"]) == len(body["content"]["source_ids"])
    for reference, source_id in zip(
        body["source_references"], body["content"]["source_ids"], strict=True
    ):
        assert reference["source_id"] == source_id
        assert reference["label_ar"]
        assert reference["category"]
