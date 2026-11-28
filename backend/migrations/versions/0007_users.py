"""Accounts: users, enrollments, saved questions and practice attempts.

Revision ID: 0007
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("sub", sa.String(255), nullable=False, unique=True),
        sa.Column("email", sa.String(320), nullable=False, server_default=""),
        sa.Column("name", sa.String(200), nullable=False, server_default=""),
        sa.Column("picture", sa.String(500), nullable=False, server_default=""),
        sa.Column("role", sa.String(16), nullable=False, server_default="user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "enrollments",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "saved_questions",
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer, sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topics", sa.ARRAY(sa.String(120)), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_attempts_user_course", "attempts", ["user_id", "course_id", "created_at"])
    op.create_table(
        "attempt_answers",
        sa.Column("attempt_id", sa.Integer, sa.ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("question_id", sa.Integer, sa.ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("result", sa.String(8)),
        sa.CheckConstraint("result IN ('right', 'wrong', 'skipped')", name="ck_attempt_answers_result"),
    )
    op.create_index("ix_attempt_answers_question", "attempt_answers", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_attempt_answers_question", table_name="attempt_answers")
    op.drop_table("attempt_answers")
    op.drop_index("ix_attempts_user_course", table_name="attempts")
    op.drop_table("attempts")
    op.drop_table("saved_questions")
    op.drop_table("enrollments")
    op.drop_table("users")
