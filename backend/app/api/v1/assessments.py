"""Assessment endpoints: start, questions, answer submission, completion,
and result/history retrieval — all scoped to the authenticated parent.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.api.deps import (
    get_assessment_service,
    get_child_service,
    get_current_user,
    get_kb_repository,
)
from app.core.rate_limit import limiter
from app.models.user import User
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.assessment import (
    AnswerSubmissionRequest,
    AssessmentQuestionResponse,
    AssessmentResponse,
)
from app.services.age_service import MAX_ASSESSMENT_AGE, MIN_ASSESSMENT_AGE
from app.services.assessment_service import AssessmentService
from app.services.child_service import ChildService

router = APIRouter(tags=["assessments"])


@router.get("/assessment-questions", response_model=list[AssessmentQuestionResponse])
async def get_assessment_questions_by_age(
    age: Annotated[int, Query(ge=MIN_ASSESSMENT_AGE, le=MAX_ASSESSMENT_AGE)],
    _current_user: Annotated[User, Depends(get_current_user)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
) -> list[AssessmentQuestionResponse]:
    questions = kb.get_questions_for_age(age)
    return [
        AssessmentQuestionResponse(
            id=q.id,
            age=q.age,
            domain=q.domain,
            question=q.question,
            linked_milestone_id=q.linked_milestone_id,
        )
        for q in questions
    ]


@router.post(
    "/children/{child_id}/assessments",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_assessment(
    child_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AssessmentResponse:
    child = await child_service.get_owned(child_id=child_id, user_id=current_user.id)
    assessment = await assessment_service.start(child)
    return await assessment_service.build_response(assessment)


@router.get("/children/{child_id}/assessments", response_model=list[AssessmentResponse])
async def list_assessments(
    child_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> list[AssessmentResponse]:
    child = await child_service.get_owned(child_id=child_id, user_id=current_user.id)
    assessments = await assessment_service.list_for_child(child.id)
    return [await assessment_service.build_response(a) for a in assessments]


@router.get("/assessments/{assessment_id}", response_model=AssessmentResponse)
async def get_assessment(
    assessment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AssessmentResponse:
    assessment = await assessment_service.get_owned(
        assessment_id=assessment_id, user_id=current_user.id
    )
    return await assessment_service.build_response(assessment)


@router.get(
    "/assessments/{assessment_id}/questions",
    response_model=list[AssessmentQuestionResponse],
)
async def get_assessment_questions(
    assessment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> list[AssessmentQuestionResponse]:
    assessment = await assessment_service.get_owned(
        assessment_id=assessment_id, user_id=current_user.id
    )
    questions = assessment_service.get_questions(assessment)
    return [
        AssessmentQuestionResponse(
            id=q.id,
            age=q.age,
            domain=q.domain,
            question=q.question,
            linked_milestone_id=q.linked_milestone_id,
        )
        for q in questions
    ]


@router.post("/assessments/{assessment_id}/answers", response_model=AssessmentResponse)
async def submit_answers(
    assessment_id: str,
    payload: AnswerSubmissionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AssessmentResponse:
    assessment = await assessment_service.get_owned(
        assessment_id=assessment_id, user_id=current_user.id
    )
    assessment = await assessment_service.submit_answers(assessment, payload)
    return await assessment_service.build_response(assessment)


@router.post("/assessments/{assessment_id}/complete", response_model=AssessmentResponse)
@limiter.limit("20/minute")
async def complete_assessment(
    request: Request,
    assessment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
) -> AssessmentResponse:
    assessment = await assessment_service.get_owned(
        assessment_id=assessment_id, user_id=current_user.id
    )
    assessment = await assessment_service.complete(assessment)
    return await assessment_service.build_response(assessment)
