"""Record the prior active version for deterministic emergency rollback."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("pack_versions") as batch:
        batch.add_column(
            sa.Column(
                "previous_active_id",
                sa.String(36),
                sa.ForeignKey("pack_versions.id", name="fk_pack_versions_previous_active_id"),
                nullable=True,
            )
        )


def downgrade():
    with op.batch_alter_table("pack_versions") as batch:
        batch.drop_column("previous_active_id")
