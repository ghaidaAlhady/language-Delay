"""Data access for follow-up / reassessment records."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.followup import Followup


async def get_by_id(session: AsyncSession, followup_id: str) -> Followup | None:
    return await session.get(Followup, followup_id)


async def get_by_current_assessment_id(
    session: AsyncSession, current_assessment_id: str
) -> Followup | None:
    result = await session.execute(
        select(Followup).where(Followup.current_assessment_id == current_assessment_id)
    )
    return result.scalar_one_or_none()


async def get_most_recent_completed_other_than(
    session: AsyncSession, *, child_id: str, exclude_assessment_id: str
) -> Assessment | None:
    result = await session.execute(
        select(Assessment)
        .where(
            Assessment.child_id == child_id,
            Assessment.status == "completed",
            Assessment.id != exclude_assessment_id,
        )
        .order_by(Assessment.completed_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_for_child(session: AsyncSession, child_id: str) -> list[Followup]:
    result = await session.execute(
        select(Followup).where(Followup.child_id == child_id).order_by(Followup.created_at.desc())
    )
    return list(result.scalars())


async def create(
    session: AsyncSession,
    *,
    child_id: str,
    previous_assessment_id: str,
    current_assessment_id: str,
    previous_score_percent: float,
    current_score_percent: float,
    improvement_percent: float,
    improved_domains: list[str],
    support_needed_domains: list[str],
    comment: str,
    next_goal: str,
) -> Followup:
    followup = Followup(
        child_id=child_id,
        previous_assessment_id=previous_assessment_id,
        current_assessment_id=current_assessment_id,
        previous_score_percent=previous_score_percent,
        current_score_percent=current_score_percent,
        improvement_percent=improvement_percent,
        improved_domains=improved_domains,
        support_needed_domains=support_needed_domains,
        comment=comment,
        next_goal=next_goal,
    )
    session.add(followup)
    await session.flush()
    return followup
