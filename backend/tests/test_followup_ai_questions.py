"""AI-varied weekly follow-up question wording — selection/scoring stays
deterministic; only wording (and which 5-8 of the deterministic candidates
to keep) may come from the provider.
"""
from __future__ import annotations

import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.ai.followup_questions import clear_cached_questions
from app.ai.protocols import ProviderError, ProviderRequest, ProviderTimeoutError
from app.ai.providers.disabled import DisabledAIProvider
from app.ai.schemas import FallbackReason
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


def _plan_at_70_percent(client: TestClient, headers: dict[str, str]) -> dict:
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
        json={
            "answers": [
                {"question_id": q["id"], "response": "never"} for q in questions
            ]
        },
        headers=headers,
    )
    client.post(f"/api/v1/assessments/{assessment['id']}/complete", headers=headers)
    plan = client.post(
        f"/api/v1/assessments/{assessment['id']}/weekly-plan", headers=headers
    ).json()
    slots = plan["activities"]
    assert len(slots) == 14
    for slot in slots[:10]:  # 10/14 = 71.4% >= 70%
        plan = client.patch(
            f"/api/v1/weekly-plan-activities/{slot['id']}",
            json={"completed": True},
            headers=headers,
        ).json()
    return plan


class _SelectingProvider:
    """Returns a valid subset with reworded text — the happy path."""

    name = "test-gemini"

    def __init__(self, *, keep: int | None = None) -> None:
        self.keep = keep
        self.requests: list[ProviderRequest] = []

    async def generate(self, request: ProviderRequest) -> str:
        self.requests.append(request)
        candidates = request.context.approved_sources
        keep = self.keep if self.keep is not None else len(candidates)
        selected = candidates[:keep]
        return json.dumps(
            {
                "questions": [
                    {
                        "id": source.source_id,
                        "wording_ar": f"صياغة معاد كتابتها رقم {index}: {source.excerpt}",
                    }
                    for index, source in enumerate(selected)
                ]
            },
            ensure_ascii=False,
        )

    async def aclose(self) -> None:
        return None


class _BadOutputProvider:
    name = "bad-provider"

    def __init__(self, failure: str) -> None:
        self.failure = failure

    async def generate(self, request: ProviderRequest) -> str:
        if self.failure == "timeout":
            raise ProviderTimeoutError
        if self.failure == "provider_error":
            raise ProviderError("private detail")
        if self.failure == "malformed":
            return "{"
        if self.failure == "too_few":
            return json.dumps({"questions": [{"id": "x", "wording_ar": "سؤال"}]})
        if self.failure == "too_many":
            return json.dumps(
                {"questions": [{"id": f"x{i}", "wording_ar": f"سؤال {i}"} for i in range(9)]}
            )

        candidates = request.context.approved_sources
        if self.failure == "unknown_id":
            questions = [{"id": "UNKNOWN-ID", "wording_ar": "سؤال غير معروف"}] + [
                {"id": s.source_id, "wording_ar": f"سؤال {i}"}
                for i, s in enumerate(candidates[:4])
            ]
        elif self.failure == "duplicate_wording":
            same_text = "هل يفعل الطفل هذا السلوك بانتظام؟"
            questions = [
                {"id": s.source_id, "wording_ar": same_text} for s in candidates[:5]
            ]
        elif self.failure == "forbidden_wording":
            questions = [
                {"id": s.source_id, "wording_ar": "هل تم تشخيص الطفل بمرض؟"}
                for s in candidates[:5]
            ]
        elif self.failure == "guarantee_wording":
            questions = [
                {"id": s.source_id, "wording_ar": "سيتحسن الطفل حتماً بعد هذا النشاط."}
                for s in candidates[:5]
            ]
        else:
            questions = [{"id": s.source_id, "wording_ar": "سؤال"} for s in candidates[:5]]
        return json.dumps({"questions": questions}, ensure_ascii=False)

    async def aclose(self) -> None:
        return None


def _use_provider(provider: object) -> None:
    app.dependency_overrides[get_ai_provider] = lambda: provider


@pytest.fixture(autouse=True)
def _clear_provider_override():
    yield
    app.dependency_overrides.pop(get_ai_provider, None)


def test_valid_provider_output_is_used_and_source_ids_are_grounded(
    client: TestClient,
) -> None:
    _use_provider(_SelectingProvider())
    headers = _auth_headers(client, "q1@example.com")
    plan = _plan_at_70_percent(client, headers)

    response = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generation_source"] == "gemini"
    assert 5 <= len(body["questions"]) <= 8
    for question in body["questions"]:
        assert question["question"].startswith("صياغة معاد كتابتها رقم")
        assert question["linked_activity_ids"] == [question["activity_id"]]
        assert question["source_question_id"] in question["source_ids"]
        assert question["prompt_version"] == "v2"


