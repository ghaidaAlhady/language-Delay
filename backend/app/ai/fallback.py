"""Useful deterministic Arabic wording for every provider failure path."""
from __future__ import annotations

from app.ai.schemas import (
    ActionTip,
    AssistanceContent,
    AssistanceContext,
    AssistanceOperation,
    GroundingRecord,
)
from app.core.constants import DISCLAIMER_AR


def _text_fact(context: AssistanceContext, key: str, default: str) -> str:
    value = context.immutable_facts.get(key)
    return value if isinstance(value, str) else default


def _number_fact(
    context: AssistanceContext, key: str, default: int | float = 0
) -> int | float:
    value = context.immutable_facts.get(key)
    return value if isinstance(value, int | float) else default


def _list_fact(context: AssistanceContext, key: str) -> list[str]:
    value = context.immutable_facts.get(key)
    return value if isinstance(value, list) else []


def _action_sources(context: AssistanceContext) -> list[GroundingRecord]:
    return [
        source
        for source in context.approved_sources
        if source.supports_action_tip
    ][:3]


def _action_tips(context: AssistanceContext) -> list[ActionTip]:
    return [
        ActionTip(
            text=(
                f"ابدؤوا بنشاط «{source.title}» كما ورد في إرشادات النشاط "
                "المعتمد، مع ممارسة قصيرة ومتكررة."
            ),
            source_id=source.source_id,
        )
        for source in _action_sources(context)
    ]


def _source_ids(
    context: AssistanceContext, tips: list[ActionTip]
) -> list[str]:
    ids = [tip.source_id for tip in tips]
    for source in context.approved_sources:
        if source.source_id not in ids:
            ids.append(source.source_id)
        if len(ids) >= 8:
            break
    return ids


def build_deterministic_fallback(
    context: AssistanceContext,
) -> AssistanceContent:
    tips = _action_tips(context)

    if context.operation is AssistanceOperation.ASSESSMENT_EXPLANATION:
        severity = _text_fact(
            context, "overall_severity", "النتيجة الحتمية المسجلة"
        )
        strengths = _list_fact(context, "strengths")
        support_needs = _list_fact(context, "support_needs")
        strengths_text = (
            f" ومن نقاط القوة المسجلة: {'، '.join(strengths[:2])}."
            if strengths
            else ""
        )
        support_text = (
            f" وتحتاج المهارات الآتية إلى دعم: {'، '.join(support_needs[:2])}."
            if support_needs
            else ""
        )
        title = "شرح مبسط للنتيجة"
        summary = (
            f"النتيجة الحتمية للتقييم هي «{severity}»."
            f"{strengths_text}{support_text}"
        )
        encouragement = (
            "الممارسة المنزلية الهادئة والمتكررة تساعد على دعم المهارات خطوة بخطوة."
        )
    elif context.operation is AssistanceOperation.WEEKLY_PLAN_SUMMARY:
        total = _number_fact(context, "total_activities")
        completed = _number_fact(context, "completed_count")
        adherence = _number_fact(context, "adherence_percent")
        title = "ملخص الخطة الأسبوعية"
        summary = (
            f"تتضمن الخطة الحتمية {total} نشاطاً، واكتمل منها {completed}. "
            f"نسبة الالتزام المسجلة هي {adherence}%."
        )
        encouragement = (
            "اختاروا وقتاً مناسباً للأسرة، ووزعوا الأنشطة على أيام الأسبوع دون ضغط."
        )
    else:
        progress = _number_fact(context, "progress_percent")
        comment = _text_fact(
            context,
            "deterministic_comment",
            "تُعرض نتيجة المتابعة الحتمية كما سجلها النظام.",
        )
        next_goal = _text_fact(
            context, "next_goal", "الاستمرار في الهدف الأسبوعي الحالي."
        )
        title = "ملخص تقدم الأسبوع"
        summary = (
            f"نسبة التقدم الحتمية المسجلة هي {progress}%. {comment} "
            f"{next_goal}"
        )
        encouragement = (
            "استمروا في الممارسة المنتظمة، وراقبوا السلوك المستهدف بهدوء."
        )

    return AssistanceContent(
        title=title,
        summary=summary,
        encouragement=encouragement,
        action_tips=tips,
        disclaimer=DISCLAIMER_AR,
        source_ids=_source_ids(context, tips),
    )
