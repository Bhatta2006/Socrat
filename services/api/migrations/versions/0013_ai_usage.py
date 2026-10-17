"""Record tokens and estimated cost per model call, for LLM budgets and the cost dashboard.

Additive: a new table only.
"""

import sqlalchemy as sa
from alembic import op

revision = "0013_ai_usage"
down_revision = "0012_adaptive_roadmap"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ai_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True
        ),
        sa.Column("feature", sa.String(24), nullable=False),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("day", sa.String(10), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_ai_usage_day", "ai_usage", ["day"])
    op.create_index("ix_ai_usage_user_created", "ai_usage", ["user_id", "created_at"])


def downgrade():
    op.drop_index("ix_ai_usage_user_created", "ai_usage")
    op.drop_index("ix_ai_usage_day", "ai_usage")
    op.drop_table("ai_usage")
