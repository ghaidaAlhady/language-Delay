"""Request/response schemas for deterministic KB06 weekly follow-up."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.ai.schemas import FallbackReason, GenerationSource
from app.rag.schemas import Domain
from app.schemas.assessment import ResponseValue


class WeeklyFollowupQuestionResponse(BaseModel):
    id: str
    """The generated/selected question id (`generated_question_id`)."""
    source_question_id: str
    """The KB06 template id this question maps to (`kb06_question_id`)."""
    source_file: str
    weekly_plan_id: str
    age: int
    domain: Domain
    weekly_goal: str
    skill: str
    activity_id: str
    activity_name: str
    expected_behavior: str
    question: str
    """The Arabic wording shown to the parent (`wording_ar`) — deterministic
    KB06 text, or Gemini-varied wording that passed grounding/safety
    validation; scoring only ever depends on `id`/`source_question_id`."""
    response_type: str
    required: bool
    progress_weight: float
    fallback_used: bool
    linked_activity_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    prompt_version: str = "deterministic"


class WeeklyFollowupContextResponse(BaseModel):
    child_id: str
    child_name: str
    weekly_plan_id: str
    assessment_id: str
    generated_at: datetime
    completed_count: int
    total_activities: int
    weekly_goals: list[str]
    questions: list[WeeklyFollowupQuestionResponse] = Field(min_length=5, max_length=8)
    generation_source: GenerationSource = GenerationSource.DETERMINISTIC_FALLBACK
    fallback_reason: FallbackReason | None = None


class WeeklyFollowupAnswerItem(BaseModel):
    question_id: str = Field(min_length=1, max_length=20)
    response: ResponseValue


class WeeklyFollowupSubmissionRequest(BaseModel):
    answers: list[WeeklyFollowupAnswerItem] = Field(min_length=5, max_length=8)


class FollowupResponse(BaseModel):
    id: str
    child_id: str
    previous_assessment_id: str
    current_assessment_id: str | None
    weekly_plan_id: str | None
    previous_score_percent: float
    current_score_percent: float
    improvement_percent: float
    improved_domains: list[Domain]
    support_needed_domains: list[Domain]
    comment: str
    next_goal: str
    created_at: datetime
