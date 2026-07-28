"""link followups to weekly plans and persist KB06 answers

Revision ID: 5f31d8aee912
Revises: ca8a1d34b622
Create Date: 2026-07-26 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5f31d8aee912"
down_revision: str | Sequence[str] | None = "ca8a1d34b622"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NAMING_CONVENTION = {
    "uq": "uq_%(table_name)s_%(column_0_name)s",
}


def upgrade() -> None:
    """Add exact plan provenance while retaining legacy follow-up rows."""
    with op.batch_alter_table(
        "followups", recreate="always", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint(
            "uq_followups_current_assessment_id", type_="unique"
        )
        batch_op.alter_column(
            "current_assessment_id",
            existing_type=sa.String(),
            nullable=True,
        )
        batch_op.add_column(sa.Column("weekly_plan_id", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("question_answers", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("question_context", sa.JSON(), nullable=True))
        batch_op.create_foreign_key(
            "fk_followups_weekly_plan_id_weekly_plans",
            "weekly_plans",
            ["weekly_plan_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_followups_weekly_plan_id", ["weekly_plan_id"]
        )


def downgrade() -> None:
    """Remove KB06 provenance columns.

    Downgrade is intentionally blocked if new weekly-plan follow-ups exist,
    because those rows have no current assessment and cannot fit the legacy
    non-null schema without data loss.
    """
    connection = op.get_bind()
    new_row_count = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM followups "
            "WHERE weekly_plan_id IS NOT NULL OR current_assessment_id IS NULL"
        )
    ).scalar_one()
    if new_row_count:
        raise RuntimeError(
            "Cannot downgrade while KB06 weekly-plan follow-up rows exist."
        )

    with op.batch_alter_table(
        "followups", recreate="always", naming_convention=_NAMING_CONVENTION
    ) as batch_op:
        batch_op.drop_constraint("uq_followups_weekly_plan_id", type_="unique")
        batch_op.drop_constraint(
            "fk_followups_weekly_plan_id_weekly_plans", type_="foreignkey"
        )
        batch_op.drop_column("question_context")
        batch_op.drop_column("question_answers")
        batch_op.drop_column("weekly_plan_id")
        batch_op.alter_column(
            "current_assessment_id",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_followups_current_assessment_id", ["current_assessment_id"]
        )
