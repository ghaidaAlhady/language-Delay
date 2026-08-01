"""Data access for weekly plans and their activity slots."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.weekly_plan import WeeklyPlan, WeeklyPlanActivity


async def get_active_for_child(session: AsyncSession, child_id: str) -> WeeklyPlan | None:
    result = await session.execute(
        select(WeeklyPlan).where(WeeklyPlan.child_id == child_id, WeeklyPlan.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def deactivate_active_for_child(session: AsyncSession, child_id: str) -> None:
    result = await session.execute(
        select(WeeklyPlan).where(WeeklyPlan.child_id == child_id, WeeklyPlan.is_active.is_(True))
    )
    for plan in result.scalars():
        plan.is_active = False
    await session.flush()


async def create(session: AsyncSession, *, child_id: str, assessment_id: str) -> WeeklyPlan:
    plan = WeeklyPlan(child_id=child_id, assessment_id=assessment_id, is_active=True)
    session.add(plan)
    await session.flush()
    return plan


async def add_activity(
    session: AsyncSession,
    *,
    weekly_plan_id: str,
    day: str,
    slot_order: int,
    activity_id: str,
) -> WeeklyPlanActivity:
    slot = WeeklyPlanActivity(
        weekly_plan_id=weekly_plan_id, day=day, slot_order=slot_order, activity_id=activity_id
    )
    session.add(slot)
    await session.flush()
    return slot


async def get_by_id(session: AsyncSession, weekly_plan_id: str) -> WeeklyPlan | None:
    return await session.get(WeeklyPlan, weekly_plan_id)


async def get_activities(
    session: AsyncSession, weekly_plan_id: str
) -> list[WeeklyPlanActivity]:
    result = await session.execute(
        select(WeeklyPlanActivity)
        .where(WeeklyPlanActivity.weekly_plan_id == weekly_plan_id)
        .order_by(WeeklyPlanActivity.day, WeeklyPlanActivity.slot_order)
    )
    return list(result.scalars())


async def get_activity_by_id(
    session: AsyncSession, activity_slot_id: str
) -> WeeklyPlanActivity | None:
    return await session.get(WeeklyPlanActivity, activity_slot_id)


async def set_activity_completed(
    session: AsyncSession,
    slot: WeeklyPlanActivity,
    *,
    completed: bool,
    completed_at: datetime | None,
) -> WeeklyPlanActivity:
    slot.completed = completed
    slot.completed_at = completed_at
    await session.flush()
    return slot


async def set_activity_kb_id(
    session: AsyncSession, slot: WeeklyPlanActivity, *, activity_id: str
) -> WeeklyPlanActivity:
    slot.activity_id = activity_id
    await session.flush()
    return slot


async def freeze_followup_questions_if_empty(
    session: AsyncSession,
    *,
    weekly_plan_id: str,
    question_context: list[dict],
    generation_source: str,
    fallback_reason: str | None,
    frozen_at: datetime,
) -> WeeklyPlan:
    """Persist the first generated question set and return the stored winner.

    The conditional update makes concurrent requests and multi-process
    deployments safe: only the first writer freezes the set, and every caller
    reloads the same database value before returning it to the parent.
    """
    await session.execute(
        update(WeeklyPlan)
        .where(
            WeeklyPlan.id == weekly_plan_id,
            WeeklyPlan.followup_question_context.is_(None),
        )
        .values(
            followup_question_context=question_context,
            followup_generation_source=generation_source,
            followup_fallback_reason=fallback_reason,
            followup_questions_frozen_at=frozen_at,
        )
    )
    await session.commit()
    stored = await get_by_id(session, weekly_plan_id)
    if stored is None:  # pragma: no cover - guarded by ownership/readiness path
        raise RuntimeError("Weekly plan disappeared while freezing follow-up questions.")
    await session.refresh(stored)
    return stored
