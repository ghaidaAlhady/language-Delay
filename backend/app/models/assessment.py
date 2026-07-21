"""Assessment, per-question answers, and per-domain results.

An assessment's per-domain results are persisted as a snapshot at completion
time (score, severity, referral, the KB03 rule ID, and its recommendation
text) rather than recomputed from the knowledge base on every read. This
keeps historical assessments stable and auditable even if the knowledge base
is later updated — a parent's report must never silently change after the
fact.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin


class Assessment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessments"

    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    age_at_assessment: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    overall_severity: Mapped[str | None] = mapped_column(String(30), nullable=True)
    overall_referral: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)


class AssessmentAnswer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_answers"
    __table_args__ = (UniqueConstraint("assessment_id", "question_id"),)

    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[str] = mapped_column(String(20), nullable=False)
    response: Mapped[str] = mapped_column(String(20), nullable=False)
    score_weight: Mapped[float] = mapped_column(Float, nullable=False)


class AssessmentDomainResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assessment_domain_results"
    __table_args__ = (UniqueConstraint("assessment_id", "domain"),)

    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    score_percent: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    referral: Mapped[str] = mapped_column(String(30), nullable=False)
    decision_rule_id: Mapped[str] = mapped_column(String(20), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(1000), nullable=False)
    follow_up: Mapped[str] = mapped_column(String(255), nullable=False)
    suggested_activity_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
