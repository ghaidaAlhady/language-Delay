"""Request/response schemas for the weekly home-activity plan."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.rag.schemas import ActivityRecord


class WeeklyPlanActivityResponse(BaseModel):
    id: str
    day: str
    slot_order: int
    completed: bool
    completed_at: datetime | None
    activity: ActivityRecord


class WeeklyPlanResponse(BaseModel):
    id: str
    child_id: str
    assessment_id: str
    is_active: bool
    generated_at: datetime
    total_activities: int
    completed_count: int
    adherence_percent: float
    activities: list[WeeklyPlanActivityResponse]


class ActivityCompletionRequest(BaseModel):
    completed: bool
