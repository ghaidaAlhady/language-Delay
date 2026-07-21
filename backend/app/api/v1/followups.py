"""Weekly follow-up / reassessment endpoints.

A follow-up is completed on top of an already-completed assessment (started
and answered via the normal /assessments flow) — see
app/services/followup_service.py for why "follow-up" reuses the KB05
assessment question set rather than a separate question bank.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import (
    get_assessment_service,
    get_child_service,
    get_current_user,
    get_followup_service,
)
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.followup import FollowupResponse
from app.services.assessment_service import AssessmentService
from app.services.child_service import ChildService
from app.services.followup_service import FollowupService

router = APIRouter(tags=["followups"])


@router.post(
    "/assessments/{assessment_id}/followup",
    response_model=FollowupResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def complete_followup(
    request: Request,
    assessment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
    followup_service: Annotated[FollowupService, Depends(get_followup_service)],
) -> FollowupResponse:
    assessment = await assessment_service.get_owned(
        assessment_id=assessment_id, user_id=current_user.id
    )
    followup = await followup_service.complete_followup(assessment)
    return followup_service.build_response(followup)


@router.get("/children/{child_id}/followups", response_model=list[FollowupResponse])
async def list_followups(
    child_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    child_service: Annotated[ChildService, Depends(get_child_service)],
    followup_service: Annotated[FollowupService, Depends(get_followup_service)],
) -> list[FollowupResponse]:
    child = await child_service.get_owned(child_id=child_id, user_id=current_user.id)
    followups = await followup_service.list_for_child(child.id)
    return [followup_service.build_response(f) for f in followups]


@router.get("/followups/{followup_id}", response_model=FollowupResponse)
async def get_followup(
    followup_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    followup_service: Annotated[FollowupService, Depends(get_followup_service)],
) -> FollowupResponse:
    followup = await followup_service.get_owned(followup_id=followup_id, user_id=current_user.id)
    return followup_service.build_response(followup)
