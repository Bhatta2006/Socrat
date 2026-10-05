"""Durable execution attempts, autosaves, signed jobs, and worker capability leases."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "code_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("goal_id", sa.String(36), sa.ForeignKey("learner_goals.id"), nullable=False),
        sa.Column(
            "pack_id", sa.String(36), sa.ForeignKey("skill_pack_versions.id"), nullable=False
        ),
        sa.Column("exercise_id", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("user_id", "idempotency_key"),
    )
    op.create_table(
        "code_drafts",
        sa.Column("attempt_id", sa.String(36), sa.ForeignKey("code_attempts.id"), primary_key=True),
        sa.Column("source", sa.String(64000), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Integer(), nullable=False),
    )
    op.create_table(
        "code_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("attempt_id", sa.String(36), sa.ForeignKey("code_attempts.id"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_digest", sa.String(64), nullable=False),
        sa.Column("client_key", sa.String(64), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("signature", sa.String(64), nullable=False),
        sa.Column("tests", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("worker_id", sa.String(64), nullable=True),
        sa.Column("lease_until", sa.Integer(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("result_signature", sa.String(64), nullable=True),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("attempt_id", "idempotency_key"),
    )
    op.create_table(
        "code_run_sources",
        sa.Column("run_id", sa.String(36), sa.ForeignKey("code_runs.id"), primary_key=True),
        sa.Column("source", sa.String(64000), nullable=False),
    )
    op.create_table(
        "execution_workers",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("images", sa.JSON(), nullable=False),
        sa.Column("seen_at", sa.Integer(), nullable=False),
    )
    for table, column in (
        ("code_attempts", "user_id"),
        ("code_runs", "user_id"),
        ("code_runs", "attempt_id"),
        ("code_runs", "status"),
        ("code_runs", "client_key"),
    ):
        op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_table("execution_capacity", sa.Column("id", sa.Integer(), primary_key=True))
    op.execute("INSERT INTO execution_capacity (id) VALUES (1)")
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER immutable_code_attempts BEFORE UPDATE OR DELETE ON code_attempts FOR EACH ROW EXECUTE FUNCTION reject_learning_mutation()"
        )
        op.execute("""CREATE FUNCTION protect_code_job() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN
            IF NEW.manifest::text IS DISTINCT FROM OLD.manifest::text OR NEW.tests::text IS DISTINCT FROM OLD.tests::text
            OR NEW.signature IS DISTINCT FROM OLD.signature OR NEW.id IS DISTINCT FROM OLD.id
            OR NEW.attempt_id IS DISTINCT FROM OLD.attempt_id OR NEW.user_id IS DISTINCT FROM OLD.user_id
            OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key OR NEW.request_digest IS DISTINCT FROM OLD.request_digest
            OR (OLD.result IS NOT NULL AND NEW.result::text IS DISTINCT FROM OLD.result::text)
            OR (OLD.result IS NOT NULL AND NEW.result_signature IS DISTINCT FROM OLD.result_signature)
            THEN RAISE EXCEPTION 'immutable code job'; END IF; RETURN NEW; END $$""")
        op.execute(
            "CREATE TRIGGER immutable_code_job BEFORE UPDATE ON code_runs FOR EACH ROW EXECUTE FUNCTION protect_code_job()"
        )
    else:
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER immutable_code_attempts_{action.lower()} BEFORE {action} ON code_attempts BEGIN SELECT RAISE(ABORT, 'immutable code attempt'); END"
            )
        op.execute("""CREATE TRIGGER immutable_code_job BEFORE UPDATE ON code_runs
            WHEN NEW.manifest != OLD.manifest OR NEW.tests != OLD.tests OR NEW.signature != OLD.signature
            OR NEW.id != OLD.id OR NEW.attempt_id != OLD.attempt_id OR NEW.user_id != OLD.user_id
            OR NEW.idempotency_key != OLD.idempotency_key OR NEW.request_digest != OLD.request_digest
            OR (OLD.result IS NOT NULL AND NEW.result IS NOT OLD.result)
            OR (OLD.result IS NOT NULL AND NEW.result_signature IS NOT OLD.result_signature)
            BEGIN SELECT RAISE(ABORT, 'immutable code job'); END""")


def downgrade():
    for table in (
        "execution_capacity",
        "execution_workers",
        "code_run_sources",
        "code_runs",
        "code_drafts",
        "code_attempts",
    ):
        op.drop_table(table)
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION protect_code_job()")
