"""Pinned resumable learning sessions and append-only command receipts."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("learner_goals.id"), nullable=False),
        sa.Column(
            "curriculum_id", sa.String(36), sa.ForeignKey("curriculum_revisions.id"), nullable=False
        ),
        sa.Column(
            "pack_id", sa.String(36), sa.ForeignKey("skill_pack_versions.id"), nullable=False
        ),
        sa.Column("local_date", sa.String(10), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("progress", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.Integer(), nullable=True),
        sa.UniqueConstraint("goal_id", "local_date"),
    )
    op.create_index("ix_learning_sessions_user_id", "learning_sessions", ["user_id"])
    op.create_table(
        "session_commands",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "session_id", sa.String(36), sa.ForeignKey("learning_sessions.id"), nullable=False
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("session_id", "idempotency_key"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER immutable_session_commands BEFORE UPDATE OR DELETE ON session_commands FOR EACH ROW EXECUTE FUNCTION reject_learning_mutation()"
        )
        op.execute("""CREATE FUNCTION protect_learning_session() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.snapshot::text IS DISTINCT FROM OLD.snapshot::text OR NEW.id IS DISTINCT FROM OLD.id
            OR NEW.user_id IS DISTINCT FROM OLD.user_id OR NEW.goal_id IS DISTINCT FROM OLD.goal_id
            OR NEW.curriculum_id IS DISTINCT FROM OLD.curriculum_id OR NEW.pack_id IS DISTINCT FROM OLD.pack_id
            OR NEW.local_date IS DISTINCT FROM OLD.local_date OR NEW.created_at IS DISTINCT FROM OLD.created_at
            THEN RAISE EXCEPTION 'immutable session pins'; END IF; RETURN NEW; END $$""")
        op.execute(
            "CREATE TRIGGER immutable_session_pins BEFORE UPDATE ON learning_sessions FOR EACH ROW EXECUTE FUNCTION protect_learning_session()"
        )
    else:
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER immutable_session_commands_{action.lower()} BEFORE {action} ON session_commands BEGIN SELECT RAISE(ABORT, 'immutable session command'); END"
            )
        op.execute("""CREATE TRIGGER immutable_session_pins BEFORE UPDATE ON learning_sessions
            WHEN NEW.snapshot != OLD.snapshot OR NEW.id != OLD.id OR NEW.user_id != OLD.user_id
            OR NEW.goal_id != OLD.goal_id OR NEW.curriculum_id != OLD.curriculum_id
            OR NEW.pack_id != OLD.pack_id OR NEW.local_date != OLD.local_date OR NEW.created_at != OLD.created_at
            BEGIN SELECT RAISE(ABORT, 'immutable session pins'); END""")


def downgrade():
    op.drop_table("session_commands")
    op.drop_table("learning_sessions")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION protect_learning_session()")
