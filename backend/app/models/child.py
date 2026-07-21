"""Child profile model."""
from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Child(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "children"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    home_language: Mapped[str] = mapped_column(String(50), nullable=False)
    has_previous_diagnosis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    previous_diagnosis_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    has_hearing_problems: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uses_hearing_aid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
