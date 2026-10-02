"""Persist confirmed, version-pinned learner goals without changing M1/M2 records."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learner_goals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("review_digest", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("confirmation_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key"),
    )
    op.create_index("ix_learner_goals_user_id", "learner_goals", ["user_id"])


def downgrade():
    op.drop_index("ix_learner_goals_user_id", "learner_goals")
    op.drop_table("learner_goals")
