"""Data access for generated reports."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment
from app.models.report import Report


async def get_by_id(session: AsyncSession, report_id: str) -> Report | None:
    return await session.get(Report, report_id)


async def get_by_assessment_id(session: AsyncSession, assessment_id: str) -> Report | None:
    result = await session.execute(
        select(Report).where(Report.assessment_id == assessment_id)
    )
    return result.scalar_one_or_none()


async def list_for_child(session: AsyncSession, child_id: str) -> list[Report]:
    result = await session.execute(
        select(Report)
        .join(Assessment, Report.assessment_id == Assessment.id)
        .where(Assessment.child_id == child_id)
        .order_by(Report.created_at.desc())
    )
    return list(result.scalars())


async def next_report_number(session: AsyncSession) -> str:
    total = await session.scalar(select(func.count()).select_from(Report))
    return f"REP-{(total or 0) + 1:04d}"


async def create(
    session: AsyncSession,
    *,
    assessment_id: str,
    report_number: str,
    summary_text: str,
    weekly_goal: str,
    next_reassessment: str,
) -> Report:
    report = Report(
        assessment_id=assessment_id,
        report_number=report_number,
        summary_text=summary_text,
        weekly_goal=weekly_goal,
        next_reassessment=next_reassessment,
    )
    session.add(report)
    await session.flush()
    return report
