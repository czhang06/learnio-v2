"""Add image_key to questions and draft_questions.

Each question can point at a PNG of its region of the original PDF, kept in
the PDF store, which keeps matrices, fractions and figures readable.

Revision ID: 0006
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"


def upgrade() -> None:
    op.add_column("questions", sa.Column("image_key", sa.String(255)))
    op.add_column("draft_questions", sa.Column("image_key", sa.String(255)))


def downgrade() -> None:
    op.drop_column("draft_questions", "image_key")
    op.drop_column("questions", "image_key")
