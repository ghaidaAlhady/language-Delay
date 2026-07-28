from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.repositories import followup_repository, user_repository, weekly_plan_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AnswerItem, AnswerSubmissionRequest, ResponseValue
from app.schemas.child import ChildCreateRequest, Gender
from app.schemas.followup import (
    WeeklyFollowupAnswerItem,
    WeeklyFollowupSubmissionRequest,
)
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


async def _make_user(
    db_session: AsyncSession, email: str = "parent@example.com"
) -> str:
    user = await user_repository.create(
        db_session, email=email, hashed_password="x", display_name="P"
    )
    await db_session.commit()
    return user.id


async def _create_child_and_plan(
    *,
    db_session: AsyncSession,
    assessment_service: AssessmentService,
    child_service: ChildService,
    weekly_plan_service: WeeklyPlanService,
) -> tuple[str, object, object, object]:
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
    questions = assessment_service.get_questions(assessment)
    await assessment_service.submit_answers(
        assessment,
        AnswerSubmissionRequest(
            answers=[
                AnswerItem(question_id=question.id, response=ResponseValue.NEVER)
                for question in questions
            ]
        ),
    )
    completed = await assessment_service.complete(assessment)
    plan = await weekly_plan_service.generate(completed)
    return user_id, child, completed, plan


async def _complete_plan(
    db_session: AsyncSession,
    weekly_plan_service: WeeklyPlanService,
    plan_id: str,
) -> None:
    slots = await weekly_plan_repository.get_activities(db_session, plan_id)
    for slot in slots:
        await weekly_plan_service.set_completion(slot, completed=True)


def _payload_for_context(context, response: ResponseValue = ResponseValue.ALWAYS):
    return WeeklyFollowupSubmissionRequest(
        answers=[
            WeeklyFollowupAnswerItem(question_id=question.id, response=response)
            for question in context.questions
        ]
    )


