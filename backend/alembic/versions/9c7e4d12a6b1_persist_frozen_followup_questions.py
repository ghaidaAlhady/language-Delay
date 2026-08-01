"""persist frozen follow-up question sets on weekly plans

Revision ID: 9c7e4d12a6b1
Revises: 5f31d8aee912
Create Date: 2026-08-01 04:58:00
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.core.database import UTCDateTime

revision: str = "9c7e4d12a6b1"
down_revision: str | Sequence[str] | None = "5f31d8aee912"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("weekly_plans") as batch_op:
        batch_op.add_column(
            sa.Column("followup_question_context", sa.JSON(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("followup_generation_source", sa.String(length=40), nullable=True)
        )
        batch_op.add_column(
            sa.Column("followup_fallback_reason", sa.String(length=40), nullable=True)
        )
        batch_op.add_column(
            sa.Column("followup_questions_frozen_at", UTCDateTime(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("weekly_plans") as batch_op:
        batch_op.drop_column("followup_questions_frozen_at")
        batch_op.drop_column("followup_fallback_reason")
        batch_op.drop_column("followup_generation_source")
        batch_op.drop_column("followup_question_context")