def test_provider_may_keep_only_5_of_the_deterministic_candidates(
    client: TestClient,
) -> None:
    _use_provider(_SelectingProvider(keep=5))
    headers = _auth_headers(client, "q2@example.com")
    plan = _plan_at_70_percent(client, headers)

    response = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions", headers=headers
    )
    assert response.status_code == 200
    assert len(response.json()["questions"]) == 5


@pytest.mark.parametrize(
    ("failure", "expected_reason"),
    [
        ("timeout", "timeout"),
        ("provider_error", "provider_error"),
        ("malformed", "invalid_output"),
        ("too_few", "invalid_output"),
        ("too_many", "invalid_output"),
        ("unknown_id", "ungrounded_output"),
        ("duplicate_wording", "unsafe_output"),
        ("forbidden_wording", "unsafe_output"),
        ("guarantee_wording", "unsafe_output"),
    ],
)
def test_every_failure_mode_falls_back_to_deterministic_wording(
    client: TestClient, failure: str, expected_reason: str
) -> None:
    _use_provider(_BadOutputProvider(failure))
    headers = _auth_headers(client, f"q3-{failure}@example.com")
    plan = _plan_at_70_percent(client, headers)

    response = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["generation_source"] == "deterministic_fallback"
    assert body["fallback_reason"] == expected_reason
    assert 5 <= len(body["questions"]) <= 8
    # The fallback text is exactly the original KB06 wording — never invented.
    for question in body["questions"]:
        assert "صياغة" not in question["question"]


def test_frozen_question_set_is_identical_across_repeat_calls(
    client: TestClient,
) -> None:
    provider = _SelectingProvider()
    _use_provider(provider)
    headers = _auth_headers(client, "q4@example.com")
    plan = _plan_at_70_percent(client, headers)

    first = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions", headers=headers
    ).json()
    refreshed_plan = client.get(
        f"/api/v1/children/{plan['child_id']}/weekly-plan", headers=headers
    ).json()
    assert refreshed_plan["reassessment_started"] is True
    # Simulate a process restart: clear the process-local optimization and
    # replace the provider. The database-frozen set must still win.
    clear_cached_questions(plan["id"])
    replacement_provider = _SelectingProvider()
    _use_provider(replacement_provider)
    second = client.get(
        f"/api/v1/weekly-plans/{plan['id']}/followup-questions", headers=headers
    ).json()

    assert replacement_provider.requests == []
    assert [q["id"] for q in first["questions"]] == [q["id"] for q in second["questions"]]
    assert [q["question"] for q in first["questions"]] == [
        q["question"] for q in second["questions"]
    ]
    # The provider was called exactly once — resume, don't regenerate.
    assert len(provider.requests) == 1


def test_submitting_answers_against_ai_worded_questions_scores_identically_to_deterministic(
    client: TestClient,
) -> None:
    """Same answers, same KB06 ids -> same score, regardless of wording."""
    headers_ai = _auth_headers(client, "q5-ai@example.com")
    _use_provider(_SelectingProvider())
    plan_ai = _plan_at_70_percent(client, headers_ai)
    context_ai = client.get(
        f"/api/v1/weekly-plans/{plan_ai['id']}/followup-questions", headers=headers_ai
    ).json()
    followup_ai = client.post(
        f"/api/v1/weekly-plans/{plan_ai['id']}/followup",
        json={
            "answers": [
                {"question_id": q["id"], "response": "always"}
                for q in context_ai["questions"]
            ]
        },
        headers=headers_ai,
    )
    assert followup_ai.status_code == 201

    # Explicitly force a known-safe disabled provider for the deterministic
    # half — popping the override would fall through to whatever the real
    # app.state.ai_provider resolves to from ambient local settings, which
    # must never influence a routine test's outcome.
    _use_provider(DisabledAIProvider(FallbackReason.DISABLED))
    headers_det = _auth_headers(client, "q5-det@example.com")
    plan_det = _plan_at_70_percent(client, headers_det)
    context_det = client.get(
        f"/api/v1/weekly-plans/{plan_det['id']}/followup-questions", headers=headers_det
    ).json()
    followup_det = client.post(
        f"/api/v1/weekly-plans/{plan_det['id']}/followup",
        json={
            "answers": [
                {"question_id": q["id"], "response": "always"}
                for q in context_det["questions"]
            ]
        },
        headers=headers_det,
    )
    assert followup_det.status_code == 201
    assert (
        followup_ai.json()["current_score_percent"]
        == followup_det.json()["current_score_percent"]
        == 100.0
    )


def test_provider_context_contains_no_pii(client: TestClient) -> None:
    provider = _SelectingProvider()
    _use_provider(provider)
    headers = _auth_headers(client, "q6@example.com")
    plan = _plan_at_70_percent(client, headers)

    client.get(f"/api/v1/weekly-plans/{plan['id']}/followup-questions", headers=headers)

    assert len(provider.requests) == 1
    context = provider.requests[0].context
    serialized = context.model_dump_json()
    assert "Layla" not in serialized
    assert "q6@example.com" not in serialized
    assert plan["child_id"] not in serialized
    assert headers["Authorization"] not in serialized
