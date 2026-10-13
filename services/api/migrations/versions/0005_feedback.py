"""tutor reply ratings and resource events

Revision ID: 0005_feedback
Revises: 0004_sprints
Create Date: 2026-10-13 21:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_feedback"
down_revision: str | None = "0004_sprints"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("assistant_messages") as batch:
        batch.add_column(sa.Column("rating", sa.Integer(), nullable=True))
    op.create_table(
        "resource_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("concept", sa.String(length=160), nullable=False),
        sa.Column("url", sa.String(length=512), nullable=False),
        sa.Column("opened_at", sa.Integer(), nullable=True),
        sa.Column("helpful", sa.Boolean(), nullable=True),
        sa.Column("updated_at", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "concept", "url"),
    )
    op.create_index(op.f("ix_resource_events_user_id"), "resource_events", ["user_id"])
    op.create_index(op.f("ix_resource_events_concept"), "resource_events", ["concept"])


def downgrade() -> None:
    op.drop_index(op.f("ix_resource_events_concept"), table_name="resource_events")
    op.drop_index(op.f("ix_resource_events_user_id"), table_name="resource_events")
    op.drop_table("resource_events")
    with op.batch_alter_table("assistant_messages") as batch:
        batch.drop_column("rating")
