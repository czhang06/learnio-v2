"""Add the display size of question images, so pages can reserve their space.

Revision ID: 0008
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"


def upgrade() -> None:
    for table in ("questions", "draft_questions"):
        op.add_column(table, sa.Column("image_width", sa.Integer))
        op.add_column(table, sa.Column("image_height", sa.Integer))


def downgrade() -> None:
    for table in ("questions", "draft_questions"):
        op.drop_column(table, "image_height")
        op.drop_column(table, "image_width")
