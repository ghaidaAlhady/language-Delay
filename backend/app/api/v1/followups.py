"""Ownership-scoped deterministic weekly-plan follow-up endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from app.ai.followup_questions import FollowupQuestionOrchestrator
from app.api.deps import (
    get_child_service,
    get_current_user,
    get_followup_question_orchestrator,
    get_followup_service,
)
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


def _correlation_id(request: Request) -> str:
    return getattr(request.state, "correlation_id", "unavailable")


async def _build_ai_varied_context(
    *,
    weekly_plan_id: str,
    user_id: str,
    followup_service: FollowupService,
    orchestrator: FollowupQuestionOrchestrator,
    correlation_id: str,
) -> WeeklyFollowupContextResponse:
    """Deterministic candidates -> optional AI wording/selection -> database-
    frozen result. Both GET and POST therefore validate against the exact set
    the parent saw, even after a deploy, restart, or another worker handles
    the next request."""
    deterministic = await followup_service.get_question_context(
        weekly_plan_id=weekly_plan_id, user_id=user_id
    )

    frozen = await followup_service.get_frozen_question_set(
        weekly_plan_id=weekly_plan_id, user_id=user_id
    )
    if frozen is not None:
        questions, generation_source, fallback_reason = frozen
        return deterministic.model_copy(
            update={
                "questions": questions,
                "generation_source": generation_source,
                "fallback_reason": fallback_reason,
            }
        )

    result = await orchestrator.generate(
        weekly_plan_id=deterministic.weekly_plan_id,
        candidates=deterministic.questions,
        correlation_id=correlation_id,
    )
    questions, generation_source, fallback_reason = (
        await followup_service.freeze_question_set(
            weekly_plan_id=weekly_plan_id,
            user_id=user_id,
            questions=result.questions,
            generation_source=result.generation_source,
            fallback_reason=result.fallback_reason,
        )
    )
    return deterministic.model_copy(
        update={
            "questions": questions,
            "generation_source": generation_source,
            "fallback_reason": fallback_reason,
        }
    )


@router.get(
    "/weekly-plans/{weekly_plan_id}/followup-questions",
    response_model=WeeklyFollowupContextResponse,
)
async def get_weekly_followup_questions(
    request: Request,
    weekly_plan_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    followup_service: Annotated[FollowupService, Depends(get_followup_service)],
    orchestrator: Annotated[
        FollowupQuestionOrchestrator, Depends(get_followup_question_orchestrator)
    ],
) -> WeeklyFollowupContextResponse:
    return await _build_ai_varied_context(
        weekly_plan_id=weekly_plan_id,
        user_id=current_user.id,
        followup_service=followup_service,
        orchestrator=orchestrator,
        correlation_id=_correlation_id(request),
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
    orchestrator: Annotated[
        FollowupQuestionOrchestrator, Depends(get_followup_question_orchestrator)
    ],
) -> FollowupResponse:
    # Idempotency must be checked *before* building an AI-varied question
    # context: submitting always deactivates/replaces the weekly plan, so a
    # duplicate submission's plan is no longer active, and building context
    # would incorrectly reject it as "not ready" instead of returning the
    # existing follow-up.
    existing = await followup_service.get_existing_for_plan(
        weekly_plan_id=weekly_plan_id, user_id=current_user.id
    )
    if existing is not None:
        return followup_service.build_response(existing)

    shown_context = await _build_ai_varied_context(
        weekly_plan_id=weekly_plan_id,
        user_id=current_user.id,
        followup_service=followup_service,
        orchestrator=orchestrator,
        correlation_id=_correlation_id(request),
    )
    followup = await followup_service.submit(
        weekly_plan_id=weekly_plan_id,
        user_id=current_user.id,
        payload=payload,
        expected_questions=shown_context.questions,
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
