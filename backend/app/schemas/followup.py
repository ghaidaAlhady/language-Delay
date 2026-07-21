"""Request/response schemas for weekly follow-up / reassessment."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.rag.schemas import Domain


class FollowupResponse(BaseModel):
    id: str
    child_id: str
    previous_assessment_id: str
    current_assessment_id: str
    previous_score_percent: float
    current_score_percent: float
    improvement_percent: float
    improved_domains: list[Domain]
    support_needed_domains: list[Domain]
    comment: str
    next_goal: str
    created_at: datetime
