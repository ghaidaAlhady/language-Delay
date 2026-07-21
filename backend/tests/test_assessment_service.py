from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, ConflictError, NotFoundError
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AnswerItem, AnswerSubmissionRequest, ResponseValue
from app.schemas.child import ChildCreateRequest, Gender
from app.services.assessment_service import AssessmentService
from app.services.child_service import ChildService


@pytest.fixture
def assessment_service(
    db_session: AsyncSession, kb_repository: KnowledgeBaseRepository
) -> AssessmentService:
    return AssessmentService(session=db_session, kb=kb_repository)


@pytest.fixture
def child_service(db_session: AsyncSession) -> ChildService:
    return ChildService(session=db_session)


def _age_n_dob(age: int) -> date:
    today = date.today()
    return date(today.year - age, today.month, min(today.day, 28))


async def _make_child(child_service: ChildService, user_id: str, age: int = 3) -> str:
    child = await child_service.create(
        user_id=user_id,
        payload=ChildCreateRequest(
            name="Layla",
            date_of_birth=_age_n_dob(age),
            gender=Gender.FEMALE,
            home_language="ar",
        ),
    )
    return child.id


async def _make_user(db_session: AsyncSession) -> str:
    from app.repositories import user_repository

    user = await user_repository.create(
        db_session, email="parent@example.com", hashed_password="x", display_name="P"
    )
    await db_session.commit()
    return user.id


async def test_start_creates_in_progress_assessment_with_locked_age(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    child_id = await _make_child(child_service, user_id, age=3)
    child = await child_service.get_owned(child_id=child_id, user_id=user_id)

    assessment = await assessment_service.start(child)
    assert assessment.status == "in_progress"
    assert assessment.age_at_assessment == 3


async def test_start_rejects_child_outside_supported_age_range(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    child_id = await _make_child(child_service, user_id, age=6)
    child = await child_service.get_owned(child_id=child_id, user_id=user_id)

    with pytest.raises(BadRequestError):
        await assessment_service.start(child)


async def test_get_owned_hides_other_users_assessment(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    from app.repositories import user_repository

    owner_id = await _make_user(db_session)
    child_id = await _make_child(child_service, owner_id, age=3)
    child = await child_service.get_owned(child_id=child_id, user_id=owner_id)
    assessment = await assessment_service.start(child)

    other_user = await user_repository.create(
        db_session, email="other@example.com", hashed_password="x", display_name="O"
    )
    await db_session.commit()

    with pytest.raises(NotFoundError):
        await assessment_service.get_owned(assessment_id=assessment.id, user_id=other_user.id)


async def test_submit_answers_rejects_unknown_question_id(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    child_id = await _make_child(child_service, user_id, age=3)
    child = await child_service.get_owned(child_id=child_id, user_id=user_id)
    assessment = await assessment_service.start(child)

    with pytest.raises(BadRequestError):
        await assessment_service.submit_answers(
            assessment,
            AnswerSubmissionRequest(
                answers=[AnswerItem(question_id="Q999", response=ResponseValue.ALWAYS)]
            ),
        )


async def test_submit_answers_upserts_same_question(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    child_id = await _make_child(child_service, user_id, age=2)
    child = await child_service.get_owned(child_id=child_id, user_id=user_id)
    assessment = await assessment_service.start(child)
    question_id = assessment_service.get_questions(assessment)[0].id

    await assessment_service.submit_answers(
        assessment,
        AnswerSubmissionRequest(
            answers=[AnswerItem(question_id=question_id, response=ResponseValue.NEVER)]
        ),
    )
    await assessment_service.submit_answers(
        assessment,
        AnswerSubmissionRequest(
            answers=[AnswerItem(question_id=question_id, response=ResponseValue.ALWAYS)]
        ),
    )

    response = await assessment_service.build_response(assessment)
    assert response.answered_count == 1


async def test_complete_requires_all_questions_answered(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    child_id = await _make_child(child_service, user_id, age=2)
    child = await child_service.get_owned(child_id=child_id, user_id=user_id)
    assessment = await assessment_service.start(child)

    with pytest.raises(BadRequestError):
        await assessment_service.complete(assessment)


async def test_complete_scores_and_persists_results(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    child_id = await _make_child(child_service, user_id, age=2)
    child = await child_service.get_owned(child_id=child_id, user_id=user_id)
    assessment = await assessment_service.start(child)

    questions = assessment_service.get_questions(assessment)
    await assessment_service.submit_answers(
        assessment,
        AnswerSubmissionRequest(
            answers=[
                AnswerItem(question_id=q.id, response=ResponseValue.ALWAYS) for q in questions
            ]
        ),
    )

    completed = await assessment_service.complete(assessment)
    assert completed.status == "completed"
    assert completed.overall_severity == "طبيعي"
    assert completed.confidence_score is not None

    response = await assessment_service.build_response(completed)
    assert len(response.domain_results) == 4
    assert all(r.score_percent == 100.0 for r in response.domain_results)


async def test_complete_twice_raises_conflict(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    child_id = await _make_child(child_service, user_id, age=2)
    child = await child_service.get_owned(child_id=child_id, user_id=user_id)
    assessment = await assessment_service.start(child)

    questions = assessment_service.get_questions(assessment)
    await assessment_service.submit_answers(
        assessment,
        AnswerSubmissionRequest(
            answers=[
                AnswerItem(question_id=q.id, response=ResponseValue.ALWAYS) for q in questions
            ]
        ),
    )
    await assessment_service.complete(assessment)

    with pytest.raises(ConflictError):
        await assessment_service.complete(assessment)


async def test_submit_answers_after_completion_raises_conflict(
    assessment_service: AssessmentService, child_service: ChildService, db_session: AsyncSession
) -> None:
    user_id = await _make_user(db_session)
    child_id = await _make_child(child_service, user_id, age=2)
    child = await child_service.get_owned(child_id=child_id, user_id=user_id)
    assessment = await assessment_service.start(child)

    questions = assessment_service.get_questions(assessment)
    await assessment_service.submit_answers(
        assessment,
        AnswerSubmissionRequest(
            answers=[
                AnswerItem(question_id=q.id, response=ResponseValue.ALWAYS) for q in questions
            ]
        ),
    )
    await assessment_service.complete(assessment)

    with pytest.raises(ConflictError):
        await assessment_service.submit_answers(
            assessment,
            AnswerSubmissionRequest(
                answers=[AnswerItem(question_id=questions[0].id, response=ResponseValue.NEVER)]
            ),
        )
