from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_course
from ..models import Document, Question, UsageEvent, question_topics
from . import segmenter
from .pdf_extract import extract_text


def upload_document(
    session: Session, *, course_code: str, kind: str, client_id: str, filename: str | None, data: bytes
) -> Document:
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    if not (filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files are supported")

    course = get_course(session, course_code)
    doc = Document(course_id=course.id, filename=filename or "upload.pdf", kind=kind, status="processing")
    session.add(doc)
    session.flush()

    try:
        text = extract_text(data)
    except Exception as exc:  # corrupt or encrypted PDF
        doc.status = "failed"
        session.commit()
        raise HTTPException(422, f"Could not read PDF: {exc}") from exc

    pieces = segmenter.split_questions(text)
    if not pieces:
        doc.status = "empty"
        session.commit()
        raise HTTPException(
            422,
            "No questions found in this PDF. Questions must start on their own line with a heading "
            'like "1.", "2)", "Question 3" or "4 (10 marks)".',
        )
    topic_names = [t.name for t in course.topics]
    labels = segmenter.tag_topics_with_llm(pieces, topic_names)
    topic_ids = {t.name: t.id for t in course.topics}

    stored = 0
    for piece, names in zip(pieces, labels):
        row = session.execute(
            pg_insert(Question)
            .values(course_id=course.id, document_id=doc.id, text=piece, text_hash=segmenter.text_hash(piece))
            .on_conflict_do_nothing(index_elements=["course_id", "text_hash"])
            .returning(Question.id)
        ).first()
        if row is None:  # duplicate question already in this course
            # Same words, possibly better layout: re-uploading a PDF refreshes
            # questions stored before line breaks were kept.
            session.execute(
                update(Question)
                .where(Question.course_id == course.id, Question.text_hash == segmenter.text_hash(piece))
                .values(text=piece)
            )
            continue
        stored += 1
        for name in names:
            if name in topic_ids:
                session.execute(question_topics.insert().values(question_id=row[0], topic_id=topic_ids[name]))

    doc.question_count = stored
    doc.status = "done"
    session.add(UsageEvent(kind="upload", client_id=client_id))
    session.commit()
    return doc
