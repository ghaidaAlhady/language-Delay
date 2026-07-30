"""Ownership-scoped, privacy-minimized context construction."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import (
    AssistanceContext,
    AssistanceOperation,
    GroundingRecord,
)
from app.core.errors import BadRequestError
from app.repositories import assessment_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AssessmentStatus
from app.services.assessment_service import AssessmentService
from app.services.followup_service import FollowupService
from app.services.weekly_plan_service import WeeklyPlanService


def _age_band(age: int) -> str:
    return f"{age} سنوات"


def _activity_source(
    kb: KnowledgeBaseRepository, activity_id: str
) -> GroundingRecord:
    activity = kb.get_activity(activity_id)
    excerpt = (
        f"الهدف: {activity.goal}. الإرشادات: {activity.parent_instructions}. "
        f"المدة: {activity.duration}. التكرار: {activity.frequency}."
    )
    return GroundingRecord(
        source_id=activity.id,
        source_type="KB02_activity",
        title=activity.name,
        excerpt=excerpt,
        supports_action_tip=True,
    )


@dataclass
class AssistanceContextBuilder:
    """Build only whitelisted fields; never serialize ORM or API resources."""

    session: AsyncSession
    kb: KnowledgeBaseRepository

    async def for_assessment(
        self, *, assessment_id: str, user_id: str
    ) -> AssistanceContext:
        service = AssessmentService(session=self.session, kb=self.kb)
        assessment = await service.get_owned(
            assessment_id=assessment_id, user_id=user_id
        )
        if assessment.status != AssessmentStatus.COMPLETED:
            raise BadRequestError(
                "The assessment must be completed before requesting an explanation."
            )
        result = await service.build_response(assessment)

        sources: list[GroundingRecord] = []
        activity_ids: list[str] = []
        domain_facts: list[str] = []
        for domain_result in result.domain_results:
            rule = self.kb.get_decision_rule_by_id(
                domain_result.decision_rule_id
            )
            sources.append(
                GroundingRecord(
                    source_id=rule.id,
                    source_type="KB03_decision_rule",
                    title=domain_result.domain.value,
                    excerpt=(
                        f"{rule.ai_recommendation} {rule.follow_up} "
                        f"الإحالة الحتمية: {rule.referral.value}."
                    ),
                )
            )
            domain_facts.append(
                f"{domain_result.domain.value}: "
                f"{domain_result.score_percent}%، "
                f"{domain_result.severity.value}، "
                f"الإحالة {domain_result.referral.value}"
            )
            for activity_id in domain_result.suggested_activity_ids:
                if activity_id not in activity_ids:
                    activity_ids.append(activity_id)

        sources.extend(
            _activity_source(self.kb, activity_id)
            for activity_id in activity_ids[:8]
        )
        assert result.overall_severity is not None
        assert result.overall_referral is not None
        return AssistanceContext(
            operation=AssistanceOperation.ASSESSMENT_EXPLANATION,
            age_band=_age_band(assessment.age_at_assessment),
            immutable_facts={
                "overall_severity": result.overall_severity.value,
                "overall_referral": result.overall_referral.value,
                "priority_domains": [d.value for d in result.priority_domains],
                "strengths": result.strengths[:6],
                "support_needs": result.support_needs[:6],
                "domain_results": domain_facts,
            },
            approved_sources=sources,
        )

    async def for_weekly_plan(
        self, *, weekly_plan_id: str, user_id: str
    ) -> AssistanceContext:
        service = WeeklyPlanService(session=self.session, kb=self.kb)
        plan = await service.get_owned(
            weekly_plan_id=weekly_plan_id, user_id=user_id
        )
        result = await service.build_response(plan)
        assessment = await assessment_repository.get_by_id(
            self.session, plan.assessment_id
        )
        if assessment is None:
            raise BadRequestError("The weekly plan has no assessment context.")

        unique_activity_ids = list(
            dict.fromkeys(slot.activity.id for slot in result.activities)
        )
        sources = [
            _activity_source(self.kb, activity_id)
            for activity_id in unique_activity_ids[:14]
        ]
        goals = list(
            dict.fromkeys(slot.activity.goal for slot in result.activities)
        )
        return AssistanceContext(
            operation=AssistanceOperation.WEEKLY_PLAN_SUMMARY,
            age_band=_age_band(assessment.age_at_assessment),
            immutable_facts={
                "is_active": result.is_active,
                "total_activities": result.total_activities,
                "completed_count": result.completed_count,
                "adherence_percent": result.adherence_percent,
                "weekly_goals": goals[:8],
            },
            approved_sources=sources,
        )

    async def for_followup(
        self, *, followup_id: str, user_id: str
    ) -> AssistanceContext:
        service = FollowupService(session=self.session, kb=self.kb)
        followup = await service.get_owned(
            followup_id=followup_id, user_id=user_id
        )
        assessment = await assessment_repository.get_by_id(
            self.session, followup.previous_assessment_id
        )
        if assessment is None:
            raise BadRequestError("The follow-up has no assessment context.")

        sources: list[GroundingRecord] = []
        seen_source_ids: set[str] = set()
        question_context = followup.question_context or []
        for item in question_context:
            if not isinstance(item, dict):
                continue
            source_question_id = item.get("source_question_id")
            question = item.get("question")
            if (
                isinstance(source_question_id, str)
                and isinstance(question, str)
                and source_question_id not in seen_source_ids
            ):
                seen_source_ids.add(source_question_id)
                sources.append(
                    GroundingRecord(
                        source_id=source_question_id,
                        source_type="KB06_followup_question",
                        title="سؤال متابعة أسبوعية",
                        excerpt=question,
                    )
                )
            activity_id = item.get("activity_id")
            if (
                isinstance(activity_id, str)
                and activity_id not in seen_source_ids
            ):
                seen_source_ids.add(activity_id)
                sources.append(_activity_source(self.kb, activity_id))

        return AssistanceContext(
            operation=AssistanceOperation.FOLLOWUP_SUMMARY,
            age_band=_age_band(assessment.age_at_assessment),
            immutable_facts={
                "progress_percent": followup.current_score_percent,
                "improvement_percent": followup.improvement_percent,
                "improved_domains": list(followup.improved_domains),
                "support_needed_domains": list(
                    followup.support_needed_domains
                ),
                "deterministic_comment": followup.comment,
                "next_goal": followup.next_goal,
            },
            approved_sources=sources[:24],
        )
