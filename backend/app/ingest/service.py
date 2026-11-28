import logging

import fitz  # PyMuPDF
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_course
from ..models import Document, DocumentStatus, Question, Topic, UsageEvent, question_topics
from .storage import get_storage

log = logging.getLogger(__name__)


def get_document(session: Session, document_id: int) -> Document:
    doc = session.get(Document, document_id)
    if doc is None:
        raise HTTPException(404, f"Unknown document {document_id}")
    return doc


def _check_pdf(data: bytes) -> None:
    """Reject unreadable files now, so the uploader hears about them immediately."""
    try:
        with fitz.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass:
                raise ValueError("the PDF is password protected")
    except Exception as exc:
        raise HTTPException(422, f"Could not read PDF: {exc}") from exc


def upload_document(
    session: Session, *, course_code: str, kind: str, client_id: str, filename: str | None, data: bytes
) -> Document:
    """Validate and store the PDF, then queue it for the worker."""
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    if not (filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files are supported")
    course = get_course(session, course_code)
    _check_pdf(data)

    doc = Document(course_id=course.id, filename=filename or "upload.pdf", kind=kind, status=DocumentStatus.QUEUED)
    session.add(doc)
    session.flush()
    doc.storage_key = f"documents/{doc.id}.pdf"
    try:
        get_storage().put(doc.storage_key, data)
    except Exception as exc:  # misconfigured bucket, bad keys, storage outage
        log.exception("Storing %s failed", doc.storage_key)
        session.rollback()
        raise HTTPException(503, f"Could not save the PDF to storage ({exc.__class__.__name__}: {exc})") from exc
    session.add(UsageEvent(kind="upload", client_id=client_id))
    session.commit()

    if settings.ingest_inline:
        from .worker import process_document

        process_document(session, doc)
    return doc


def publish_document(session: Session, doc: Document) -> Document:
    """Copy a reviewed document's drafts into the question bank.

    A draft whose text is already in the course is not stored again, but its
    text and image replace the stored ones: same words, possibly better layout,
    so re-uploading a PDF refreshes questions stored by an older ingester.
    """
    if doc.status != DocumentStatus.NEEDS_REVIEW:
        raise HTTPException(409, f"Only documents awaiting review can be published (this one is {doc.status})")
    topic_ids = dict(session.execute(select(Topic.name, Topic.id).where(Topic.course_id == doc.course_id)).all())
    stored = 0
    for draft in doc.drafts:
        row = session.execute(
            pg_insert(Question)
            .values(
                course_id=doc.course_id,
                document_id=doc.id,
                text=draft.text,
                text_hash=draft.text_hash,
                image_key=draft.image_key,
            )
            .on_conflict_do_nothing(index_elements=["course_id", "text_hash"])
            .returning(Question.id)
        ).first()
        if row is None:  # already in this course
            session.execute(
                update(Question)
                .where(Question.course_id == doc.course_id, Question.text_hash == draft.text_hash)
                .values(text=draft.text, image_key=draft.image_key)
            )
            continue
        stored += 1
        for name in draft.topic_names:
            if name in topic_ids:
                session.execute(question_topics.insert().values(question_id=row[0], topic_id=topic_ids[name]))
    doc.drafts.clear()
    doc.question_count = stored
    doc.status = DocumentStatus.PUBLISHED
    session.commit()
    return doc


def retry_document(session: Session, doc: Document) -> Document:
    """Put a failed document back in the queue, to run again on its stored PDF."""
    if doc.status != DocumentStatus.FAILED:
        raise HTTPException(409, f"Only failed documents can be retried (this one is {doc.status})")
    if doc.storage_key is None:
        raise HTTPException(409, "This document was uploaded before PDFs were stored; upload it again.")
    doc.status = DocumentStatus.QUEUED
    doc.error = None
    doc.attempts = 0
    doc.locked_at = None
    session.commit()
    return doc
