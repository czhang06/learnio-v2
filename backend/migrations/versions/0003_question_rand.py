"""Add a stored random sort key so exam sampling can use an index.

ORDER BY random() must read and sort every matching row. A per-row random
value with an index on (course_id, rand) lets us pick a random starting point
and read the next N rows in index order instead.

Revision ID: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    # The volatile default is evaluated per row, so existing rows get distinct values.
    op.add_column("questions", sa.Column("rand", sa.Float(53), nullable=False, server_default=sa.text("random()")))
    op.create_index("ix_questions_course_rand", "questions", ["course_id", "rand"])


def downgrade() -> None:
    op.drop_index("ix_questions_course_rand", table_name="questions")
    op.drop_column("questions", "rand")