async def test_kb06_context_requires_fully_completed_active_plan(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id, _child, _assessment, plan = await _create_child_and_plan(
        db_session=db_session,
        assessment_service=assessment_service,
        child_service=child_service,
        weekly_plan_service=weekly_plan_service,
    )

    with pytest.raises(BadRequestError, match="All activities"):
        await followup_service.get_question_context(
            weekly_plan_id=plan.id, user_id=user_id
        )


async def test_kb06_context_matches_plan_age_domain_goal_and_activity(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id, child, assessment, plan = await _create_child_and_plan(
        db_session=db_session,
        assessment_service=assessment_service,
        child_service=child_service,
        weekly_plan_service=weekly_plan_service,
    )
    await _complete_plan(db_session, weekly_plan_service, plan.id)

    context = await followup_service.get_question_context(
        weekly_plan_id=plan.id, user_id=user_id
    )

    assert context.child_id == child.id
    assert context.assessment_id == assessment.id
    assert context.weekly_plan_id == plan.id
    assert context.completed_count == context.total_activities == 14
    assert len(context.questions) == 8
    assert all(question.age == 2 for question in context.questions)
    assert all(question.source_file == "KB06.json" for question in context.questions)
    assert all(question.activity_id in question.id for question in context.questions)
    assert all(question.weekly_goal in context.weekly_goals for question in context.questions)
    assert all(not question.fallback_used for question in context.questions)
    assert len(assessment_service.get_questions(assessment)) == 20
    assert {question.id for question in context.questions}.isdisjoint(
        {question.id for question in assessment_service.get_questions(assessment)}
    )


def test_kb06_generic_fallback_is_used_only_without_specific_activity_match(
    kb_repository: KnowledgeBaseRepository,
) -> None:
    known = kb_repository.get_activities_for_age(2)[:5]
    specific = kb_repository.select_weekly_followup_questions(
        age=2, activities=known
    )
    unknown = [
        activity.model_copy(update={"id": f"Z{index:03d}"})
        for index, activity in enumerate(known, start=1)
    ]
    fallback = kb_repository.select_weekly_followup_questions(
        age=2, activities=unknown
    )

    assert all(not question.fallback_used for question in specific)
    assert all(question.fallback_used for question in fallback)
    assert all(
        question.source_record.is_generic_fallback for question in fallback
    )


async def test_submit_rejects_incomplete_invalid_and_duplicate_answers(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id, _child, _assessment, plan = await _create_child_and_plan(
        db_session=db_session,
        assessment_service=assessment_service,
        child_service=child_service,
        weekly_plan_service=weekly_plan_service,
    )
    await _complete_plan(db_session, weekly_plan_service, plan.id)
    context = await followup_service.get_question_context(
        weekly_plan_id=plan.id, user_id=user_id
    )

    incomplete = WeeklyFollowupSubmissionRequest(
        answers=[
            WeeklyFollowupAnswerItem(
                question_id=question.id, response=ResponseValue.ALWAYS
            )
            for question in context.questions[:-1]
        ]
    )
    with pytest.raises(BadRequestError, match="complete KB06"):
        await followup_service.submit(
            weekly_plan_id=plan.id, user_id=user_id, payload=incomplete
        )

    invalid_answers = list(_payload_for_context(context).answers)
    invalid_answers[0] = WeeklyFollowupAnswerItem(
        question_id="not-kb06", response=ResponseValue.ALWAYS
    )
    with pytest.raises(BadRequestError, match="complete KB06"):
        await followup_service.submit(
            weekly_plan_id=plan.id,
            user_id=user_id,
            payload=WeeklyFollowupSubmissionRequest(answers=invalid_answers),
        )

    duplicate_answers = list(_payload_for_context(context).answers)
    duplicate_answers[-1] = duplicate_answers[0]
    with pytest.raises(BadRequestError, match="only once"):
        await followup_service.submit(
            weekly_plan_id=plan.id,
            user_id=user_id,
            payload=WeeklyFollowupSubmissionRequest(answers=duplicate_answers),
        )


async def test_submit_persists_kb06_answers_and_activates_replacement_plan(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id, child, assessment, plan = await _create_child_and_plan(
        db_session=db_session,
        assessment_service=assessment_service,
        child_service=child_service,
        weekly_plan_service=weekly_plan_service,
    )
    await _complete_plan(db_session, weekly_plan_service, plan.id)
    context = await followup_service.get_question_context(
        weekly_plan_id=plan.id, user_id=user_id
    )

    followup = await followup_service.submit(
        weekly_plan_id=plan.id,
        user_id=user_id,
        payload=_payload_for_context(context),
    )
    response = followup_service.build_response(followup)
    replacement = await weekly_plan_service.get_active_owned(
        child_id=child.id, user_id=user_id
    )

    assert response.weekly_plan_id == plan.id
    assert response.previous_assessment_id == assessment.id
    assert response.current_assessment_id is None
    assert response.current_score_percent == 100
    assert response.improvement_percent == 100
    assert followup.question_answers is not None
    assert len(followup.question_answers) == 8
    assert followup.question_context is not None
    assert all(
        question["source_file"] == "KB06.json"
        for question in followup.question_context
    )
    assert replacement.id != plan.id
    assert replacement.assessment_id == assessment.id
    assert replacement.is_active is True
    assert plan.is_active is False


async def test_submit_is_idempotent_and_does_not_replace_plan_twice(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id, child, _assessment, plan = await _create_child_and_plan(
        db_session=db_session,
        assessment_service=assessment_service,
        child_service=child_service,
        weekly_plan_service=weekly_plan_service,
    )
    await _complete_plan(db_session, weekly_plan_service, plan.id)
    context = await followup_service.get_question_context(
        weekly_plan_id=plan.id, user_id=user_id
    )
    payload = _payload_for_context(context)

    first = await followup_service.submit(
        weekly_plan_id=plan.id, user_id=user_id, payload=payload
    )
    first_replacement = await weekly_plan_service.get_active_owned(
        child_id=child.id, user_id=user_id
    )
    second = await followup_service.submit(
        weekly_plan_id=plan.id, user_id=user_id, payload=payload
    )
    second_replacement = await weekly_plan_service.get_active_owned(
        child_id=child.id, user_id=user_id
    )
    stored = await followup_repository.list_for_child(db_session, child.id)

    assert first.id == second.id
    assert first_replacement.id == second_replacement.id
    assert len(stored) == 1


async def test_inactive_or_other_parents_plan_is_rejected(
    assessment_service: AssessmentService,
    followup_service: FollowupService,
    weekly_plan_service: WeeklyPlanService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    user_id, child, assessment, first_plan = await _create_child_and_plan(
        db_session=db_session,
        assessment_service=assessment_service,
        child_service=child_service,
        weekly_plan_service=weekly_plan_service,
    )
    await _complete_plan(db_session, weekly_plan_service, first_plan.id)
    await weekly_plan_service.generate(assessment)

    with pytest.raises(ConflictError, match="no longer"):
        await followup_service.get_question_context(
            weekly_plan_id=first_plan.id, user_id=user_id
        )

    other_user_id = await _make_user(db_session, "other@example.com")
    active = await weekly_plan_service.get_active_owned(
        child_id=child.id, user_id=user_id
    )
    with pytest.raises(NotFoundError):
        await followup_service.get_question_context(
            weekly_plan_id=active.id, user_id=other_user_id
        )
