"""Record which option a learner chose, so calibration can count distractor rates.

Additive and nullable: earlier rows simply have no choice recorded.
"""

import sqlalchemy as sa
from alembic import op

revision = "0011_quiz_response_choice"
down_revision = "0010_quiz_engine_sessions"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("quiz_responses", sa.Column("choice", sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table("quiz_responses") as batch:
        batch.drop_column("choice")
