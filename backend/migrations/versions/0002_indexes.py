"""Add indexes for course-scoped listing and topic lookups.

Revision ID: 0002
"""

from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    # Course-scoped scans in id order (listing, keyset pagination).
    op.create_index("ix_questions_course_id_id", "questions", ["course_id", "id"])
    # Reverse lookup of the (question_id, topic_id) primary key: all questions for a topic.
    op.create_index("ix_question_topics_topic_question", "question_topics", ["topic_id", "question_id"])


def downgrade() -> None:
    op.drop_index("ix_question_topics_topic_question", table_name="question_topics")
    op.drop_index("ix_questions_course_id_id", table_name="questions")
