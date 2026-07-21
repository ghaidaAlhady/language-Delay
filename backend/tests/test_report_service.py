from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError, NotFoundError
from app.repositories import user_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import AnswerItem, AnswerSubmissionRequest, ResponseValue
from app.schemas.child import ChildCreateRequest, Gender
from app.services.assessment_service import AssessmentService
from app.services.child_service import ChildService
from app.services.report_service import ReportService


@pytest.fixture
def assessment_service(
    db_session: AsyncSession, kb_repository: KnowledgeBaseRepository
) -> AssessmentService:
    return AssessmentService(session=db_session, kb=kb_repository)


@pytest.fixture
def report_service(
    db_session: AsyncSession, kb_repository: KnowledgeBaseRepository
) -> ReportService:
    return ReportService(session=db_session, kb=kb_repository)


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
    response: ResponseValue = ResponseValue.ALWAYS,
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
    report_service: ReportService,
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
        await report_service.generate(assessment)


async def test_generate_produces_report_with_expected_content(
    assessment_service: AssessmentService,
    report_service: ReportService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    _user_id, child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session
    )

    report = await report_service.generate(assessment)
    response = await report_service.build_response(report)

    assert response.report_number.startswith("REP-")
    assert response.child_id == child.id
    assert response.overall_severity.value == "طبيعي"
    assert response.referral_recommended is False
    assert response.summary_text
    assert response.weekly_goal
    assert response.next_reassessment
    assert response.disclaimer
    assert len(response.domain_summaries) == 4
    assert response.recommended_activity_ids


async def test_generate_is_idempotent(
    assessment_service: AssessmentService,
    report_service: ReportService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    _user_id, _child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session
    )

    first = await report_service.generate(assessment)
    second = await report_service.generate(assessment)
    assert first.id == second.id


async def test_referral_recommended_when_severity_notable(
    assessment_service: AssessmentService,
    report_service: ReportService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    _user_id, _child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session, response=ResponseValue.NEVER
    )

    report = await report_service.generate(assessment)
    response = await report_service.build_response(report)
    assert response.overall_severity.value == "تأخر ملحوظ"
    assert response.referral_recommended is True


async def test_get_owned_hides_other_users_report(
    assessment_service: AssessmentService,
    report_service: ReportService,
    child_service: ChildService,
    db_session: AsyncSession,
) -> None:
    _user_id, _child, assessment = await _completed_assessment(
        assessment_service, child_service, db_session
    )
    report = await report_service.generate(assessment)

    other_user_id = await _make_user(db_session, email="other@example.com")
    with pytest.raises(NotFoundError):
        await report_service.get_owned(report_id=report.id, user_id=other_user_id)
