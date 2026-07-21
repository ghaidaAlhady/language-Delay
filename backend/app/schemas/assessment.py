"""Request/response schemas for assessments."""
from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.rag.schemas import Domain, ReferralGuidance, Severity


class ResponseValue(StrEnum):
    """The approved 5-point response scale (PROJECT_SPEC.md).

    KB05 only defines a binary Yes/No score per question. Each level here
    maps deterministically onto that question's own yes/no bounds rather
    than inventing new per-level scores: Always/Often -> full credit,
    Sometimes -> half credit, Rarely/Never -> no credit. See
    docs/DECISIONS_AND_ASSUMPTIONS.md.
    """

    ALWAYS = "always"
    OFTEN = "often"
    SOMETIMES = "sometimes"
    RARELY = "rarely"
    NEVER = "never"


RESPONSE_WEIGHTS: dict[ResponseValue, float] = {
    ResponseValue.ALWAYS: 1.0,
    ResponseValue.OFTEN: 1.0,
    ResponseValue.SOMETIMES: 0.5,
    ResponseValue.RARELY: 0.0,
    ResponseValue.NEVER: 0.0,
}


class AssessmentStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AssessmentQuestionResponse(BaseModel):
    id: str
    age: int
    domain: Domain
    question: str
    linked_milestone_id: str


class AnswerItem(BaseModel):
    question_id: str = Field(min_length=1, max_length=20)
    response: ResponseValue


class AnswerSubmissionRequest(BaseModel):
    answers: list[AnswerItem] = Field(min_length=1)


class AssessmentDomainResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    domain: Domain
    score_percent: float
    severity: Severity
    referral: ReferralGuidance
    decision_rule_id: str
    recommendation: str
    follow_up: str
    suggested_activity_ids: list[str]


class AssessmentResponse(BaseModel):
    id: str
    child_id: str
    age_at_assessment: int
    status: AssessmentStatus
    started_at: datetime
    completed_at: datetime | None
    answered_count: int
    total_questions: int
    overall_severity: Severity | None
    overall_referral: ReferralGuidance | None
    confidence_score: float | None
    priority_domains: list[Domain]
    strengths: list[str]
    support_needs: list[str]
    domain_results: list[AssessmentDomainResultResponse]
