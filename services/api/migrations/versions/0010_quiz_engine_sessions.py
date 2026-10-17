"""Adaptive quiz sessions: the served steps and pending item of one engine session.

Additive only; learner-scoped and erased with the account.
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_quiz_engine_sessions"
down_revision = "0009_quiz_runtime"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quiz_engine_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "enrollment_id",
            sa.String(36),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("mode", sa.String(24), nullable=False),
        sa.Column("track", sa.String(16), nullable=False),
        sa.Column("concepts", sa.JSON(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_quiz_engine_sessions_enrollment_id", "quiz_engine_sessions", ["enrollment_id"]
    )


def downgrade():
    op.drop_index("ix_quiz_engine_sessions_enrollment_id", table_name="quiz_engine_sessions")
    op.drop_table("quiz_engine_sessions")
