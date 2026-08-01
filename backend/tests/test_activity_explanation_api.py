"""The "افهم أكثر" per-activity AI explanation endpoint."""
from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.ai.protocols import ProviderError, ProviderRequest, ProviderTimeoutError
from app.api.deps import get_ai_provider
from app.main import app


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "supersecret1", "display_name": "Parent"},
    )
    tokens = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "supersecret1"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _plan_with_slot(client: TestClient, headers: dict[str, str]) -> tuple[str, str]:
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
    plan = client.post(
        f"/api/v1/assessments/{assessment['id']}/weekly-plan", headers=headers
    ).json()
    return plan["activities"][0]["id"], plan["activities"][0]["activity"]["id"]


def _valid_payload(activity_id: str) -> dict:
    return {
        "activity_id": activity_id,
        "title_ar": "عنوان النشاط",
        "simple_explanation_ar": "شرح مبسط للنشاط.",
        "purpose_ar": "الهدف من النشاط.",
        "steps_ar": ["الخطوة الأولى", "الخطوة الثانية", "الخطوة الثالثة"],
        "example_dialogue": {
            "parent_text": "هيا نجرّب معًا.",
            "example_child_response": "قد يشارك الطفل بمحاولة بسيطة.",
            "supportive_parent_continuation": "أحسنت! لنكرر ذلك.",
        },
        "alternative_ar": "طريقة أسهل لتنفيذ النشاط نفسه.",
        "source_ids": [activity_id],
    }


class _ValidProvider:
    name = "test-gemini"

    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []

    async def generate(self, request: ProviderRequest) -> str:
        self.requests.append(request)
        activity_id = str(request.context.immutable_facts["activity_id"])
        return json.dumps(_valid_payload(activity_id), ensure_ascii=False)

    async def aclose(self) -> None:
        return None


class _BadOutputProvider:
    name = "bad-provider"

    def __init__(self, failure: str) -> None:
        self.failure = failure

    async def generate(self, request: ProviderRequest) -> str:
        activity_id = str(request.context.immutable_facts["activity_id"])
        if self.failure == "timeout":
            raise ProviderTimeoutError
        if self.failure == "provider_error":
            raise ProviderError("private detail")
        if self.failure == "malformed":
            return "{"
        if self.failure == "too_few_steps":
            payload = _valid_payload(activity_id)
            payload["steps_ar"] = ["خطوة واحدة فقط"]
            return json.dumps(payload, ensure_ascii=False)
        if self.failure == "too_many_steps":
            payload = _valid_payload(activity_id)
            payload["steps_ar"] = [f"خطوة {i}" for i in range(6)]
            return json.dumps(payload, ensure_ascii=False)
        if self.failure == "wrong_activity_id":
            payload = _valid_payload("A999")
            return json.dumps(payload, ensure_ascii=False)
        if self.failure == "unknown_source":
            payload = _valid_payload(activity_id)
            payload["source_ids"] = ["A999"]
            return json.dumps(payload, ensure_ascii=False)
        if self.failure == "forbidden_wording":
            payload = _valid_payload(activity_id)
            payload["simple_explanation_ar"] = "هذا تشخيص طبي مؤكد ويحتاج دواءً."
            return json.dumps(payload, ensure_ascii=False)
        if self.failure == "guarantee_wording":
            payload = _valid_payload(activity_id)
            payload["purpose_ar"] = "هذا النشاط مضمون وسيتحسن الطفل حتماً."
            return json.dumps(payload, ensure_ascii=False)
        return json.dumps(_valid_payload(activity_id), ensure_ascii=False)

    async def aclose(self) -> None:
        return None


def _use_provider(provider: object) -> None:
    app.dependency_overrides[get_ai_provider] = lambda: provider


@pytest.fixture(autouse=True)
def _clear_provider_override():
    yield
    app.dependency_overrides.pop(get_ai_provider, None)


def test_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/v1/weekly-plan-activities/unknown/ai-explanation")
    assert response.status_code == 401


def test_valid_grounded_explanation_with_steps_and_dialogue(client: TestClient) -> None:
    _use_provider(_ValidProvider())
    headers = _auth_headers(client, "e1@example.com")
    slot_id, activity_id = _plan_with_slot(client, headers)

    response = client.post(
        f"/api/v1/weekly-plan-activities/{slot_id}/ai-explanation", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generation_source"] == "gemini"
    assert body["content"]["activity_id"] == activity_id
    assert 3 <= len(body["content"]["steps_ar"]) <= 5
    assert body["content"]["example_dialogue"]["parent_text"]
    assert body["content"]["alternative_ar"]
    assert body["source_references"][0]["source_id"] == activity_id
    assert body["source_references"][0]["label_ar"]


def test_ownership_is_masked_as_not_found_before_provider_call(client: TestClient) -> None:
    provider = _ValidProvider()
    _use_provider(provider)
    owner_headers = _auth_headers(client, "owner@example.com")
    slot_id, _activity_id = _plan_with_slot(client, owner_headers)

    stranger_headers = _auth_headers(client, "stranger@example.com")
    response = client.post(
        f"/api/v1/weekly-plan-activities/{slot_id}/ai-explanation",
        headers=stranger_headers,
    )
    assert response.status_code == 404
    assert provider.requests == []


@pytest.mark.parametrize(
    ("failure", "expected_reason"),
    [
        ("timeout", "timeout"),
        ("provider_error", "provider_error"),
        ("malformed", "invalid_output"),
        ("too_few_steps", "invalid_output"),
        ("too_many_steps", "invalid_output"),
        ("wrong_activity_id", "ungrounded_output"),
        ("unknown_source", "ungrounded_output"),
        ("forbidden_wording", "unsafe_output"),
        ("guarantee_wording", "unsafe_output"),
    ],
)
def test_every_failure_mode_falls_back_to_kb02_explanation(
    client: TestClient, failure: str, expected_reason: str
) -> None:
    _use_provider(_BadOutputProvider(failure))
    headers = _auth_headers(client, f"e2-{failure}@example.com")
    slot_id, activity_id = _plan_with_slot(client, headers)

    response = client.post(
        f"/api/v1/weekly-plan-activities/{slot_id}/ai-explanation", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generation_source"] == "deterministic_fallback"
    assert body["fallback_reason"] == expected_reason
    assert body["content"]["activity_id"] == activity_id
    assert 3 <= len(body["content"]["steps_ar"]) <= 5


def test_provider_context_contains_no_session_or_child_data(client: TestClient) -> None:
    provider = _ValidProvider()
    _use_provider(provider)
    headers = _auth_headers(client, "e3@example.com")
    slot_id, _activity_id = _plan_with_slot(client, headers)

    client.post(f"/api/v1/weekly-plan-activities/{slot_id}/ai-explanation", headers=headers)

    assert len(provider.requests) == 1
    serialized = provider.requests[0].context.model_dump_json()
    assert "Layla" not in serialized
    assert "e3@example.com" not in serialized
    assert headers["Authorization"] not in serialized
