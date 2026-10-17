"""Adaptive quiz runtime state: responses, learner abilities, item ratings and calibrations.

Additive only. Item definitions stay in content files.
"""

import sqlalchemy as sa
from alembic import op

revision = "0009_quiz_runtime"
down_revision = "0008_product_tour"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "quiz_responses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "enrollment_id",
            sa.String(36),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_id", sa.String(200), nullable=False),
        sa.Column("family", sa.String(200), nullable=False, server_default=""),
        sa.Column("pattern", sa.String(200), nullable=False, server_default=""),
        sa.Column("concept", sa.String(160), nullable=False),
        sa.Column("mode", sa.String(24), nullable=False),
        sa.Column("pool", sa.String(16), nullable=False),
        sa.Column("session_id", sa.String(36), nullable=False, server_default=""),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("hint_level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("time_s", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("seed", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_quiz_responses_item_id", "quiz_responses", ["item_id"])
    op.create_index(
        "ix_quiz_responses_enrollment_created", "quiz_responses", ["enrollment_id", "created_at"]
    )
    op.create_table(
        "learner_abilities",
        sa.Column(
            "enrollment_id",
            sa.String(36),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("pattern", sa.String(200), primary_key=True),
        sa.Column("theta", sa.Float(), nullable=False),
        sa.Column("n", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "item_ratings",
        sa.Column("item_id", sa.String(200), primary_key=True),
        sa.Column("d_current", sa.Float(), nullable=False),
        sa.Column("n_responses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "item_calibrations",
        sa.Column("item_id", sa.String(200), primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("n_responses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pct_correct", sa.Float(), nullable=True),
        sa.Column("discrimination", sa.Float(), nullable=True),
        sa.Column("distractor_counts", sa.JSON(), nullable=False),
        sa.Column("median_time_s", sa.Float(), nullable=True),
        sa.Column("flags", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.Integer(), nullable=False),
        sa.Column("approved_by", sa.String(120), nullable=True),
        sa.Column("approved_at", sa.Integer(), nullable=True),
    )


def downgrade():
    op.drop_table("item_calibrations")
    op.drop_table("item_ratings")
    op.drop_table("learner_abilities")
    op.drop_index("ix_quiz_responses_enrollment_created", table_name="quiz_responses")
    op.drop_index("ix_quiz_responses_item_id", table_name="quiz_responses")
    op.drop_table("quiz_responses")
