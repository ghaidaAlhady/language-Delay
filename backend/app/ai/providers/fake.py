"""Deterministic fake used only by the isolated E2E backend."""
from __future__ import annotations

import json

from app.ai.protocols import ProviderRequest, ProviderTimeoutError
from app.ai.schemas import (
    ActionTip,
    ActivityExplanationContent,
    AssistanceContent,
    AssistanceOperation,
    ExampleDialogue,
)
from app.core.constants import DISCLAIMER_AR


class FakeAIProvider:
    """Return valid grounded content; normal assessments exercise fallback."""

    name = "fake-gemini"

    async def generate(self, request: ProviderRequest) -> str:
        facts = request.context.immutable_facts

        if request.operation is AssistanceOperation.FOLLOWUP_QUESTION_VARIATION:
            return self._generate_followup_questions(request)
        if request.operation is AssistanceOperation.ACTIVITY_EXPLANATION:
            return self._generate_activity_explanation(request)

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

    def _generate_followup_questions(self, request: ProviderRequest) -> str:
        candidates = request.context.approved_sources
        selected = candidates[: min(8, max(5, len(candidates)))]
        questions = [
            {
                "id": source.source_id,
                "wording_ar": f"سؤال معاد صياغته: {source.excerpt}",
            }
            for source in selected
        ]
        return json.dumps({"questions": questions}, ensure_ascii=False)

    def _generate_activity_explanation(self, request: ProviderRequest) -> str:
        activity_id = str(request.context.immutable_facts.get("activity_id", ""))
        activity_name = (
            request.context.approved_sources[0].title
            if request.context.approved_sources
            else activity_id
        )
        content = ActivityExplanationContent(
            activity_id=activity_id,
            title_ar=activity_name,
            simple_explanation_ar=f"هذا شرح مبسّط بالذكاء الاصطناعي لنشاط «{activity_name}».",
            purpose_ar="يهدف النشاط إلى دعم المهارة المستهدفة بطريقة تدريجية.",
            steps_ar=[
                f"جهّزوا الأدوات اللازمة لنشاط «{activity_name}».",
                "ابدأوا بخطوة بسيطة وامنحوا الطفل وقتًا للمحاولة.",
                "كرروا النشاط بانتظام مع تشجيع هادئ.",
            ],
            example_dialogue=ExampleDialogue(
                parent_text=f"هيا نجرّب «{activity_name}» معًا.",
                example_child_response="قد يشارك الطفل بمحاولة بسيطة — هذا مثال محتمل فقط.",
                supportive_parent_continuation="أحسنت! لنكرر ذلك مرة أخرى بهدوء.",
            ),
            alternative_ar=(
                f"إذا لم يستجب الطفل، بسّطوا «{activity_name}» بتقليل عدد "
                "الخيارات أو المدة، مع الحفاظ على هدف النشاط نفسه."
            ),
            source_ids=[activity_id] if activity_id else [],
        )
        return content.model_dump_json()

    async def aclose(self) -> None:
        return None

