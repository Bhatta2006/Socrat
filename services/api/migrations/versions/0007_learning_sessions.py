"""Bounded evidence-led learning sessions and evidence provenance."""

import sqlalchemy as sa
from alembic import op

revision = "0007_learning_sessions"
down_revision = "0006_web_vitals"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("evidence", sa.Column("details", sa.JSON(), nullable=False, server_default="{}"))
    op.add_column("evidence", sa.Column("seq", sa.BigInteger(), nullable=False, server_default="0"))
    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "enrollment_id",
            sa.String(36),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day", sa.String(10), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("finished_at", sa.Integer(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("enrollment_id", "day"),
    )
    op.create_index("ix_learning_sessions_enrollment_id", "learning_sessions", ["enrollment_id"])
    op.create_table(
        "content_issues",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("concept", sa.String(160), nullable=False),
        sa.Column("atom_id", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(24), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_content_issues_user_id", "content_issues", ["user_id"])


def downgrade():
    op.drop_table("content_issues")
    op.drop_table("learning_sessions")
    op.drop_column("evidence", "details")
    op.drop_column("evidence", "seq")
