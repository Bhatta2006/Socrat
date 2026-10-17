"""Adaptive roadmap: learner-approved plan proposals, overrides and revision diffs.

Additive: existing enrollments get empty overrides and revisions an empty snapshot.
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_adaptive_roadmap"
down_revision = "0011_quiz_response_choice"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "enrollments", sa.Column("adaptive", sa.JSON(), nullable=False, server_default="{}")
    )
    op.add_column(
        "plan_revisions", sa.Column("snapshot", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column(
        "plan_revisions", sa.Column("changes", sa.JSON(), nullable=False, server_default="{}")
    )
    op.create_table(
        "plan_proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "enrollment_id",
            sa.String(36),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("key", sa.String(240), nullable=False),
        sa.Column("group", sa.String(64), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("decided_at", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_plan_proposals_enrollment_status", "plan_proposals", ["enrollment_id", "status"]
    )


def downgrade():
    op.drop_index("ix_plan_proposals_enrollment_status", table_name="plan_proposals")
    op.drop_table("plan_proposals")
    with op.batch_alter_table("plan_revisions") as batch:
        batch.drop_column("changes")
        batch.drop_column("snapshot")
    with op.batch_alter_table("enrollments") as batch:
        batch.drop_column("adaptive")
