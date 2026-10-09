"""practice library: learner marks on external problems and linked CP accounts

Revision ID: 0002_practice
Revises: 0001_v2
Create Date: 2026-10-09 23:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_practice"
down_revision: str | None = "0001_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "practice_marks",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("problem_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("bookmarked", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.Integer(), nullable=True),
        sa.Column("solved_at", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "problem_id"),
    )
    op.create_table(
        "linked_accounts",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("handle", sa.String(length=64), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("max_rating", sa.Integer(), nullable=True),
        sa.Column("rank", sa.String(length=40), nullable=False),
        sa.Column("solved", sa.JSON(), nullable=False),
        sa.Column("attempted", sa.JSON(), nullable=False),
        sa.Column("tag_stats", sa.JSON(), nullable=False),
        sa.Column("synced_at", sa.Integer(), nullable=True),
        sa.Column("sync_error", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "platform"),
    )


def downgrade() -> None:
    op.drop_table("linked_accounts")
    op.drop_table("practice_marks")
