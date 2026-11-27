"""Drop questions.difficulty.

Every question kept the default of 3 and the frontend stopped showing it, so
the column and its API filters go.

Revision ID: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    op.drop_column("questions", "difficulty")


def downgrade() -> None:
    op.add_column("questions", sa.Column("difficulty", sa.SmallInteger, nullable=False, server_default="3"))
