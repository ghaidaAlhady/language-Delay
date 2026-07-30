from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.ai.protocols import (
    ProviderError,
    ProviderRequest,
    ProviderTimeoutError,
)
from app.ai.schemas import ActionTip, AssistanceContent
from app.api.deps import get_ai_provider
from app.core.constants import DISCLAIMER_AR
from app.main import app


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecret1",
            "display_name": "Private Parent",
        },
    )
    tokens = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "supersecret1"},
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _completed_assessment(
    client: TestClient,
    headers: dict[str, str],
    *,
    response_value: str = "never",
) -> tuple[str, str]:
    today = date.today()
    dob = date(today.year - 2, today.month, min(today.day, 28)).isoformat()
    child = client.post(
        "/api/v1/children",
        json={
            "name": "Layla Private",
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
        json={
            "answers": [
                {
                    "question_id": question["id"],
                    "response": response_value,
                }
                for question in questions
            ]
        },
        headers=headers,
    )
    complete = client.post(
        f"/api/v1/assessments/{assessment['id']}/complete", headers=headers
    )
    assert complete.status_code == 200
    return assessment["id"], child["id"]


def _full_journey(
    client: TestClient, headers: dict[str, str]
) -> tuple[str, str, str, str]:
    assessment_id, child_id = _completed_assessment(client, headers)
    plan = client.post(
        f"/api/v1/assessments/{assessment_id}/weekly-plan", headers=headers
    ).json()
    for slot in plan["activities"]:
        response = client.patch(
            f"/api/v1/weekly-plan-activities/{slot['id']}",
            json={"completed": True},
            headers=headers,
        )
        assert response.status_code == 200
    context = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions",
        headers=headers,
    ).json()
    followup = client.post(
        f"/api/v1/weekly-plans/{plan['id']}/followup",
        json={
            "answers": [
                {"question_id": question["id"], "response": "always"}
                for question in context["questions"]
            ]
        },
        headers=headers,
    ).json()
    return assessment_id, child_id, plan["id"], followup["id"]


class ValidProvider:
    name = "test-gemini"

    def __init__(self) -> None:
        self.requests: list[ProviderRequest] = []

    async def generate(self, request: ProviderRequest) -> str:
        self.requests.append(request)
        action_sources = [
            source
            for source in request.context.approved_sources
            if source.supports_action_tip
        ][:2]
        content = AssistanceContent(
            title="صياغة مساندة",
            summary="هذا ملخص مبسط للحقائق الحتمية المعروضة.",
            encouragement="استمروا في الممارسة المنزلية المنتظمة.",
            action_tips=[
                ActionTip(
                    text=f"جرّبوا نشاط «{source.title}» كما ورد في المصدر.",
                    source_id=source.source_id,
                )
                for source in action_sources
            ],
            disclaimer=DISCLAIMER_AR,
            source_ids=[
                source.source_id
                for source in request.context.approved_sources[:8]
            ],
        )
        return content.model_dump_json()

    async def aclose(self) -> None:
        return None


class FailureProvider:
    name = "failing-provider"

    def __init__(self, failure: str) -> None:
        self.failure = failure

    async def generate(self, request: ProviderRequest) -> str:
        if self.failure == "timeout":
            raise ProviderTimeoutError
        if self.failure == "provider_error":
            raise ProviderError("private provider detail")
        if self.failure == "malformed":
            return "{"

        source = request.context.approved_sources[0]
        content = AssistanceContent(
            title="صياغة",
            summary=(
                "هذا تشخيص مؤكد."
                if self.failure == "unsafe"
                else "صياغة موجزة."
            ),
            encouragement="استمروا في الممارسة.",
            disclaimer=DISCLAIMER_AR,
            source_ids=[
                "UNKNOWN"
                if self.failure == "ungrounded"
                else source.source_id
            ],
        )
        return content.model_dump_json()

    async def aclose(self) -> None:
        return None


def _use_provider(provider: object) -> None:
    app.dependency_overrides[get_ai_provider] = lambda: provider


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/assessments/unknown/ai-explanation",
        "/api/v1/weekly-plans/unknown/ai-summary",
        "/api/v1/followups/unknown/ai-summary",
    ],
)
def test_ai_endpoints_require_authentication(
    client: TestClient, path: str
) -> None:
    assert client.post(path).status_code == 401


