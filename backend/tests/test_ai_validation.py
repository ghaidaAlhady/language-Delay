from __future__ import annotations

import json

import pytest

from app.ai.fallback import build_deterministic_fallback
from app.ai.providers import build_ai_provider
from app.ai.providers.disabled import DisabledAIProvider
from app.ai.providers.fake import FakeAIProvider
from app.ai.schemas import (
    ActionTip,
    AssistanceContent,
    AssistanceContext,
    AssistanceOperation,
    GroundingRecord,
)
from app.ai.validators import (
    InvalidOutputError,
    UngroundedOutputError,
    UnsafeOutputError,
    parse_and_validate,
)
from app.core.config import Settings
from app.core.constants import DISCLAIMER_AR
from app.rag.schemas import ReferralGuidance, Severity


@pytest.fixture
def ai_context() -> AssistanceContext:
    return AssistanceContext(
        operation=AssistanceOperation.ASSESSMENT_EXPLANATION,
        age_band="2 سنوات",
        immutable_facts={
            "overall_severity": Severity.MILD_DELAY.value,
            "overall_referral": ReferralGuidance.NO.value,
            "progress_percent": 25.0,
        },
        approved_sources=[
            GroundingRecord(
                source_id="R001",
                source_type="KB03_decision_rule",
                title="اللغة الاستقبالية",
                excerpt="توصية حتمية معتمدة.",
            ),
            GroundingRecord(
                source_id="A001",
                source_type="KB02_activity",
                title="لعبة الصور",
                excerpt="استخدموا الصور في ممارسة قصيرة.",
                supports_action_tip=True,
            ),
        ],
    )


@pytest.fixture
def valid_content() -> AssistanceContent:
    return AssistanceContent(
        title="شرح مبسط للنتيجة",
        summary=f"النتيجة الحتمية هي {Severity.MILD_DELAY.value} ونسبة التقدم 25%.",
        encouragement="يمكن دعم المهارات بالممارسة المنزلية المنتظمة.",
        action_tips=[
            ActionTip(
                text="جرّبوا نشاط «لعبة الصور» وفق الإرشادات المعتمدة.",
                source_id="A001",
            )
        ],
        disclaimer=DISCLAIMER_AR,
        source_ids=["R001", "A001"],
    )


def test_accepts_valid_grounded_output(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    result = parse_and_validate(valid_content.model_dump_json(), ai_context)
    assert result == valid_content


def test_rejects_malformed_json(ai_context: AssistanceContext) -> None:
    with pytest.raises(InvalidOutputError):
        parse_and_validate("{", ai_context)


def test_rejects_extra_output_field(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    payload = valid_content.model_dump(mode="json")
    payload["diagnosis"] = "unexpected"
    with pytest.raises(InvalidOutputError):
        parse_and_validate(json.dumps(payload), ai_context)


def test_rejects_changed_disclaimer(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.disclaimer = "تنبيه مختلف"
    with pytest.raises(UnsafeOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


@pytest.mark.parametrize(
    "unsafe_text",
    [
        "هذا تشخيص مؤكد.",
        "يحتاج الطفل إلى دواء.",
        "هذه خطة علاج مناسبة.",
        "See https://example.com",
        "<strong>نص</strong>",
        "```json",
    ],
)
def test_rejects_unsafe_terms_urls_and_markup(
    ai_context: AssistanceContext,
    valid_content: AssistanceContent,
    unsafe_text: str,
) -> None:
    valid_content.summary = unsafe_text
    with pytest.raises(UnsafeOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_unknown_source_id(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.source_ids.append("UNKNOWN")
    with pytest.raises(UngroundedOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_duplicate_source_ids(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.source_ids.append("A001")
    with pytest.raises(UngroundedOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_tip_without_action_source(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.action_tips[0].source_id = "R001"
    with pytest.raises(UngroundedOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_tip_without_exact_activity_name(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.action_tips[0].text = "جرّبوا نشاطاً آخر."
    with pytest.raises(UngroundedOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_unknown_activity_mentioned_in_body(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.summary += " استخدموا A999."
    with pytest.raises(UngroundedOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_contradictory_severity(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.summary = f"النتيجة {Severity.NOTABLE_DELAY.value}."
    with pytest.raises(UnsafeOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_contradictory_referral(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.summary = "يجب الإحالة إلى أخصائي."
    with pytest.raises(UnsafeOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_contradictory_progress(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.summary = "يوجد تقدم واضح."
    with pytest.raises(UnsafeOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_rejects_invented_percentage(
    ai_context: AssistanceContext, valid_content: AssistanceContent
) -> None:
    valid_content.summary = "النسبة 88%."
    with pytest.raises(UnsafeOutputError):
        parse_and_validate(valid_content.model_dump_json(), ai_context)


def test_deterministic_fallback_is_grounded_and_has_exact_disclaimer(
    ai_context: AssistanceContext,
) -> None:
    content = build_deterministic_fallback(ai_context)
    assert content.disclaimer == DISCLAIMER_AR
    assert content.action_tips[0].source_id == "A001"
    assert "لعبة الصور" in content.action_tips[0].text
    assert set(content.source_ids) <= {"R001", "A001"}


def test_provider_is_disabled_by_default() -> None:
    settings = Settings(secret_key="test", _env_file=None)
    provider = build_ai_provider(settings)
    assert isinstance(provider, DisabledAIProvider)


def test_incomplete_gemini_configuration_uses_disabled_provider() -> None:
    settings = Settings(
        secret_key="test",
        gemini_enabled=True,
        gemini_api_key="",
        gemini_model="",
        _env_file=None,
    )
    provider = build_ai_provider(settings)
    assert isinstance(provider, DisabledAIProvider)


def test_fake_provider_is_available_only_in_e2e() -> None:
    production = Settings(
        secret_key="test",
        app_env="production",
        ai_test_provider="fake",
        _env_file=None,
    )
    e2e = Settings(
        secret_key="test",
        app_env="e2e",
        ai_test_provider="fake",
        _env_file=None,
    )
    assert isinstance(build_ai_provider(production), DisabledAIProvider)
    assert isinstance(build_ai_provider(e2e), FakeAIProvider)
