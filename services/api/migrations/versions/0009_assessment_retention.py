"""Protected forms, durable exposures, separable answers and append-only reviews."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assessment_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("learner_goals.id"), nullable=False),
        sa.Column(
            "pack_id", sa.String(36), sa.ForeignKey("skill_pack_versions.id"), nullable=False
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.Integer(), nullable=False),
        sa.Column("deadline_at", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.UniqueConstraint("user_id", "idempotency_key"),
    )
    for key in ("user_id", "goal_id"):
        op.create_index(f"ix_assessment_sessions_{key}", "assessment_sessions", [key])
    op.create_table(
        "assessment_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id", sa.String(36), sa.ForeignKey("assessment_sessions.id"), nullable=False
        ),
        sa.Column("exercise_id", sa.String(64), nullable=False),
        sa.Column("family_id", sa.String(64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("issued_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("session_id", "position"),
    )
    op.create_index("ix_assessment_items_session_id", "assessment_items", ["session_id"])
    op.create_table(
        "assessment_responses",
        sa.Column("item_id", sa.String(36), sa.ForeignKey("assessment_items.id"), primary_key=True),
        sa.Column(
            "session_id", sa.String(36), sa.ForeignKey("assessment_sessions.id"), nullable=False
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("session_id", "idempotency_key"),
    )
    op.create_table(
        "assessment_answers",
        sa.Column("item_id", sa.String(36), sa.ForeignKey("assessment_items.id"), primary_key=True),
        sa.Column("answer", sa.String(2000), nullable=False),
    )
    op.create_table(
        "assessment_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("item_id", sa.String(36), sa.ForeignKey("assessment_items.id"), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("evidence_reference", sa.String(512), nullable=False),
        sa.Column("rationale", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("item_id", "idempotency_key"),
    )
    op.create_index("ix_assessment_reviews_item_id", "assessment_reviews", ["item_id"])
    op.create_table(
        "assessment_disputes",
        sa.Column("item_id", sa.String(36), sa.ForeignKey("assessment_items.id"), primary_key=True),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("rationale", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    for table in (
        "assessment_items",
        "assessment_responses",
        "assessment_reviews",
        "assessment_disputes",
    ):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(
                f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_learning_mutation()"
            )
        else:
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable assessment record'); END"
                )


def downgrade():
    for table in (
        "assessment_disputes",
        "assessment_reviews",
        "assessment_answers",
        "assessment_responses",
        "assessment_items",
        "assessment_sessions",
    ):
        op.drop_table(table)
