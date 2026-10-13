"""anonymous field performance samples (Core Web Vitals)

Revision ID: 0006_web_vitals
Revises: 0005_feedback
Create Date: 2026-10-14 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_web_vitals"
down_revision: str | None = "0005_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "web_vitals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("day", sa.String(length=10), nullable=False),
        sa.Column("route", sa.String(length=80), nullable=False),
        sa.Column("metric", sa.String(length=8), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("device", sa.String(length=8), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_web_vitals_day_metric", "web_vitals", ["day", "metric"])


def downgrade() -> None:
    op.drop_index("ix_web_vitals_day_metric", table_name="web_vitals")
    op.drop_table("web_vitals")
