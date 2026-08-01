"""Deterministic weekly-plan follow-up using KB06, never the initial KB05 set."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import FallbackReason, GenerationSource
from app.core.database import utcnow
from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.followup import Followup
from app.models.weekly_plan import WeeklyPlan
from app.rag.schemas import Domain
from app.repositories import (
    assessment_repository,
    child_repository,
    followup_repository,
    weekly_plan_repository,
)
from app.repositories.knowledge_base_repository import (
    KnowledgeBaseRepository,
    SelectedWeeklyFollowupQuestion,
)
from app.schemas.assessment import ResponseValue
from app.schemas.followup import (
    FollowupResponse,
    WeeklyFollowupContextResponse,
    WeeklyFollowupQuestionResponse,
    WeeklyFollowupSubmissionRequest,
)
from app.services.weekly_plan_service import (
    WeeklyPlanService,
    activities_remaining_for_eligibility,
    completion_stats,
    is_reassessment_eligible,
)

logger = get_logger(__name__)

WEEKLY_RESPONSE_WEIGHTS: dict[ResponseValue, float] = {
    ResponseValue.ALWAYS: 1.0,
    ResponseValue.OFTEN: 0.75,
    ResponseValue.SOMETIMES: 0.5,
    ResponseValue.RARELY: 0.25,
    ResponseValue.NEVER: 0.0,
}


def _progress_comment(progress_percent: float) -> str:
    if progress_percent >= 75:
        return (
            "أظهرت إجابات المتابعة تقدّمًا واضحًا في المهارات التي تدرب عليها "
            "الطفل ضمن الخطة الأسبوعية."
        )
    if progress_percent >= 50:
        return (
            "أظهرت إجابات المتابعة تقدّمًا تدريجيًا في مهارات الخطة الأسبوعية، "
            "مع أهمية الاستمرار في الممارسة."
        )
    return (
        "تشير إجابات المتابعة إلى أن مهارات الخطة الأسبوعية تحتاج إلى مزيد من "
        "الممارسة والدعم المنزلي."
    )


@dataclass
class FollowupService:
    session: AsyncSession
    kb: KnowledgeBaseRepository

    async def _get_owned_plan(
        self, *, weekly_plan_id: str, user_id: str
    ) -> WeeklyPlan:
        plan = await weekly_plan_repository.get_by_id(self.session, weekly_plan_id)
        if plan is None:
            raise NotFoundError("Weekly plan not found.")
        child = await child_repository.get_by_id(self.session, plan.child_id)
        if child is None or child.user_id != user_id:
            raise NotFoundError("Weekly plan not found.")
        return plan

    async def _validate_plan_ready(self, plan: WeeklyPlan) -> None:
        active_plan = await weekly_plan_repository.get_active_for_child(
            self.session, plan.child_id
        )
        if not plan.is_active or active_plan is None or active_plan.id != plan.id:
            raise ConflictError(
                "The selected weekly plan is no longer the child's active plan."
            )
        slots = await weekly_plan_repository.get_activities(self.session, plan.id)
        completed, total = completion_stats(slots)
        if not is_reassessment_eligible(completed, total):
            raise BadRequestError(
                "At least 70% of the active weekly plan's activities must be "
                "completed before starting follow-up.",
                details={
                    "completed_count": completed,
                    "total_activities": total,
                    "required_percent": 70,
                    "remaining_for_eligibility": activities_remaining_for_eligibility(
                        completed, total
                    ),
                },
            )

    async def _select_questions(
        self, plan: WeeklyPlan
    ) -> tuple[list[SelectedWeeklyFollowupQuestion], int]:
        assessment = await assessment_repository.get_by_id(
            self.session, plan.assessment_id
        )
        if assessment is None:
            raise NotFoundError("Weekly plan assessment not found.")
        slots = await weekly_plan_repository.get_activities(self.session, plan.id)
        day_order = {
            template.day: index
            for index, template in enumerate(self.kb.weekly_plan_template)
        }
        ordered_slots = sorted(
            slots,
            key=lambda slot: (
                # Completed activities first (reassessment is now allowed
                # from 70% completion, so some slots may still be open) —
                # `select_weekly_followup_questions` below caps to the first
                # 8, so this ordering is what makes candidate selection
                # prioritize completed activities.
                not slot.completed,
                day_order.get(slot.day, len(day_order)),
                slot.slot_order,
                slot.id,
            ),
        )
        activities = [
            self.kb.get_activity(slot.activity_id) for slot in ordered_slots
        ]
        return (
            self.kb.select_weekly_followup_questions(
                age=assessment.age_at_assessment,
                activities=activities,
            ),
            assessment.age_at_assessment,
        )

    def _build_question_response(
        self,
        *,
        plan: WeeklyPlan,
        age: int,
        selected: SelectedWeeklyFollowupQuestion,
    ) -> WeeklyFollowupQuestionResponse:
        record = selected.source_record
        activity = selected.activity
        return WeeklyFollowupQuestionResponse(
            id=selected.id,
            source_question_id=record.id,
            source_file=record.source_file,
            weekly_plan_id=plan.id,
            age=age,
            domain=activity.domain,
            weekly_goal=activity.goal,
            skill=activity.target_skill,
            activity_id=activity.id,
            activity_name=activity.name,
            expected_behavior=activity.expected_outcome,
            question=selected.question_text_ar,
            response_type=record.response_type,
            required=record.required,
            progress_weight=record.progress_weight,
            fallback_used=selected.fallback_used,
        )

    async def get_question_context(
        self, *, weekly_plan_id: str, user_id: str
    ) -> WeeklyFollowupContextResponse:
        plan = await self._get_owned_plan(
            weekly_plan_id=weekly_plan_id, user_id=user_id
        )
        await self._validate_plan_ready(plan)
        child = await child_repository.get_by_id(self.session, plan.child_id)
        assert child is not None
        slots = await weekly_plan_repository.get_activities(self.session, plan.id)
        selected, age = await self._select_questions(plan)
        questions = [
            self._build_question_response(plan=plan, age=age, selected=question)
            for question in selected
        ]
        fallback_count = sum(1 for question in questions if question.fallback_used)
        if fallback_count:
            logger.info(
                "weekly_followup_kb06_fallback",
                weekly_plan_id=plan.id,
                fallback_question_count=fallback_count,
            )
        weekly_goals = list(dict.fromkeys(question.weekly_goal for question in questions))
        return WeeklyFollowupContextResponse(
            child_id=child.id,
            child_name=child.name,
            weekly_plan_id=plan.id,
            assessment_id=plan.assessment_id,
            generated_at=plan.created_at,
            completed_count=sum(1 for slot in slots if slot.completed),
            total_activities=len(slots),
            weekly_goals=weekly_goals,
            questions=questions,
        )

    async def get_frozen_question_set(
        self, *, weekly_plan_id: str, user_id: str
    ) -> tuple[
        list[WeeklyFollowupQuestionResponse],
        GenerationSource,
        FallbackReason | None,
    ] | None:
        """Return the database-frozen question set for this owned plan.

        Invalid legacy/corrupt payloads are ignored safely so the route can
        regenerate and freeze a valid deterministic/provider-backed set.
        """
        plan = await self._get_owned_plan(
            weekly_plan_id=weekly_plan_id, user_id=user_id
        )
        raw_questions = plan.followup_question_context
        if not raw_questions:
            return None
        try:
            questions = [
                WeeklyFollowupQuestionResponse.model_validate(item)
                for item in raw_questions
            ]
            if not 5 <= len(questions) <= 8:
                return None
            source = GenerationSource(
                plan.followup_generation_source
                or GenerationSource.DETERMINISTIC_FALLBACK.value
            )
            reason = (
                FallbackReason(plan.followup_fallback_reason)
                if plan.followup_fallback_reason
                else None
            )
        except (TypeError, ValueError):
            logger.warning(
                "invalid_frozen_followup_question_context",
                weekly_plan_id=weekly_plan_id,
            )
            return None
        return questions, source, reason

    async def freeze_question_set(
        self,
        *,
        weekly_plan_id: str,
        user_id: str,
        questions: list[WeeklyFollowupQuestionResponse],
        generation_source: GenerationSource,
        fallback_reason: FallbackReason | None,
    ) -> tuple[
        list[WeeklyFollowupQuestionResponse],
        GenerationSource,
        FallbackReason | None,
    ]:
        """Atomically freeze and return the first question set for a plan."""
        plan = await self._get_owned_plan(
            weekly_plan_id=weekly_plan_id, user_id=user_id
        )
        stored = await weekly_plan_repository.freeze_followup_questions_if_empty(
            self.session,
            weekly_plan_id=plan.id,
            question_context=[question.model_dump(mode="json") for question in questions],
            generation_source=generation_source.value,
            fallback_reason=fallback_reason.value if fallback_reason else None,
            frozen_at=utcnow(),
        )
        stored_questions = [
            WeeklyFollowupQuestionResponse.model_validate(item)
            for item in (stored.followup_question_context or [])
        ]
        stored_source = GenerationSource(
            stored.followup_generation_source
            or GenerationSource.DETERMINISTIC_FALLBACK.value
        )
        stored_reason = (
            FallbackReason(stored.followup_fallback_reason)
            if stored.followup_fallback_reason
            else None
        )
        return stored_questions, stored_source, stored_reason

    async def get_existing_for_plan(
        self, *, weekly_plan_id: str, user_id: str
    ) -> Followup | None:
        """Cheap idempotency pre-check, deliberately with no plan-readiness
        validation: a plan is always deactivated once its follow-up is
        submitted, so validating "is this plan still active" would itself
        reject the very duplicate-submission case this is meant to detect.
        Callers (the API route) must check this *before* building an
        AI-varied question context, not after."""
        plan = await self._get_owned_plan(
            weekly_plan_id=weekly_plan_id, user_id=user_id
        )
        return await followup_repository.get_by_weekly_plan_id(self.session, plan.id)

    async def submit(
        self,
        *,
        weekly_plan_id: str,
        user_id: str,
        payload: WeeklyFollowupSubmissionRequest,
        expected_questions: list[WeeklyFollowupQuestionResponse] | None = None,
    ) -> Followup:
        """`expected_questions` should be the exact set the parent was shown
        (e.g. the AI-varied/frozen set from `app.ai.followup_questions`, via
        the API route composition). Falls back to the plain deterministic set
        when not supplied, e.g. direct API use without the AI layer."""
        plan = await self._get_owned_plan(
            weekly_plan_id=weekly_plan_id, user_id=user_id
        )
        existing = await followup_repository.get_by_weekly_plan_id(
            self.session, plan.id
        )
        if existing is not None:
            return existing

        await self._validate_plan_ready(plan)
        if expected_questions is None:
            context = await self.get_question_context(
                weekly_plan_id=plan.id, user_id=user_id
            )
            expected_questions = context.questions
        expected_by_id = {question.id: question for question in expected_questions}
        submitted_ids = [answer.question_id for answer in payload.answers]
        duplicate_ids = sorted(
            question_id
            for question_id in set(submitted_ids)
            if submitted_ids.count(question_id) > 1
        )
        if duplicate_ids:
            raise BadRequestError(
                "Each weekly follow-up question may be answered only once.",
                details={"duplicate_question_ids": duplicate_ids},
            )
        unknown_ids = sorted(set(submitted_ids) - set(expected_by_id))
        missing_ids = sorted(set(expected_by_id) - set(submitted_ids))
        if unknown_ids or missing_ids:
            raise BadRequestError(
                "Answers must match the complete KB06 question set for this weekly plan.",
                details={
                    "invalid_question_ids": unknown_ids,
                    "missing_question_ids": missing_ids,
                },
            )

        domain_totals: dict[Domain, float] = defaultdict(float)
        domain_weights: dict[Domain, float] = defaultdict(float)
        weighted_total = 0.0
        total_weight = 0.0
        answer_snapshot: list[dict] = []
        for answer in payload.answers:
            question = expected_by_id[answer.question_id]
            response_weight = WEEKLY_RESPONSE_WEIGHTS[answer.response]
            weighted_value = response_weight * question.progress_weight
            weighted_total += weighted_value
            total_weight += question.progress_weight
            domain_totals[question.domain] += weighted_value
            domain_weights[question.domain] += question.progress_weight
            answer_snapshot.append(
                {
                    "question_id": answer.question_id,
                    "response": answer.response.value,
                    "score_weight": response_weight,
                }
            )

        progress_percent = round(
            (weighted_total / total_weight * 100) if total_weight else 0.0, 2
        )
        domain_scores = {
            domain: round(domain_totals[domain] / weight * 100, 2)
            for domain, weight in domain_weights.items()
        }
        improved_domains = [
            domain for domain, score in domain_scores.items() if score >= 50
        ]
        support_needed_domains = [
            domain for domain, score in domain_scores.items() if score < 50
        ]
        priority_domain = min(
            domain_scores, key=lambda domain: (domain_scores[domain], domain.value)
        )
        priority_question = next(
            question
            for question in expected_questions
            if question.domain == priority_domain
        )
        next_goal = (
            f"الهدف القادم: الاستمرار في «{priority_question.weekly_goal}» "
            f"من خلال أنشطة {priority_domain.value}."
        )

        try:
            followup = await followup_repository.create(
                self.session,
                child_id=plan.child_id,
                previous_assessment_id=plan.assessment_id,
                current_assessment_id=None,
                weekly_plan_id=plan.id,
                previous_score_percent=100.0,
                current_score_percent=progress_percent,
                improvement_percent=progress_percent,
                improved_domains=[domain.value for domain in improved_domains],
                support_needed_domains=[
                    domain.value for domain in support_needed_domains
                ],
                comment=_progress_comment(progress_percent),
                next_goal=next_goal,
                question_answers=answer_snapshot,
                question_context=[
                    question.model_dump(mode="json")
                    for question in expected_questions
                ],
            )
        except IntegrityError:
            await self.session.rollback()
            existing = await followup_repository.get_by_weekly_plan_id(
                self.session, plan.id
            )
            if existing is not None:
                return existing
            raise

        assessment = await assessment_repository.get_by_id(
            self.session, plan.assessment_id
        )
        assert assessment is not None
        weekly_plan_service = WeeklyPlanService(session=self.session, kb=self.kb)
        await weekly_plan_service.generate(assessment)
        return followup

    async def get_owned(self, *, followup_id: str, user_id: str) -> Followup:
        followup = await followup_repository.get_by_id(self.session, followup_id)
        if followup is None:
            raise NotFoundError("Follow-up not found.")
        child = await child_repository.get_by_id(self.session, followup.child_id)
        if child is None or child.user_id != user_id:
            raise NotFoundError("Follow-up not found.")
        return followup

    async def list_for_child(self, child_id: str) -> list[Followup]:
        return await followup_repository.list_for_child(self.session, child_id)

    def build_response(self, followup: Followup) -> FollowupResponse:
        return FollowupResponse(
            id=followup.id,
            child_id=followup.child_id,
            previous_assessment_id=followup.previous_assessment_id,
            current_assessment_id=followup.current_assessment_id,
            weekly_plan_id=followup.weekly_plan_id,
            previous_score_percent=followup.previous_score_percent,
            current_score_percent=followup.current_score_percent,
            improvement_percent=followup.improvement_percent,
            improved_domains=[Domain(d) for d in followup.improved_domains],
            support_needed_domains=[
                Domain(d) for d in followup.support_needed_domains
            ],
            comment=followup.comment,
            next_goal=followup.next_goal,
            created_at=followup.created_at,
        )