def test_disabled_by_default_returns_useful_http_200_fallback(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "disabled@example.com")
    assessment_id, _child_id = _completed_assessment(client, headers)

    response = client.post(
        f"/api/v1/assessments/{assessment_id}/ai-explanation",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["generation_source"] == "deterministic_fallback"
    assert body["fallback_reason"] == "disabled"
    assert body["content"]["summary"]
    assert body["content"]["disclaimer"] == DISCLAIMER_AR
    assert response.headers["X-Request-ID"]


def test_all_three_resources_accept_valid_grounded_provider_output_without_pii(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "private-parent@example.com")
    assessment_id, child_id, plan_id, followup_id = _full_journey(
        client, headers
    )
    provider = ValidProvider()
    _use_provider(provider)

    paths = [
        f"/api/v1/assessments/{assessment_id}/ai-explanation",
        f"/api/v1/weekly-plans/{plan_id}/ai-summary",
        f"/api/v1/followups/{followup_id}/ai-summary",
    ]
    for path in paths:
        response = client.post(path, headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["generation_source"] == "gemini"
        assert body["fallback_reason"] is None
        assert body["prompt_version"] == "v1"
        assert body["content"]["disclaimer"] == DISCLAIMER_AR

    assert len(provider.requests) == 3
    forbidden_values = {
        "Layla Private",
        "private-parent@example.com",
        assessment_id,
        child_id,
        plan_id,
        followup_id,
    }
    for request in provider.requests:
        serialized = request.context.model_dump_json()
        for value in forbidden_values:
            assert value not in serialized
            assert value not in request.prompt
        assert "question_answers" not in serialized
        assert "notes" not in serialized


def test_incomplete_assessment_is_rejected_before_provider_call(
    client: TestClient,
) -> None:
    headers = _auth_headers(client, "incomplete@example.com")
    today = date.today()
    dob = date(today.year - 2, today.month, min(today.day, 28)).isoformat()
    child = client.post(
        "/api/v1/children",
        json={
            "name": "Child",
            "date_of_birth": dob,
            "gender": "female",
            "home_language": "ar",
        },
        headers=headers,
    ).json()
    assessment = client.post(
        f"/api/v1/children/{child['id']}/assessments", headers=headers
    ).json()
    provider = ValidProvider()
    _use_provider(provider)

    response = client.post(
        f"/api/v1/assessments/{assessment['id']}/ai-explanation",
        headers=headers,
    )
    assert response.status_code == 400
    assert provider.requests == []


def test_resource_ownership_is_masked_as_not_found_before_provider_call(
    client: TestClient,
) -> None:
    owner_headers = _auth_headers(client, "owner@example.com")
    other_headers = _auth_headers(client, "other@example.com")
    assessment_id, _child_id, plan_id, followup_id = _full_journey(
        client, owner_headers
    )
    provider = ValidProvider()
    _use_provider(provider)

    for path in [
        f"/api/v1/assessments/{assessment_id}/ai-explanation",
        f"/api/v1/weekly-plans/{plan_id}/ai-summary",
        f"/api/v1/followups/{followup_id}/ai-summary",
    ]:
        assert client.post(path, headers=other_headers).status_code == 404
    assert provider.requests == []


@pytest.mark.parametrize(
    ("failure", "expected_reason"),
    [
        ("timeout", "timeout"),
        ("provider_error", "provider_error"),
        ("malformed", "invalid_output"),
        ("unsafe", "unsafe_output"),
        ("ungrounded", "ungrounded_output"),
    ],
)
def test_provider_failures_return_safe_http_200_without_changing_assessment(
    client: TestClient, failure: str, expected_reason: str
) -> None:
    headers = _auth_headers(client, f"{failure}@example.com")
    assessment_id, _child_id = _completed_assessment(client, headers)
    before = client.get(
        f"/api/v1/assessments/{assessment_id}", headers=headers
    ).json()
    _use_provider(FailureProvider(failure))

    response = client.post(
        f"/api/v1/assessments/{assessment_id}/ai-explanation",
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["generation_source"] == "deterministic_fallback"
    assert body["fallback_reason"] == expected_reason
    assert "private provider detail" not in response.text
    after = client.get(
        f"/api/v1/assessments/{assessment_id}", headers=headers
    ).json()
    assert after["overall_severity"] == before["overall_severity"]
    assert after["overall_referral"] == before["overall_referral"]
    assert after["domain_results"] == before["domain_results"]


def test_ai_endpoint_is_rate_limited(client: TestClient) -> None:
    headers = _auth_headers(client, "rate-limit@example.com")
    assessment_id, _child_id = _completed_assessment(client, headers)
    path = f"/api/v1/assessments/{assessment_id}/ai-explanation"

    statuses = [
        client.post(path, headers=headers).status_code for _ in range(21)
    ]
    assert statuses[:20] == [200] * 20
    assert statuses[20] == 429

