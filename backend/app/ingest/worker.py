"""Background ingestion worker backed by the documents table.

A job is a document row in status `queued`. Workers claim one with
SELECT ... FOR UPDATE SKIP LOCKED, so several worker loops (or processes)
never pick the same job. A job left in `processing` longer than
`job_timeout_seconds` (its worker died mid-run) is claimed again, up to
`max_attempts` times, then marked failed.

On the free Render plan there is no separate worker service, so the loop runs
inside the API process (started from main.py). Jobs live in Postgres, so a
restart or an idle spin-down only delays them.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, sessionmaker

from ..config import settings
from ..db import SessionLocal
from ..models import Document, DocumentStatus
from .pipeline import IngestError, stage_questions
from .storage import get_storage

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def claim_next(session: Session) -> Document | None:
    """Lock the oldest runnable job, mark it processing and commit."""
    stale_before = _now() - timedelta(seconds=settings.job_timeout_seconds)
    stale = (Document.status == DocumentStatus.PROCESSING) & (Document.locked_at < stale_before)
    session.execute(
        update(Document)
        .where(stale, Document.attempts >= settings.max_attempts)
        .values(status=DocumentStatus.FAILED, error=f"Gave up after {settings.max_attempts} attempts.", locked_at=None)
    )
    doc = session.scalar(
        select(Document)
        .where(or_(Document.status == DocumentStatus.QUEUED, stale))
        .order_by(Document.created_at, Document.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if doc is None:
        session.commit()
        return None
    doc.status = DocumentStatus.PROCESSING
    doc.locked_at = _now()
    doc.attempts += 1
    session.commit()
    return doc


def process_document(session: Session, doc: Document) -> None:
    """Run the pipeline on one document and record the outcome on it."""
    from .service import publish_document

    doc.status = DocumentStatus.PROCESSING
    try:
        stage_questions(session, doc, get_storage().get(doc.storage_key))
    except Exception as exc:
        session.rollback()
        if not isinstance(exc, IngestError):
            log.exception("Ingesting document %s failed", doc.id)
        doc.status = DocumentStatus.FAILED
        doc.error = str(exc) or exc.__class__.__name__
        doc.locked_at = None
        session.commit()
        return
    doc.locked_at = None
    session.commit()
    if settings.auto_publish:
        publish_document(session, doc)


def run_once(factory: sessionmaker = SessionLocal) -> bool:
    """Process one job if there is one. Returns whether a job was found."""
    with factory() as session:
        doc = claim_next(session)
        if doc is None:
            return False
        process_document(session, doc)
        return True


async def run_forever(stop: asyncio.Event, factory: sessionmaker = SessionLocal) -> None:
    """Poll for jobs until `stop` is set. Blocking work runs in a thread."""
    while not stop.is_set():
        try:
            found = await asyncio.to_thread(run_once, factory)
        except Exception:  # database unreachable, etc.: keep the loop alive
            log.exception("Ingestion worker iteration failed")
            found = False
        if not found:
            try:
                await asyncio.wait_for(stop.wait(), timeout=settings.worker_poll_seconds)
            except TimeoutError:
                pass
