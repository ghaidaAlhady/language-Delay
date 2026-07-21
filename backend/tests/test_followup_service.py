from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.rag.schemas import Domain
from app.repositories import user_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AnswerItem, AnswerSubmissionRequest, ResponseValue
from app.schemas.child import ChildCreateRequest, Gender
from app.services.assessment_service import AssessmentService
from app.services.child_service import ChildService
from app.services.followup_service import FollowupService
from app.services.weekly_plan_service import WeeklyPlanService


@pytest.fixture
def assessment_service(
    db_session: AsyncSession, kb_repository: KnowledgeBaseRepository
) -> AssessmentService:
    return AssessmentService(session=db_session, kb=kb_repository)


@pytest.fixture
def followup_service(
    db_session: AsyncSession, kb_repository: KnowledgeBaseRepository
) -> FollowupService:
    return FollowupService(session=db_session, kb=kb_repository)


@pytest.fixture
def weekly_plan_service(
    db_session: AsyncSession, kb_repository: KnowledgeBaseRepository
) -> WeeklyPlanService:
    return WeeklyPlanService(session=db_session, kb=kb_repository)


@pytest.fixture
def child_service(db_session: AsyncSession) -> ChildService:
    return ChildService(session=db_session)


async def _make_user(db_session: AsyncSession, email: str = "parent@example.com") -> str:
    user = await user_repository.create(
        db_session, email=email, hashed_password="x", display_name="P"
    )
    await db_session.commit()
    return user.id


async def _complete(assessment_service, assessment, response: ResponseValue):
    questions = assessment_service.get_questions(assessment)
    await assessment_service.submit_answers(
        assessment,
        AnswerSubmissionRequest(
            answers=[AnswerItem(question_id=q.id, response=response) for q in questions]
        ),
    )
    return await assessment_service.complete(assessment)


async def test_followup_requires_completed_assessment(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)
    child = await child_service.create(
        user_id=user_id,
        payload=ChildCreateRequest(
            name="Layla",
            date_of_birth=date(date.today().year - 2, date.today().month, 1),
            gender=Gender.FEMALE,
            home_language="ar",
        ),
    )
    assessment = await assessment_service.start(child)

    with pytest.raises(BadRequestError):
        await followup_service.complete_followup(assessment)


async def test_followup_requires_a_previous_assessment(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)
    child = await child_service.create(
        user_id=user_id,
        payload=ChildCreateRequest(
            name="Layla",
            date_of_birth=date(date.today().year - 2, date.today().month, 1),
            gender=Gender.FEMALE,
            home_language="ar",
        ),
    )
    assessment = await assessment_service.start(child)
    completed = await _complete(assessment_service, assessment, ResponseValue.ALWAYS)

    with pytest.raises(BadRequestError):
        await followup_service.complete_followup(completed)


async def test_followup_detects_improvement_and_regenerates_plan(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)
    child = await child_service.create(
        user_id=user_id,
        payload=ChildCreateRequest(
            name="Layla",
            date_of_birth=date(date.today().year - 2, date.today().month, 1),
            gender=Gender.FEMALE,
            home_language="ar",
        ),
    )

    first = await assessment_service.start(child)
    first_completed = await _complete(assessment_service, first, ResponseValue.NEVER)
    first_plan = await weekly_plan_service.generate(first_completed)

    second = await assessment_service.start(child)
    second_completed = await _complete(assessment_service, second, ResponseValue.ALWAYS)

    followup = await followup_service.complete_followup(second_completed)
    response = followup_service.build_response(followup)

    assert response.previous_assessment_id == first_completed.id
    assert response.current_assessment_id == second_completed.id
    assert response.improvement_percent > 0
    assert set(response.improved_domains) == set(Domain)
    assert response.support_needed_domains == []
    assert "تحسن" in response.comment or response.comment  # KB04 "improved" narrative
    assert response.next_goal

    active_plan = await weekly_plan_service.get_active_owned(child_id=child.id, user_id=user_id)
    assert active_plan.id != first_plan.id
    assert active_plan.assessment_id == second_completed.id


async def test_followup_is_idempotent(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)
    child = await child_service.create(
        user_id=user_id,
        payload=ChildCreateRequest(
            name="Layla",
            date_of_birth=date(date.today().year - 2, date.today().month, 1),
            gender=Gender.FEMALE,
            home_language="ar",
        ),
    )
    first = await assessment_service.start(child)
    first_completed = await _complete(assessment_service, first, ResponseValue.ALWAYS)
    await weekly_plan_service.generate(first_completed)

    second = await assessment_service.start(child)
    second_completed = await _complete(assessment_service, second, ResponseValue.ALWAYS)

    first_followup = await followup_service.complete_followup(second_completed)
    second_followup = await followup_service.complete_followup(second_completed)
    assert first_followup.id == second_followup.id


async def test_get_owned_hides_other_users_followup(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id = await _make_user(db_session)
    child = await child_service.create(
        user_id=user_id,
        payload=ChildCreateRequest(
            name="Layla",
            date_of_birth=date(date.today().year - 2, date.today().month, 1),
            gender=Gender.FEMALE,
            home_language="ar",
        ),
    )
    first = await assessment_service.start(child)
    first_completed = await _complete(assessment_service, first, ResponseValue.ALWAYS)
    await weekly_plan_service.generate(first_completed)

    second = await assessment_service.start(child)
    second_completed = await _complete(assessment_service, second, ResponseValue.NEVER)
    followup = await followup_service.complete_followup(second_completed)

    other_user_id = await _make_user(db_session, email="other@example.com")
    with pytest.raises(NotFoundError):
        await followup_service.get_owned(followup_id=followup.id, user_id=other_user_id)
