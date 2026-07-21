"""Data access for assessments, answers, and per-domain results."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, AssessmentAnswer, AssessmentDomainResult
from app.services.scoring_service import DomainScoreResult


async def create(session: AsyncSession, *, child_id: str, age_at_assessment: int) -> Assessment:
    assessment = Assessment(child_id=child_id, age_at_assessment=age_at_assessment)
    session.add(assessment)
    await session.flush()
    return assessment


async def get_by_id(session: AsyncSession, assessment_id: str) -> Assessment | None:
    return await session.get(Assessment, assessment_id)


async def list_for_child(session: AsyncSession, child_id: str) -> list[Assessment]:
    result = await session.execute(
        select(Assessment)
        .where(Assessment.child_id == child_id)
        .order_by(Assessment.created_at.desc())
    )
    return list(result.scalars())


async def get_answers(session: AsyncSession, assessment_id: str) -> list[AssessmentAnswer]:
    result = await session.execute(
        select(AssessmentAnswer).where(AssessmentAnswer.assessment_id == assessment_id)
    )
    return list(result.scalars())


async def upsert_answer(
    session: AsyncSession,
    *,
    assessment_id: str,
    question_id: str,
    response: str,
    score_weight: float,
) -> AssessmentAnswer:
    result = await session.execute(
        select(AssessmentAnswer).where(
            AssessmentAnswer.assessment_id == assessment_id,
            AssessmentAnswer.question_id == question_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        existing.response = response
        existing.score_weight = score_weight
        await session.flush()
        return existing

    answer = AssessmentAnswer(
        assessment_id=assessment_id,
        question_id=question_id,
        response=response,
        score_weight=score_weight,
    )
    session.add(answer)
    await session.flush()
    return answer


async def get_domain_results(
    session: AsyncSession, assessment_id: str
) -> list[AssessmentDomainResult]:
    result = await session.execute(
        select(AssessmentDomainResult).where(
            AssessmentDomainResult.assessment_id == assessment_id
        )
    )
    return list(result.scalars())


async def save_domain_results(
    session: AsyncSession, *, assessment_id: str, results: list[DomainScoreResult]
) -> None:
    for result in results:
        session.add(
            AssessmentDomainResult(
                assessment_id=assessment_id,
                domain=result.domain.value,
                score_percent=result.score_percent,
                severity=result.severity.value,
                referral=result.referral.value,
                decision_rule_id=result.decision_rule_id,
                recommendation=result.recommendation,
                follow_up=result.follow_up,
                suggested_activity_ids=result.suggested_activity_ids,
            )
        )
    await session.flush()


async def mark_completed(
    session: AsyncSession,
    assessment: Assessment,
    *,
    overall_severity: str,
    overall_referral: str,
    confidence_score: float,
    completed_at: datetime,
) -> Assessment:
    assessment.status = "completed"
    assessment.completed_at = completed_at
    assessment.overall_severity = overall_severity
    assessment.overall_referral = overall_referral
    assessment.confidence_score = confidence_score
    await session.flush()
    return assessment
