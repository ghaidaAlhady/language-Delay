"""Persisted weekly-plan follow-up and deterministic KB06 answer snapshot."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Followup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "followups"

    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    previous_assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    current_assessment_id: Mapped[str | None] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=True
    )
    weekly_plan_id: Mapped[str | None] = mapped_column(
        ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    previous_score_percent: Mapped[float] = mapped_column(Float, nullable=False)
    current_score_percent: Mapped[float] = mapped_column(Float, nullable=False)
    improvement_percent: Mapped[float] = mapped_column(Float, nullable=False)
    improved_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    support_needed_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    comment: Mapped[str] = mapped_column(String(2000), nullable=False)
    next_goal: Mapped[str] = mapped_column(String(500), nullable=False)
    question_answers: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    question_context: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
