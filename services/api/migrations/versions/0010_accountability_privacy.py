"""Preferences, reminders and transaction-scoped, learner-owned erasure."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

# Each expression resolves OLD to its learner, never the reviewer or operator.
OWNERS = {
    "diagnostic_attempts": "(SELECT user_id FROM diagnostic_sessions WHERE id=OLD.diagnostic_id)",
    "diagnostic_responses": "(SELECT user_id FROM diagnostic_sessions WHERE id=OLD.diagnostic_id)",
    "learning_evidence": "OLD.user_id",
    "mastery_events": "OLD.user_id",
    "learning_policy_reviews": "OLD.user_id",
    "curriculum_revisions": "OLD.user_id",
    "planning_commands": "(SELECT user_id FROM learner_goals WHERE id=OLD.goal_id)",
    "code_attempts": "OLD.user_id",
    "session_commands": "(SELECT user_id FROM learning_sessions WHERE id=OLD.session_id)",
    "tutor_turns": "OLD.user_id",
    "submit_assistance": "(SELECT user_id FROM code_runs WHERE id=OLD.run_id)",
    "advisor_shadows": "OLD.user_id",
    "assessment_items": "(SELECT user_id FROM assessment_sessions WHERE id=OLD.session_id)",
    "assessment_responses": "(SELECT user_id FROM assessment_sessions WHERE id=OLD.session_id)",
    "assessment_reviews": "(SELECT s.user_id FROM assessment_sessions s JOIN assessment_items i ON i.session_id=s.id WHERE i.id=OLD.item_id)",
    "assessment_disputes": "(SELECT s.user_id FROM assessment_sessions s JOIN assessment_items i ON i.session_id=s.id WHERE i.id=OLD.item_id)",
}


def triggers(erasure):
    postgres = op.get_bind().dialect.name == "postgresql"
    for table, owner in OWNERS.items():
        allowed = f"EXISTS (SELECT 1 FROM privacy_requests WHERE status='erasing' AND target_user_id={owner})"
        if postgres:
            op.execute(f"DROP TRIGGER IF EXISTS immutable_{table} ON {table}")
            op.execute(f"DROP TRIGGER IF EXISTS immutable_{table}_delete ON {table}")
            op.execute(f"DROP FUNCTION IF EXISTS erase_{table}()")
            if erasure:
                op.execute(
                    f"CREATE TRIGGER immutable_{table} BEFORE UPDATE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_learning_mutation()"
                )
                op.execute(
                    f"CREATE FUNCTION erase_{table}() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN IF {allowed} THEN RETURN OLD; END IF; RAISE EXCEPTION 'immutable learning fact'; END; $$"
                )
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_delete BEFORE DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION erase_{table}()"
                )
            else:
                op.execute(
                    f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_learning_mutation()"
                )
        else:
            op.execute(f"DROP TRIGGER IF EXISTS immutable_{table}_delete")
            condition = f" WHEN NOT ({allowed})" if erasure else ""
            op.execute(
                f"CREATE TRIGGER immutable_{table}_delete BEFORE DELETE ON {table}{condition} BEGIN SELECT RAISE(ABORT, 'immutable learning fact'); END"
            )


def upgrade():
    op.create_table(
        "assessment_deferrals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("learner_goals.id"), nullable=False),
        sa.Column("cycle", sa.String(80), nullable=False),
        sa.Column("until_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("goal_id", "cycle"),
    )
    op.create_index("ix_assessment_deferrals_goal_id", "assessment_deferrals", ["goal_id"])
    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
    )
    op.create_table(
        "reminders",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("local_date", sa.String(10), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.Integer(), nullable=True),
        sa.UniqueConstraint("user_id", "local_date"),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("target_user_id", sa.String(36), nullable=True),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("cleanup_context", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("deadline_at", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.Integer(), nullable=True),
    )
    op.create_index("ix_privacy_requests_target_user_id", "privacy_requests", ["target_user_id"])
    triggers(True)


def downgrade():
    triggers(False)
    op.drop_table("privacy_requests")
    op.drop_table("reminders")
    op.drop_table("user_preferences")
    op.drop_table("assessment_deferrals")
