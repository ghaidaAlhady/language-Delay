"""Generated assessment report.

The report's own narrative metadata (report number, weekly-goal text,
reassessment interval) is persisted here. The scored data it describes
(domain results, strengths, support needs, confidence) is not duplicated —
it is read through the report's one-to-one assessment, keeping a single
source of truth for anything audit-relevant.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    assessment_id: Mapped[str] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    report_number: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="ar")
    summary_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    weekly_goal: Mapped[str] = mapped_column(String(500), nullable=False)
    next_reassessment: Mapped[str] = mapped_column(String(255), nullable=False)
