"""M2 skill-pack imports, reviews, releases, and quarantine."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_events", sa.Column("target_id", sa.String(36), nullable=True))
    op.create_table(
        "content_operators",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role", sa.String(40), primary_key=True),
    )
    op.create_table(
        "pack_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pack_key", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("author_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.Integer(), nullable=True),
        sa.UniqueConstraint("pack_key", "version"),
    )
    op.create_index("ix_pack_versions_pack_key", "pack_versions", ["pack_key"])
    op.create_index(
        "ux_pack_versions_active_key",
        "pack_versions",
        ["pack_key"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_table(
        "pack_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("pack_versions.id"), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(40), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("note", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("version_id", "role", "reviewer_id"),
    )
    op.create_index("ix_pack_reviews_version_id", "pack_reviews", ["version_id"])
    op.create_table(
        "pack_quarantines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("pack_versions.id"), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
    )
    op.create_index("ix_pack_quarantines_version_id", "pack_quarantines", ["version_id"])
    op.create_table(
        "pack_item_quarantines",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("version_id", sa.String(36), sa.ForeignKey("pack_versions.id"), nullable=False),
        sa.Column("item_key", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.Integer(), nullable=False),
        sa.UniqueConstraint("version_id", "item_key"),
    )
    op.create_index("ix_pack_item_quarantines_version_id", "pack_item_quarantines", ["version_id"])


def downgrade():
    op.drop_table("pack_item_quarantines")
    op.drop_table("pack_quarantines")
    op.drop_table("pack_reviews")
    op.drop_table("pack_versions")
    op.drop_table("content_operators")
    op.drop_column("audit_events", "target_id")
