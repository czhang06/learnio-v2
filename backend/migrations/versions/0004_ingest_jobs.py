"""Turn documents into ingestion jobs and stage questions for review.

Adds the job columns the background worker needs (stored PDF key, error,
attempt count, lock time), a partial index for the worker's claim query, and
the draft_questions table that holds questions until a document is published.
Existing statuses are mapped onto the new lifecycle.

Revision ID: 0004
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.alter_column("documents", "status", type_=sa.String(20), server_default="queued")
    op.add_column("documents", sa.Column("storage_key", sa.String(255)))
    op.add_column("documents", sa.Column("error", sa.Text))
    op.add_column("documents", sa.Column("attempts", sa.Integer, nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("locked_at", sa.DateTime(timezone=True)))
    op.add_column(
        "documents", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now())
    )
    # Old rows have no stored PDF, so anything that did not finish cannot be retried.
    op.execute("UPDATE documents SET status = 'published' WHERE status = 'done'")
    op.execute("UPDATE documents SET status = 'failed', error = 'No questions found in this PDF.' WHERE status = 'empty'")
    op.execute(
        "UPDATE documents SET status = 'failed', error = 'Uploaded before background ingestion; upload it again.' "
        "WHERE status NOT IN ('published', 'failed')"
    )
    op.create_index(
        "ix_documents_queued", "documents", ["created_at"], postgresql_where=sa.text("status = 'queued'")
    )
    op.create_table(
        "draft_questions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "document_id", sa.Integer, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("text_hash", sa.String(64), nullable=False),
        sa.Column("topic_names", sa.ARRAY(sa.String(120)), nullable=False, server_default="{}"),
    )
    op.create_index("ix_draft_questions_document_id", "draft_questions", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_draft_questions_document_id", table_name="draft_questions")
    op.drop_table("draft_questions")
    op.drop_index("ix_documents_queued", table_name="documents")
    op.execute("UPDATE documents SET status = 'done' WHERE status = 'published'")
    op.execute("UPDATE documents SET status = 'empty' WHERE status = 'needs_review'")
    for column in ("updated_at", "locked_at", "attempts", "error", "storage_key"):
        op.drop_column("documents", column)
    op.alter_column("documents", "status", type_=sa.String(16), server_default="pending")
