"""Weekly plan endpoints: generation, retrieval, completion, adherence,
and alternative-activity suggestion — all ownership-scoped.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.ai.activity_explanation import ActivityExplanationOrchestrator
from app.ai.schemas import ActivityExplanationResponse
from app.api.deps import (
    get_activity_explanation_orchestrator,
    get_assessment_service,
    get_current_user,
    get_kb_repository,
    get_weekly_plan_service,
)
from app.core.rate_limit import limiter
from app.models.user import User
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.schemas.weekly_plan import ActivityCompletionRequest, WeeklyPlanResponse
from app.services.assessment_service import AssessmentService
from app.services.weekly_plan_service import WeeklyPlanService

router = APIRouter(tags=["weekly-plan"])


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unavailable")


@router.post(
    "/assessments/{assessment_id}/weekly-plan",
    response_model=WeeklyPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("20/minute")
async def generate_weekly_plan(
    request: Request,
    assessment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
    weekly_plan_service: Annotated[WeeklyPlanService, Depends(get_weekly_plan_service)],
) -> WeeklyPlanResponse:
    assessment = await assessment_service.get_owned(
        assessment_id=assessment_id, user_id=current_user.id
    )
    plan = await weekly_plan_service.generate(assessment)
    return await weekly_plan_service.build_response(plan)


@router.get("/children/{child_id}/weekly-plan", response_model=WeeklyPlanResponse)
async def get_active_weekly_plan(
    child_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    weekly_plan_service: Annotated[WeeklyPlanService, Depends(get_weekly_plan_service)],
) -> WeeklyPlanResponse:
    plan = await weekly_plan_service.get_active_owned(child_id=child_id, user_id=current_user.id)
    return await weekly_plan_service.build_response(plan)


@router.patch("/weekly-plan-activities/{activity_slot_id}", response_model=WeeklyPlanResponse)
async def set_activity_completion(
    activity_slot_id: str,
    payload: ActivityCompletionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    weekly_plan_service: Annotated[WeeklyPlanService, Depends(get_weekly_plan_service)],
) -> WeeklyPlanResponse:
    slot = await weekly_plan_service.get_owned_activity_slot(
        slot_id=activity_slot_id, user_id=current_user.id
    )
    slot = await weekly_plan_service.set_completion(slot, completed=payload.completed)
    plan = await weekly_plan_service.get_by_id(slot.weekly_plan_id)
    return await weekly_plan_service.build_response(plan)


@router.post(
    "/weekly-plan-activities/{activity_slot_id}/alternative",
    response_model=WeeklyPlanResponse,
)
async def get_alternative_activity(
    activity_slot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    weekly_plan_service: Annotated[WeeklyPlanService, Depends(get_weekly_plan_service)],
) -> WeeklyPlanResponse:
    slot = await weekly_plan_service.get_owned_activity_slot(
        slot_id=activity_slot_id, user_id=current_user.id
    )
    slot = await weekly_plan_service.suggest_alternative(slot)
    plan = await weekly_plan_service.get_by_id(slot.weekly_plan_id)
    return await weekly_plan_service.build_response(plan)


@router.post(
    "/weekly-plan-activities/{activity_slot_id}/ai-explanation",
    response_model=ActivityExplanationResponse,
)
@limiter.limit("20/minute")
async def get_activity_ai_explanation(
    request: Request,
    activity_slot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    weekly_plan_service: Annotated[WeeklyPlanService, Depends(get_weekly_plan_service)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
    orchestrator: Annotated[
        ActivityExplanationOrchestrator, Depends(get_activity_explanation_orchestrator)
    ],
) -> ActivityExplanationResponse:
    # Ownership is fully resolved (slot -> plan -> child -> user) before the
    # KB02 activity is even looked up, let alone before any provider call —
    # the same "ownership masked as 404, before provider call" contract the
    # Milestone 2 AI endpoints already use.
    slot = await weekly_plan_service.get_owned_activity_slot(
        slot_id=activity_slot_id, user_id=current_user.id
    )
    activity = kb.get_activity(slot.activity_id)
    return await orchestrator.generate(
        activity=activity, correlation_id=_correlation_id(request)
    )
