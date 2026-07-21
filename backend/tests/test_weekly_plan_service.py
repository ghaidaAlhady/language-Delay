from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.repositories import user_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AnswerItem, AnswerSubmissionRequest, ResponseValue
from app.schemas.child import ChildCreateRequest, Gender
from app.services.assessment_service import AssessmentService
from app.services.child_service import ChildService
from app.services.weekly_plan_service import TOTAL_ACTIVITIES, WeeklyPlanService


@pytest.fixture
def assessment_service(
    db_session: AsyncSession, kb_repository: KnowledgeBaseRepository
) -> AssessmentService:
    return AssessmentService(session=db_session, kb=kb_repository)


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


async def _completed_assessment(
    assessment_service: AssessmentService,
    child_service: ChildService,
    db_session: AsyncSession,
    *,
    response: ResponseValue = ResponseValue.NEVER,
    age: int = 2,
):
    user_id = await _make_user(db_session)
    today = date.today()
    dob = date(today.year - age, today.month, min(today.day, 28))
    child = await child_service.create(
        user_id=user_id,
        payload=ChildCreateRequest(
            name="Layla", date_of_birth=dob, gender=Gender.FEMALE, home_language="ar"
        ),
    )
    assessment = await assessment_service.start(child)
    questions = assessment_service.get_questions(assessment)
    await assessment_service.submit_answers(
        assessment,
        AnswerSubmissionRequest(
            answers=[AnswerItem(question_id=q.id, response=response) for q in questions]
        ),
    )
    completed = await assessment_service.complete(assessment)
    return user_id, child, completed


async def test_generate_requires_completed_assessment(
    assessment_service: AssessmentService,
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
    assessment = await assessment_service.start(child)

    with pytest.raises(BadRequestError):
        await weekly_plan_service.generate(assessment)


async def test_generate_creates_exactly_7_days_2_activities(
    assessment_service: AssessmentService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    _user_id, _child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session
    )

    plan = await weekly_plan_service.generate(assessment)
    response = await weekly_plan_service.build_response(plan)

    assert response.total_activities == TOTAL_ACTIVITIES
    days = {a.day for a in response.activities}
    assert len(days) == 7
    for day in days:
        slots = [a for a in response.activities if a.day == day]
        assert len(slots) == 2
        assert {s.slot_order for s in slots} == {1, 2}

    # Every slot resolves to a real, traceable KB02 activity.
    activity_ids = {a.activity.id for a in response.activities}
    assert len(activity_ids) == len(response.activities)  # no duplicate activities


async def test_generate_deactivates_previous_plan(
    assessment_service: AssessmentService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id, child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session
    )
    first_plan = await weekly_plan_service.generate(assessment)

    second_assessment = await assessment_service.start(child)
    questions = assessment_service.get_questions(second_assessment)
    await assessment_service.submit_answers(
        second_assessment,
        AnswerSubmissionRequest(
            answers=[
                AnswerItem(question_id=q.id, response=ResponseValue.ALWAYS) for q in questions
            ]
        ),
    )
    second_assessment = await assessment_service.complete(second_assessment)
    second_plan = await weekly_plan_service.generate(second_assessment)

    active = await weekly_plan_service.get_active_owned(child_id=child.id, user_id=user_id)
    assert active.id == second_plan.id
    assert active.id != first_plan.id

    refreshed_first = await weekly_plan_service.get_by_id(first_plan.id)
    assert refreshed_first.is_active is False


async def test_get_active_owned_hides_other_users_plan(
    assessment_service: AssessmentService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    _user_id, child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session
    )
    await weekly_plan_service.generate(assessment)

    other_user_id = await _make_user(db_session, email="other@example.com")
    with pytest.raises(NotFoundError):
        await weekly_plan_service.get_active_owned(child_id=child.id, user_id=other_user_id)


async def test_set_completion_updates_adherence(
    assessment_service: AssessmentService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    _user_id, _child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session
    )
    plan = await weekly_plan_service.generate(assessment)
    response = await weekly_plan_service.build_response(plan)
    slot_id = response.activities[0].id

    from app.repositories import weekly_plan_repository

    slot = await weekly_plan_repository.get_activity_by_id(db_session, slot_id)
    assert slot is not None
    await weekly_plan_service.set_completion(slot, completed=True)

    updated = await weekly_plan_service.build_response(plan)
    assert updated.completed_count == 1
    assert updated.adherence_percent == round(1 / TOTAL_ACTIVITIES * 100, 2)


async def test_suggest_alternative_replaces_activity_without_duplicating(
    assessment_service: AssessmentService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
    kb_repository: KnowledgeBaseRepository,
) -> None:
    _user_id, _child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session, response=ResponseValue.ALWAYS
    )
    plan = await weekly_plan_service.generate(assessment)
    response = await weekly_plan_service.build_response(plan)

    used_ids = {a.activity.id for a in response.activities}
    # Find a slot whose domain still has an unused KB02 activity at this age
    # (the generator's domain-blind top-up can fully exhaust some domains —
    # see test_suggest_alternative_raises_conflict_when_domain_pool_exhausted).
    target = next(
        a
        for a in response.activities
        if any(
            candidate.id not in used_ids
            for candidate in kb_repository.get_activities_for_age(
                assessment.age_at_assessment, a.activity.domain
            )
        )
    )

    from app.repositories import weekly_plan_repository

    slot = await weekly_plan_repository.get_activity_by_id(db_session, target.id)
    assert slot is not None
    updated_slot = await weekly_plan_service.suggest_alternative(slot)

    assert updated_slot.activity_id != target.activity.id
    refreshed = await weekly_plan_service.build_response(plan)
    activity_ids = [a.activity.id for a in refreshed.activities]
    assert len(activity_ids) == len(set(activity_ids))


async def test_suggest_alternative_raises_conflict_when_domain_pool_exhausted(
    assessment_service: AssessmentService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    # Every domain at NOTABLE_DELAY suggests its entire age-appropriate KB02
    # pool, so a fully-"never" assessment can exhaust a domain with no
    # unused activity left to offer as an alternative.
    _user_id, _child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session, response=ResponseValue.NEVER
    )
    plan = await weekly_plan_service.generate(assessment)
    response = await weekly_plan_service.build_response(plan)

    from app.repositories import weekly_plan_repository

    slot = await weekly_plan_repository.get_activity_by_id(
        db_session, response.activities[0].id
    )
    assert slot is not None
    with pytest.raises(ConflictError):
        await weekly_plan_service.suggest_alternative(slot)
