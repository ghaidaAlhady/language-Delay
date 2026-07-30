"""Weekly plan generation, completion tracking, and adherence.

Generation is deterministic: activities come from the completed assessment's
KB03-suggested activity IDs (worst-domain-first), topped up from the rest of
the age-appropriate KB02 pool if a domain didn't suggest enough to fill all
14 slots. Nothing is invented — every slot resolves to a real KB02 row.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.core.errors import BadRequestError, ConflictError, NotFoundError, ServiceUnavailableError
from app.models.assessment import Assessment
from app.models.weekly_plan import WeeklyPlan, WeeklyPlanActivity
from app.rag.schemas import SEVERITY_ORDER, Domain, Severity
from app.repositories import assessment_repository, child_repository, weekly_plan_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AssessmentStatus
from app.schemas.weekly_plan import WeeklyPlanActivityResponse, WeeklyPlanResponse

DAYS_PER_WEEK = 7
ACTIVITIES_PER_DAY = 2
TOTAL_ACTIVITIES = DAYS_PER_WEEK * ACTIVITIES_PER_DAY


@dataclass
class WeeklyPlanService:
    session: AsyncSession
    kb: KnowledgeBaseRepository

    async def generate(self, assessment: Assessment) -> WeeklyPlan:
        if assessment.status != AssessmentStatus.COMPLETED:
            raise BadRequestError(
                "The assessment must be completed before generating a weekly plan."
            )

        domain_rows = await assessment_repository.get_domain_results(
            self.session, assessment.id
        )
        ordered_rows = sorted(
            domain_rows,
            key=lambda r: (-SEVERITY_ORDER.index(Severity(r.severity)), r.score_percent),
        )

        selected_ids: list[str] = []
        for row in ordered_rows:
            for activity_id in row.suggested_activity_ids:
                if activity_id not in selected_ids:
                    selected_ids.append(activity_id)

        if len(selected_ids) < TOTAL_ACTIVITIES:
            # Round-robin across domains rather than draining KB02's file
            # order domain-by-domain, so top-up doesn't fully exhaust
            # whichever domain happens to sort first — that would leave no
            # "alternative activity" candidates left for it.
            remaining_by_domain = {
                domain: [
                    a.id
                    for a in self.kb.get_activities_for_age(
                        assessment.age_at_assessment, domain
                    )
                    if a.id not in selected_ids
                ]
                for domain in Domain
            }
            while len(selected_ids) < TOTAL_ACTIVITIES:
                added_any = False
                for domain in Domain:
                    pool = remaining_by_domain[domain]
                    if pool:
                        selected_ids.append(pool.pop(0))
                        added_any = True
                        if len(selected_ids) >= TOTAL_ACTIVITIES:
                            break
                if not added_any:
                    break

        if len(selected_ids) < TOTAL_ACTIVITIES:
            raise ServiceUnavailableError(
                "Not enough age-appropriate activities available to build a full weekly plan."
            )
        selected_ids = selected_ids[:TOTAL_ACTIVITIES]

        await weekly_plan_repository.deactivate_active_for_child(
            self.session, assessment.child_id
        )
        plan = await weekly_plan_repository.create(
            self.session, child_id=assessment.child_id, assessment_id=assessment.id
        )

        days = [d.day for d in self.kb.weekly_plan_template]
        for index, activity_id in enumerate(selected_ids):
            await weekly_plan_repository.add_activity(
                self.session,
                weekly_plan_id=plan.id,
                day=days[index // ACTIVITIES_PER_DAY],
                slot_order=index % ACTIVITIES_PER_DAY + 1,
                activity_id=activity_id,
            )

        await self.session.commit()
        return plan

    async def get_by_id(self, weekly_plan_id: str) -> WeeklyPlan:
        plan = await weekly_plan_repository.get_by_id(self.session, weekly_plan_id)
        if plan is None:
            raise NotFoundError("Weekly plan not found.")
        return plan

    async def get_owned(self, *, weekly_plan_id: str, user_id: str) -> WeeklyPlan:
        plan = await weekly_plan_repository.get_by_id(
            self.session, weekly_plan_id
        )
        if plan is None:
            raise NotFoundError("Weekly plan not found.")
        child = await child_repository.get_by_id(self.session, plan.child_id)
        if child is None or child.user_id != user_id:
            raise NotFoundError("Weekly plan not found.")
        return plan

    async def get_active_owned(self, *, child_id: str, user_id: str) -> WeeklyPlan:
        child = await child_repository.get_by_id(self.session, child_id)
        if child is None or child.user_id != user_id:
            raise NotFoundError("Child not found.")
        plan = await weekly_plan_repository.get_active_for_child(self.session, child_id)
        if plan is None:
            raise NotFoundError("No active weekly plan found for this child.")
        return plan

    async def get_owned_activity_slot(
        self, *, slot_id: str, user_id: str
    ) -> WeeklyPlanActivity:
        slot = await weekly_plan_repository.get_activity_by_id(self.session, slot_id)
        if slot is None:
            raise NotFoundError("Weekly plan activity not found.")
        plan = await weekly_plan_repository.get_by_id(self.session, slot.weekly_plan_id)
        if plan is None:
            raise NotFoundError("Weekly plan activity not found.")
        child = await child_repository.get_by_id(self.session, plan.child_id)
        if child is None or child.user_id != user_id:
            raise NotFoundError("Weekly plan activity not found.")
        return slot

    async def set_completion(
        self, slot: WeeklyPlanActivity, *, completed: bool
    ) -> WeeklyPlanActivity:
        updated = await weekly_plan_repository.set_activity_completed(
            self.session, slot, completed=completed, completed_at=utcnow() if completed else None
        )
        await self.session.commit()
        return updated

    async def suggest_alternative(self, slot: WeeklyPlanActivity) -> WeeklyPlanActivity:
        plan = await weekly_plan_repository.get_by_id(self.session, slot.weekly_plan_id)
        assert plan is not None
        assessment = await assessment_repository.get_by_id(self.session, plan.assessment_id)
        assert assessment is not None

        current_activity = self.kb.get_activity(slot.activity_id)
        existing_ids = {
            s.activity_id
            for s in await weekly_plan_repository.get_activities(self.session, plan.id)
        }
        candidates = [
            a
            for a in self.kb.get_activities_for_age(
                assessment.age_at_assessment, current_activity.domain
            )
            if a.id not in existing_ids
        ]
        if not candidates:
            raise ConflictError(
                "No alternative activity is available for this domain and age."
            )

        updated = await weekly_plan_repository.set_activity_kb_id(
            self.session, slot, activity_id=candidates[0].id
        )
        await self.session.commit()
        return updated

    async def build_response(self, plan: WeeklyPlan) -> WeeklyPlanResponse:
        slots = await weekly_plan_repository.get_activities(self.session, plan.id)
        activity_responses = [
            WeeklyPlanActivityResponse(
                id=slot.id,
                day=slot.day,
                slot_order=slot.slot_order,
                completed=slot.completed,
                completed_at=slot.completed_at,
                activity=self.kb.get_activity(slot.activity_id),
            )
            for slot in slots
        ]
        completed_count = sum(1 for a in activity_responses if a.completed)
        total = len(activity_responses)
        adherence_percent = round((completed_count / total * 100) if total else 0.0, 2)

        return WeeklyPlanResponse(
            id=plan.id,
            child_id=plan.child_id,
            assessment_id=plan.assessment_id,
            is_active=plan.is_active,
            generated_at=plan.created_at,
            total_activities=total,
            completed_count=completed_count,
            adherence_percent=adherence_percent,
            activities=activity_responses,
        )
