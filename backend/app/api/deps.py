"""Shared FastAPI dependencies."""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestration import AIAssistanceService
from app.ai.protocols import AIProvider
from app.core.config import Settings, get_settings
from app.core.database import get_db as _get_db
from app.core.errors import UnauthorizedError
from app.models.user import User
from app.repositories import user_repository
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.security.tokens import decode_access_token
from app.services.assessment_service import AssessmentService
from app.services.auth_service import AuthService
from app.services.child_service import ChildService
from app.services.followup_service import FollowupService
from app.services.report_service import ReportService
from app.services.weekly_plan_service import WeeklyPlanService

DbSession = AsyncSession

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async for session in _get_db():
        yield session


def get_kb_repository(request: Request) -> KnowledgeBaseRepository:
    return request.app.state.kb_repository


def get_ai_provider(request: Request) -> AIProvider:
    return request.app.state.ai_provider


def get_settings_dep() -> Settings:
    return get_settings()


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> AuthService:
    return AuthService(session=session, settings=settings)


def get_child_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ChildService:
    return ChildService(session=session)


def get_assessment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
) -> AssessmentService:
    return AssessmentService(session=session, kb=kb)


def get_report_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
) -> ReportService:
    return ReportService(session=session, kb=kb)


def get_weekly_plan_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
) -> WeeklyPlanService:
    return WeeklyPlanService(session=session, kb=kb)


def get_followup_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
) -> FollowupService:
    return FollowupService(session=session, kb=kb)


def get_ai_assistance_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
    provider: Annotated[AIProvider, Depends(get_ai_provider)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> AIAssistanceService:
    return AIAssistanceService(
        session=session,
        kb=kb,
        provider=provider,
        settings=settings,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token.")

    user_id = decode_access_token(credentials.credentials, settings)
    user = await user_repository.get_by_id(session, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid or expired access token.")
    return user
