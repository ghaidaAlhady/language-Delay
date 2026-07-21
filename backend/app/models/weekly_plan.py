"""Weekly home-activity plan: exactly 7 days x 2 activities.

Per the approved product spec, only the latest weekly plan is ever "active"
for a child (unlike assessments/reports, which are always kept in full).
Generating a new plan deactivates the previous one rather than deleting it,
so history remains available for audit while "current plan" queries only
ever see one row.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin


class WeeklyPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "weekly_plans"

    child_id: Mapped[str] = mapped_column(
        ForeignKey("children.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WeeklyPlanActivity(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "weekly_plan_activities"
    __table_args__ = (UniqueConstraint("weekly_plan_id", "day", "slot_order"),)

    weekly_plan_id: Mapped[str] = mapped_column(
        ForeignKey("weekly_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day: Mapped[str] = mapped_column(String(20), nullable=False)
    slot_order: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_id: Mapped[str] = mapped_column(String(20), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
