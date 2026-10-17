"""Grouped error reports: server exceptions, browser crashes and learner problem reports.

Additive: a new table only.
"""

import sqlalchemy as sa
from alembic import op

revision = "0014_error_reports"
down_revision = "0013_ai_usage"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "error_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("route", sa.String(120), nullable=False, server_default=""),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(12), nullable=False, server_default="open"),
        sa.Column("first_at", sa.Integer(), nullable=False),
        sa.Column("last_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_error_reports_status_last", "error_reports", ["status", "last_at"])


def downgrade():
    op.drop_index("ix_error_reports_status_last", "error_reports")
    op.drop_table("error_reports")
