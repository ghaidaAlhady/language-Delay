"""Request/response schemas for generated reports."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.rag.schemas import Domain, ReferralGuidance, Severity


class ReportDomainSummary(BaseModel):
    domain: Domain
    score_percent: float
    severity: Severity
    recommendation: str


class ReportResponse(BaseModel):
    id: str
    report_number: str
    language: str
    child_id: str
    child_name: str
    child_age_years: int
    assessment_id: str
    generated_at: datetime
    overall_severity: Severity
    overall_referral: ReferralGuidance
    referral_recommended: bool
    confidence_score: float
    domain_summaries: list[ReportDomainSummary]
    strengths: list[str]
    support_needs: list[str]
    summary_text: str
    weekly_goal: str
    recommended_activity_ids: list[str]
    next_reassessment: str
    disclaimer: str
