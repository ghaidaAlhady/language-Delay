"""Aggregates all versioned API routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    ai_assistance,
    assessments,
    auth,
    children,
    followups,
    health,
    knowledge_base,
    reports,
    weekly_plans,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ai_assistance.router)
api_router.include_router(auth.router)
api_router.include_router(children.router)
api_router.include_router(assessments.router)
api_router.include_router(reports.router)
api_router.include_router(knowledge_base.router)
api_router.include_router(weekly_plans.router)
api_router.include_router(followups.router)
