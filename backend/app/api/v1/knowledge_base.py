"""Direct, traceable knowledge-base retrieval: activities and source
references. Every record returned here is a real KB02/KB01 row.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_assessment_service, get_current_user, get_kb_repository
from app.models.user import User
from app.rag.schemas import ActivityRecord, Domain, ReferenceRecord
from app.repositories.knowledge_base_repository import KnowledgeBaseRepository
from app.services.age_service import MAX_ASSESSMENT_AGE, MIN_ASSESSMENT_AGE
from app.services.assessment_service import AssessmentService

router = APIRouter(tags=["knowledge-base"])


@router.get("/activities", response_model=list[ActivityRecord])
async def list_activities(
    _current_user: Annotated[User, Depends(get_current_user)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
    age: Annotated[int, Query(ge=MIN_ASSESSMENT_AGE, le=MAX_ASSESSMENT_AGE)],
    domain: Annotated[Domain | None, Query()] = None,
) -> list[ActivityRecord]:
    return kb.get_activities_for_age(age, domain)


@router.get("/assessments/{assessment_id}/activities", response_model=list[ActivityRecord])
async def get_assessment_activities(
    assessment_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    assessment_service: Annotated[AssessmentService, Depends(get_assessment_service)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
) -> list[ActivityRecord]:
    assessment = await assessment_service.get_owned(
        assessment_id=assessment_id, user_id=current_user.id
    )
    activity_ids = await assessment_service.get_recommended_activity_ids(assessment)
    return kb.get_activities_by_ids(activity_ids)


@router.get("/references", response_model=list[ReferenceRecord])
async def list_references(
    _current_user: Annotated[User, Depends(get_current_user)],
    kb: Annotated[KnowledgeBaseRepository, Depends(get_kb_repository)],
) -> list[ReferenceRecord]:
    return kb.references
