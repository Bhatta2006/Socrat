"""Persist the explicitly development-only presenter clock."""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "demo_clock",
        sa.Column("id", sa.String(16), primary_key=True),
        sa.Column("offset_seconds", sa.Integer(), nullable=False),
    )


def downgrade():
    op.drop_table("demo_clock")
