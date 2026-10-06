"""Bounded tutor records, separable content, Submit assistance and shadow decisions."""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tutor_turns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("attempt_id", sa.String(36), sa.ForeignKey("code_attempts.id"), nullable=False),
        sa.Column("scope_id", sa.String(36), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("context_digest", sa.String(64), nullable=False),
        sa.Column("action_digest", sa.String(64), nullable=False),
        sa.Column("granted_level", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("telemetry", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("attempt_id", "idempotency_key"),
        sa.UniqueConstraint("attempt_id", "position"),
    )
    for key in ("user_id", "attempt_id", "scope_id"):
        op.create_index(f"ix_tutor_turns_{key}", "tutor_turns", [key])
    op.create_table(
        "tutor_artifacts",
        sa.Column("turn_id", sa.String(36), sa.ForeignKey("tutor_turns.id"), primary_key=True),
        sa.Column("reasoning", sa.String(2000), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
    )
    op.create_table(
        "submit_assistance",
        sa.Column("run_id", sa.String(36), sa.ForeignKey("code_runs.id"), primary_key=True),
        sa.Column("hint_level", sa.Integer(), nullable=False),
    )
    op.create_table(
        "advisor_shadows",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "curriculum_id", sa.String(36), sa.ForeignKey("curriculum_revisions.id"), nullable=False
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("curriculum_id", "idempotency_key"),
    )
    op.create_index("ix_advisor_shadows_user_id", "advisor_shadows", ["user_id"])
    for table in ("tutor_turns", "submit_assistance", "advisor_shadows"):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(
                f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_learning_mutation()"
            )
        else:
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable assistance record'); END"
                )


def downgrade():
    for table in ("advisor_shadows", "submit_assistance", "tutor_artifacts", "tutor_turns"):
        op.drop_table(table)
