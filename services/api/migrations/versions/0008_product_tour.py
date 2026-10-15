"""First-run product tour: remember when each learner has seen it.

Existing accounts are marked as seen, so only learners who join after this release get the tour.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_product_tour"
down_revision = "0007_learning_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("tour_seen_at", sa.Integer(), nullable=True))
    op.execute("UPDATE users SET tour_seen_at = created_at")


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("tour_seen_at")
