"""Add staged diagnostics and append-only learning evidence."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

IMMUTABLE = (
    "diagnostic_attempts",
    "diagnostic_responses",
    "learning_evidence",
    "mastery_events",
    "learning_policy_reviews",
)


def upgrade():
    # Explicit column definitions keep historical migrations independent of ORM changes.
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "goal_id", sa.String(36), sa.ForeignKey("learner_goals.id"), nullable=False, unique=True
        ),
        sa.Column(
            "pack_id", sa.String(36), sa.ForeignKey("skill_pack_versions.id"), nullable=False
        ),
        sa.Column("blueprint_id", sa.String(64), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.Integer(), nullable=False),
        sa.Column("deadline_at", sa.Integer(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
    )
    op.create_table(
        "diagnostic_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "diagnostic_id", sa.String(36), sa.ForeignKey("diagnostic_sessions.id"), nullable=False
        ),
        sa.Column("exercise_id", sa.String(64), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("selection", sa.JSON(), nullable=False),
        sa.Column("issued_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("diagnostic_id", "position"),
    )
    op.create_table(
        "diagnostic_responses",
        sa.Column(
            "attempt_id", sa.String(36), sa.ForeignKey("diagnostic_attempts.id"), primary_key=True
        ),
        sa.Column(
            "diagnostic_id", sa.String(36), sa.ForeignKey("diagnostic_sessions.id"), nullable=False
        ),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("answer_digest", sa.String(64), nullable=False),
        sa.Column("outcome", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("diagnostic_id", "idempotency_key"),
    )
    op.create_table(
        "diagnostic_answers",
        sa.Column(
            "attempt_id", sa.String(36), sa.ForeignKey("diagnostic_attempts.id"), primary_key=True
        ),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("answer", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "learning_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.String(36), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "sequence"),
        sa.UniqueConstraint("user_id", "source_id", "kind"),
    )
    op.create_table(
        "learner_states",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("active_policy", sa.String(64), nullable=False),
        sa.Column("previous_policy", sa.String(64), nullable=True),
        sa.Column("projection", sa.JSON(), nullable=False),
    )
    op.create_table(
        "mastery_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "evidence_id", sa.String(36), sa.ForeignKey("learning_evidence.id"), nullable=False
        ),
        sa.Column("concept_key", sa.String(160), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("before_state", sa.JSON(), nullable=False),
        sa.Column("after_state", sa.JSON(), nullable=False),
        sa.Column("reason_code", sa.String(64), nullable=False),
        sa.UniqueConstraint("evidence_id", "concept_key", "policy_version"),
    )
    op.create_table(
        "learning_policy_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("policy_version", sa.String(64), nullable=False),
        sa.Column("policy_digest", sa.String(64), nullable=False),
        sa.Column("evidence_reference", sa.String(512), nullable=False),
        sa.Column("projection_digest", sa.String(64), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    for table, column in (
        ("diagnostic_sessions", "user_id"),
        ("diagnostic_attempts", "diagnostic_id"),
        ("diagnostic_responses", "diagnostic_id"),
        ("diagnostic_answers", "user_id"),
        ("learning_evidence", "user_id"),
        ("mastery_events", "user_id"),
        ("learning_policy_reviews", "user_id"),
    ):
        op.create_index(f"ix_{table}_{column}", table, [column])
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("""CREATE TRIGGER diagnostic_snapshot_immutable BEFORE UPDATE ON diagnostic_sessions
            WHEN NEW.id != OLD.id OR NEW.user_id != OLD.user_id OR NEW.goal_id != OLD.goal_id
            OR NEW.pack_id != OLD.pack_id OR NEW.blueprint_id != OLD.blueprint_id
            OR NEW.policy_version != OLD.policy_version OR NEW.snapshot != OLD.snapshot
            OR (OLD.result IS NOT NULL AND NEW.result IS NOT OLD.result)
            BEGIN SELECT RAISE(ABORT, 'immutable diagnostic snapshot'); END""")
    if dialect == "postgresql":
        op.execute("""CREATE FUNCTION protect_diagnostic_snapshot() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF NEW.id IS DISTINCT FROM OLD.id OR NEW.user_id IS DISTINCT FROM OLD.user_id
                OR NEW.goal_id IS DISTINCT FROM OLD.goal_id OR NEW.pack_id IS DISTINCT FROM OLD.pack_id
                OR NEW.blueprint_id IS DISTINCT FROM OLD.blueprint_id OR NEW.policy_version IS DISTINCT FROM OLD.policy_version
                OR NEW.snapshot::text IS DISTINCT FROM OLD.snapshot::text
                OR (OLD.result IS NOT NULL AND NEW.result::text IS DISTINCT FROM OLD.result::text)
                THEN RAISE EXCEPTION 'immutable diagnostic snapshot'; END IF;
                RETURN NEW;
            END $$""")
        op.execute(
            "CREATE TRIGGER diagnostic_snapshot_immutable BEFORE UPDATE ON diagnostic_sessions FOR EACH ROW EXECUTE FUNCTION protect_diagnostic_snapshot()"
        )
        op.execute(
            "CREATE FUNCTION reject_learning_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable learning fact'; END; $$"
        )
    for table in IMMUTABLE:
        if dialect == "postgresql":
            op.execute(
                f"CREATE TRIGGER immutable_{table} BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_learning_mutation()"
            )
        elif dialect == "sqlite":
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{table}_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'immutable learning fact'); END"
                )


def downgrade():
    for table in (
        "learning_policy_reviews",
        "mastery_events",
        "learner_states",
        "learning_evidence",
        "diagnostic_answers",
        "diagnostic_responses",
        "diagnostic_attempts",
        "diagnostic_sessions",
    ):
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_learning_mutation()")
        op.execute("DROP FUNCTION protect_diagnostic_snapshot()")
