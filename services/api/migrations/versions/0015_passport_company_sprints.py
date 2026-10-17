"""Public Skill Passports and company-targeted sprints.

Additive: two new tables only.
"""

import sqlalchemy as sa
from alembic import op

revision = "0015_passport_company_sprints"
down_revision = "0014_error_reports"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "skill_passports",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("slug", sa.String(24), nullable=False, unique=True),
        sa.Column("public", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "company_sprints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "enrollment_id",
            sa.String(36),
            sa.ForeignKey("enrollments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company", sa.String(80), nullable=False),
        sa.Column("company_name", sa.String(120), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("weeks", sa.Integer(), nullable=False),
        sa.Column("started_on", sa.String(10), nullable=False),
        sa.Column("ends_on", sa.String(10), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("proposal_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("finished_at", sa.Integer(), nullable=True),
    )
    op.create_index("ix_company_sprints_enrollment_id", "company_sprints", ["enrollment_id"])


def downgrade():
    op.drop_index("ix_company_sprints_enrollment_id", "company_sprints")
    op.drop_table("company_sprints")
    op.drop_table("skill_passports")
