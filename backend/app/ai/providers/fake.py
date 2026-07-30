"""Deterministic fake used only by the isolated E2E backend."""
from __future__ import annotations

from app.ai.protocols import ProviderRequest, ProviderTimeoutError
from app.ai.schemas import (
    ActionTip,
    AssistanceContent,
    AssistanceOperation,
)
from app.core.constants import DISCLAIMER_AR


class FakeAIProvider:
    """Return valid grounded content; normal assessments exercise fallback."""

    name = "fake-gemini"

    async def generate(self, request: ProviderRequest) -> str:
        facts = request.context.immutable_facts
        if (
            request.operation is AssistanceOperation.ASSESSMENT_EXPLANATION
            and facts.get("overall_severity") == "طبيعي"
        ):
            raise ProviderTimeoutError

        action_sources = [
            source
            for source in request.context.approved_sources
            if source.supports_action_tip
        ][:2]
        tips = [
            ActionTip(
                text=f"جرّبوا نشاط «{source.title}» وفق الإرشادات المعتمدة.",
                source_id=source.source_id,
            )
            for source in action_sources
        ]

        if request.operation is AssistanceOperation.ASSESSMENT_EXPLANATION:
            title = "شرح مبسط للنتيجة"
            summary = (
                "تعرض هذه الصياغة النتيجة الحتمية كما هي: "
                f"{facts.get('overall_severity')}."
            )
        elif request.operation is AssistanceOperation.WEEKLY_PLAN_SUMMARY:
            title = "ملخص الخطة الأسبوعية"
            summary = (
                f"تضم الخطة {facts.get('total_activities')} نشاطاً، "
                f"واكتمل منها {facts.get('completed_count')}."
            )
        else:
            title = "ملخص تقدم الأسبوع"
            summary = (
                "تعرض المتابعة نسبة التقدم الحتمية المسجلة: "
                f"{facts.get('progress_percent')}%."
            )

        content = AssistanceContent(
            title=title,
            summary=summary,
            encouragement="الاستمرار بخطوات قصيرة ومنتظمة يدعم التعلم المنزلي.",
            action_tips=tips,
            disclaimer=DISCLAIMER_AR,
            source_ids=[
                source.source_id
                for source in request.context.approved_sources[:8]
            ],
        )
        return content.model_dump_json()

    async def aclose(self) -> None:
        return None

