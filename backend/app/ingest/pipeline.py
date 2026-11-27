"""The ingestion steps a worker runs on one document: extract → segment → tag → stage.

Results land in draft_questions; nothing touches `questions` until the
document is published (see service.publish_document).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Course, Document, DocumentStatus, DraftQuestion, Question
from . import segmenter
from .pdf_extract import extract_text

NO_QUESTIONS = (
    "No questions found in this PDF. Questions must start on their own line with a heading "
    'like "1.", "2)", "Question 3" or "4 (10 marks)".'
)


class IngestError(Exception):
    """A failure worth showing to the uploader as the document's error message."""


def stage_questions(session: Session, doc: Document, data: bytes) -> None:
    """Replace the document's drafts with freshly segmented questions and mark it for review."""
    try:
        text = extract_text(data)
    except Exception as exc:  # corrupt or encrypted PDF
        raise IngestError(f"Could not read PDF: {exc}") from exc

    pieces = segmenter.split_questions(text)
    if not pieces:
        raise IngestError(NO_QUESTIONS)

    course = session.get(Course, doc.course_id)
    labels = segmenter.tag_topics_with_llm(pieces, [t.name for t in course.topics])

    doc.drafts.clear()
    session.flush()
    hashes = []
    for position, (piece, names) in enumerate(zip(pieces, labels)):
        digest = segmenter.text_hash(piece)
        hashes.append(digest)
        doc.drafts.append(DraftQuestion(position=position, text=piece, text_hash=digest, topic_names=list(names)))

    existing = set(
        session.scalars(select(Question.text_hash).where(Question.course_id == doc.course_id, Question.text_hash.in_(hashes)))
    )
    doc.question_count = len(set(hashes) - existing)
    doc.status = DocumentStatus.NEEDS_REVIEW
    doc.error = None
