"""weekly personalised assessments

Revision ID: 0003_weekly
Revises: 0002_practice
Create Date: 2026-10-13 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_weekly"
down_revision: str | None = "0002_practice"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weekly_assessments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("enrollment_id", sa.String(length=36), nullable=False),
        sa.Column("iso_week", sa.String(length=10), nullable=False),
        sa.Column("concepts", sa.JSON(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("coding", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("timed", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.Integer(), nullable=True),
        sa.Column("finished_at", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("report", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enrollment_id", "iso_week"),
    )
    op.create_index(
        op.f("ix_weekly_assessments_enrollment_id"),
        "weekly_assessments",
        ["enrollment_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_weekly_assessments_enrollment_id"), table_name="weekly_assessments")
    op.drop_table("weekly_assessments")
