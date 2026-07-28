"""Ownership-scoped deterministic weekly-plan follow-up endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.api.deps import get_child_service, get_current_user, get_followup_service
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.followup import (
    FollowupResponse,
    WeeklyFollowupContextResponse,
    WeeklyFollowupSubmissionRequest,
)
from app.services.child_service import ChildService
from app.services.followup_service import FollowupService

router = APIRouter(tags=["followups"])


@router.get(
    "/weekly-plans/{weekly_plan_id}/followup-questions",
    response_model=WeeklyFollowupContextResponse,
)
async def get_weekly_followup_questions(
    weekly_plan_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    followup_service: Annotated[FollowupService, Depends(get_followup_service)],
) -> WeeklyFollowupContextResponse:
    return await followup_service.get_question_context(
        weekly_plan_id=weekly_plan_id, user_id=current_user.id
    )


@router.post(
    "/weekly-plans/{weekly_plan_id}/followup",
    response_model=FollowupResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def submit_weekly_followup(
    request: Request,
    weekly_plan_id: str,
    payload: WeeklyFollowupSubmissionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    followup_service: Annotated[FollowupService, Depends(get_followup_service)],
) -> FollowupResponse:
    followup = await followup_service.submit(
        weekly_plan_id=weekly_plan_id,
        user_id=current_user.id,
        payload=payload,
    )
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
    return [followup_service.build_response(followup) for followup in followups]


@router.get("/followups/{followup_id}", response_model=FollowupResponse)
async def get_followup(
    followup_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    followup_service: Annotated[FollowupService, Depends(get_followup_service)],
) -> FollowupResponse:
    followup = await followup_service.get_owned(
        followup_id=followup_id, user_id=current_user.id
    )
    return followup_service.build_response(followup)
