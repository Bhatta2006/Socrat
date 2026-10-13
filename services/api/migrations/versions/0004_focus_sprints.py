"""focus sprints

Revision ID: 0004_sprints
Revises: 0003_weekly
Create Date: 2026-10-13 18:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sprints"
down_revision: str | None = "0003_weekly"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "focus_sprints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("enrollment_id", sa.String(length=36), nullable=False),
        sa.Column("problems", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.Integer(), nullable=False),
        sa.Column("deadline", sa.Integer(), nullable=False),
        sa.Column("finished_at", sa.Integer(), nullable=True),
        sa.Column("results", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_focus_sprints_enrollment_id"), "focus_sprints", ["enrollment_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_focus_sprints_enrollment_id"), table_name="focus_sprints")
    op.drop_table("focus_sprints")
