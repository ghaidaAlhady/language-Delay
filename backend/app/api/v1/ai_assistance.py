"""Optional, ownership-scoped AI-assisted wording endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.ai.orchestration import AIAssistanceService
from app.ai.schemas import AssistanceResponse
from app.api.deps import get_ai_assistance_service, get_current_user
from app.core.rate_limit import limiter
from app.models.user import User

router = APIRouter(tags=["ai-assistance"])


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unavailable")


@router.post(
    "/assessments/{assessment_id}/ai-explanation",
    response_model=AssistanceResponse,
)
@limiter.limit("20/minute")
async def create_assessment_explanation(
    request: Request,
    assessment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        AIAssistanceService, Depends(get_ai_assistance_service)
    ],
) -> AssistanceResponse:
    return await service.assessment_explanation(
        assessment_id=assessment_id,
        user_id=current_user.id,
        correlation_id=_correlation_id(request),
    )


@router.post(
    "/weekly-plans/{weekly_plan_id}/ai-summary",
    response_model=AssistanceResponse,
)
@limiter.limit("20/minute")
async def create_weekly_plan_summary(
    request: Request,
    weekly_plan_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        AIAssistanceService, Depends(get_ai_assistance_service)
    ],
) -> AssistanceResponse:
    return await service.weekly_plan_summary(
        weekly_plan_id=weekly_plan_id,
        user_id=current_user.id,
        correlation_id=_correlation_id(request),
    )


@router.post(
    "/followups/{followup_id}/ai-summary",
    response_model=AssistanceResponse,
)
@limiter.limit("20/minute")
async def create_followup_summary(
    request: Request,
    followup_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[
        AIAssistanceService, Depends(get_ai_assistance_service)
    ],
) -> AssistanceResponse:
    return await service.followup_summary(
        followup_id=followup_id,
        user_id=current_user.id,
        correlation_id=_correlation_id(request),
    )

