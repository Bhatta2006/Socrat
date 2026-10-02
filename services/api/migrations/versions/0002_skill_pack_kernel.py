"""Add immutable skill-pack versions, release pointers, and review history.

M1 tables are retained; application rollback must account for readiness revision.
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "skill_pack_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pack_key", sa.String(64), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("domain", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("pack_key", "version"),
        sa.CheckConstraint(
            "status IN ('draft','technical_review','learning_review','language_verified','staged','released','quarantined','retired')",
            name="skill_pack_status",
        ),
    )
    op.create_index("ix_skill_pack_versions_pack_key", "skill_pack_versions", ["pack_key"])
    op.create_table(
        "skill_pack_heads",
        sa.Column("pack_key", sa.String(64), primary_key=True),
        sa.Column(
            "active_id", sa.String(36), sa.ForeignKey("skill_pack_versions.id"), nullable=True
        ),
        sa.Column(
            "previous_id", sa.String(36), sa.ForeignKey("skill_pack_versions.id"), nullable=True
        ),
    )
    op.create_table(
        "content_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "version_id", sa.String(36), sa.ForeignKey("skill_pack_versions.id"), nullable=False
        ),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("evidence_reference", sa.String(512), nullable=False),
        sa.Column("reason", sa.String(2000), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_content_reviews_version_id", "content_reviews", ["version_id"])
    if op.get_bind().dialect.name == "sqlite":
        op.execute("""CREATE TRIGGER skill_pack_immutable BEFORE UPDATE ON skill_pack_versions
            WHEN NEW.id != OLD.id OR NEW.pack_key != OLD.pack_key OR NEW.version != OLD.version
            OR NEW.domain != OLD.domain OR NEW.payload != OLD.payload OR NEW.digest != OLD.digest
            OR NEW.author_id != OLD.author_id OR NEW.created_at != OLD.created_at
            BEGIN SELECT RAISE(ABORT, 'immutable_skill_pack'); END""")
        op.execute("""CREATE TRIGGER skill_pack_no_delete BEFORE DELETE ON skill_pack_versions
            BEGIN SELECT RAISE(ABORT, 'immutable_skill_pack'); END""")
        for action in ("UPDATE", "DELETE"):
            op.execute(f"""CREATE TRIGGER content_review_no_{action.lower()} BEFORE {action} ON content_reviews
                BEGIN SELECT RAISE(ABORT, 'append_only_review'); END""")
    elif op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION protect_skill_pack() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'immutable_skill_pack'; END IF;
                IF NEW.id IS DISTINCT FROM OLD.id OR NEW.pack_key IS DISTINCT FROM OLD.pack_key
                OR NEW.version IS DISTINCT FROM OLD.version OR NEW.domain IS DISTINCT FROM OLD.domain
                OR NEW.payload::text IS DISTINCT FROM OLD.payload::text OR NEW.digest IS DISTINCT FROM OLD.digest
                OR NEW.author_id IS DISTINCT FROM OLD.author_id OR NEW.created_at IS DISTINCT FROM OLD.created_at
                THEN RAISE EXCEPTION 'immutable_skill_pack'; END IF;
                RETURN NEW;
            END $$""")
        op.execute(
            "CREATE TRIGGER skill_pack_immutable BEFORE UPDATE OR DELETE ON skill_pack_versions FOR EACH ROW EXECUTE FUNCTION protect_skill_pack()"
        )
        op.execute("""CREATE FUNCTION protect_content_review() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN RAISE EXCEPTION 'append_only_review'; END $$""")
        op.execute(
            "CREATE TRIGGER content_review_immutable BEFORE UPDATE OR DELETE ON content_reviews FOR EACH ROW EXECUTE FUNCTION protect_content_review()"
        )
    else:
        raise RuntimeError("Skill packs require PostgreSQL or SQLite")


def downgrade():
    op.drop_table("content_reviews")
    op.drop_table("skill_pack_heads")
    op.drop_table("skill_pack_versions")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION protect_content_review()")
        op.execute("DROP FUNCTION protect_skill_pack()")
