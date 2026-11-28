from datetime import datetime

from sqlalchemy import (
    ARRAY,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Column,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

question_topics = Table(
    "question_topics",
    Base.metadata,
    Column("question_id", ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("topic_id", ForeignKey("topics.id", ondelete="CASCADE"), primary_key=True),
)


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(200), default="")

    topics: Mapped[list["Topic"]] = relationship(back_populates="course")


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (UniqueConstraint("course_id", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(120))

    course: Mapped[Course] = relationship(back_populates="topics")


class DocumentStatus:
    """Ingestion lifecycle. A failed job can be retried, which puts it back in the queue."""

    QUEUED = "queued"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    PUBLISHED = "published"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        # The worker's claim query only ever looks at queued rows, oldest first.
        Index("ix_documents_queued", "created_at", postgresql_where=text("status = 'queued'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(16), default="exam")  # exam | syllabus
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.QUEUED)
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    storage_key: Mapped[str | None] = mapped_column(String(255))
    error: Mapped[str | None] = mapped_column(Text)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    drafts: Mapped[list["DraftQuestion"]] = relationship(
        back_populates="document", order_by="DraftQuestion.position", cascade="all, delete-orphan"
    )


class DraftQuestion(Base):
    """A question found by ingestion, held back until its document is published.

    Keeping drafts out of `questions` means listing and exam sampling never
    need to filter on review state, so their indexes stay exactly as benchmarked.
    """

    __tablename__ = "draft_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(64))
    topic_names: Mapped[list[str]] = mapped_column(ARRAY(String(120)), default=list)
    image_key: Mapped[str | None] = mapped_column(String(255))

    document: Mapped[Document] = relationship(back_populates="drafts")


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("course_id", "text_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(64))
    image_key: Mapped[str | None] = mapped_column(String(255))  # PNG of the question's region of its PDF
    rand: Mapped[float] = mapped_column(Float(53), server_default=func.random())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    topics: Mapped[list[Topic]] = relationship(secondary=question_topics)


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(32))  # upload | exam_generated | exam_viewed
    client_id: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """Someone signed in through the frontend. `sub` is the identity
    provider's stable id for them (Google's account id)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    picture: Mapped[str] = mapped_column(String(500), default="")
    role: Mapped[str] = mapped_column(String(16), default="user", server_default="user")  # user | admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    courses: Mapped[list[Course]] = relationship(secondary="enrollments", order_by="Course.code")


enrollments = Table(
    "enrollments",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("course_id", ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

saved_questions = Table(
    "saved_questions",
    Base.metadata,
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("question_id", ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)


class Attempt(Base):
    """A practice exam generated for a signed-in user."""

    __tablename__ = "attempts"
    __table_args__ = (Index("ix_attempts_user_course", "user_id", "course_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    topics: Mapped[list[str]] = mapped_column(ARRAY(String(120)), default=list, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    course: Mapped[Course] = relationship()
    answers: Mapped[list["AttemptAnswer"]] = relationship(
        back_populates="attempt", order_by="AttemptAnswer.position", cascade="all, delete-orphan"
    )


class AttemptAnswer(Base):
    """One question of an attempt and how the user marked themselves on it."""

    __tablename__ = "attempt_answers"
    __table_args__ = (
        CheckConstraint("result IN ('right', 'wrong', 'skipped')", name="ck_attempt_answers_result"),
        Index("ix_attempt_answers_question", "question_id"),
    )

    attempt_id: Mapped[int] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer)
    result: Mapped[str | None] = mapped_column(String(8))  # right | wrong | skipped; None until marked

    attempt: Mapped[Attempt] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship()
