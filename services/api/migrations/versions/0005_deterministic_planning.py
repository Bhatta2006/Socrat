"""Immutable curriculum revisions and serialized, idempotent planning commands."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "curriculum_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("learner_goals.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("goal_id", "revision"),
    )
    op.create_table(
        "curriculum_heads",
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("learner_goals.id"), primary_key=True),
        sa.Column(
            "active_id", sa.String(36), sa.ForeignKey("curriculum_revisions.id"), nullable=False
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_table(
        "planning_commands",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("learner_goals.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("goal_id", "idempotency_key"),
    )
    for table, column in (
        ("curriculum_revisions", "goal_id"),
        ("curriculum_revisions", "user_id"),
        ("planning_commands", "goal_id"),
    ):
        op.create_index(f"ix_{table}_{column}", table, [column])
    for table in ("curriculum_revisions", "planning_commands"):
        if op.get_bind().dialect.name == "postgresql":
            op.execute(
                f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_learning_mutation()"
            )
        elif op.get_bind().dialect.name == "sqlite":
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable planning record'); END"
                )


def downgrade():
    for table in ("planning_commands", "curriculum_heads", "curriculum_revisions"):
        op.drop_table(table)
