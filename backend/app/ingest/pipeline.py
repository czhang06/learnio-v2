"""The ingestion steps a worker runs on one document: extract → segment → tag → stage.

Results land in draft_questions; nothing touches `questions` until the
document is published (see service.publish_document).
"""

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Course, Document, DocumentStatus, DraftQuestion, Question
import hashlib
import logging

from . import segmenter
from .images import display_size, render_questions, to_web
from .pdf_extract import extract_layout
from .storage import get_storage

log = logging.getLogger(__name__)

NO_QUESTIONS = (
    "No questions found in this PDF. Questions must start on their own line with a heading "
    'like "1.", "2)", "Question 3" or "4 (10 marks)".'
)


UNREADABLE = (
    "The text in this PDF can't be read: its fonts don't map to real characters, "
    "so it would need OCR. Try another copy of the exam."
)

_COMMON_WORDS = frozenset(
    "the of and to in is that for be this if what find show are with as on by it its an or".split()
)


class IngestError(Exception):
    """A failure worth showing to the uploader as the document's error message."""


def looks_unreadable(text: str) -> bool:
    """True when extraction produced gibberish rather than language.

    PDFs whose fonts have no character map extract as symbol soup. Real exam
    text, even heavy on maths, keeps a steady share of common English words:
    at least 18% of words in every readable file of the OCW set, against 3-6%
    in the two that extract as gibberish.
    """
    words = re.findall(r"[A-Za-z]{2,}", text)
    if len(words) < 50:
        return False  # too short to judge; let segmentation decide
    common = sum(w.lower() in _COMMON_WORDS for w in words)
    return common / len(words) < 0.10


def stage_questions(session: Session, doc: Document, data: bytes) -> None:
    """Replace the document's drafts with freshly segmented questions and mark it for review."""
    try:
        layout = extract_layout(data)
    except Exception as exc:  # corrupt or encrypted PDF
        raise IngestError(f"Could not read PDF: {exc}") from exc
    if looks_unreadable(layout.text):
        raise IngestError(UNREADABLE)

    found = segmenter.split_questions_with_lines(layout.text)
    if not found:
        raise IngestError(NO_QUESTIONS)
    pieces = [body for body, _, _ in found]
    images = _images(data, layout, found)

    course = session.get(Course, doc.course_id)
    labels = segmenter.tag_topics_with_llm(pieces, [t.name for t in course.topics])

    doc.drafts.clear()
    session.flush()
    hashes = []
    storage = get_storage()
    for position, (piece, names, image) in enumerate(zip(pieces, labels, images)):
        digest = segmenter.text_hash(piece)
        hashes.append(digest)
        image_key, size = None, (None, None)
        if image is not None:
            # The content hash in the name means a re-rendered image gets a new
            # URL, so browsers never show a stale copy of an immutable URL.
            web = to_web(image)
            image_key = f"images/{doc.id}-{position}-{hashlib.sha256(web.data).hexdigest()[:10]}.{web.extension}"
            storage.put(image_key, web.data, web.media_type)
            size = display_size(web.width, web.height)
        doc.drafts.append(
            DraftQuestion(
                position=position,
                text=piece,
                text_hash=digest,
                topic_names=list(names),
                image_key=image_key,
                image_width=size[0],
                image_height=size[1],
            )
        )

    existing = set(
        session.scalars(select(Question.text_hash).where(Question.course_id == doc.course_id, Question.text_hash.in_(hashes)))
    )
    doc.question_count = len(set(hashes) - existing)
    doc.status = DocumentStatus.NEEDS_REVIEW
    doc.error = None


def _images(data: bytes, layout, found) -> list[bytes | None]:
    """PNG crops of each question; without them the questions still have text."""
    try:
        return render_questions(data, layout.lines, [(first, end) for _, first, end in found])
    except Exception:
        log.exception("Rendering question images failed")
        return [None] * len(found)
