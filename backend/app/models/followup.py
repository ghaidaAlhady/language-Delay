"""Weekly follow-up / reassessment: compares a new assessment to the child's
previous one and records the resulting progress narrative.

"Follow-up" is implemented as a reassessment using the same KB05 question set
(see docs/DECISIONS_AND_ASSUMPTIONS.md) — no separate follow-up question bank
exists in the supplied knowledge base, so inventing one would violate the
"use only the supplied KB" rule. Progress fields mirror KB04's
تقرير_التقدم (progress report) template.
"""
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
    current_assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    previous_score_percent: Mapped[float] = mapped_column(Float, nullable=False)
    current_score_percent: Mapped[float] = mapped_column(Float, nullable=False)
    improvement_percent: Mapped[float] = mapped_column(Float, nullable=False)
    improved_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    support_needed_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    comment: Mapped[str] = mapped_column(String(2000), nullable=False)
    next_goal: Mapped[str] = mapped_column(String(500), nullable=False)
