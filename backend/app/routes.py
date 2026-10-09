import random

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from .config import settings
from .db import get_session
from .models import Course, Document, Question, Topic, UsageEvent, question_topics
from .schemas import (
    CourseIn,
    CourseOut,
    DocumentOut,
    ExamOut,
    ExamRequest,
    QuestionOut,
    QuestionPage,
)
from .services import segmenter
from .services.pdf_extract import extract_text

router = APIRouter(prefix="/api")


def to_out(q: Question) -> QuestionOut:
    return QuestionOut(id=q.id, text=q.text, difficulty=q.difficulty, topics=[t.name for t in q.topics])


def get_course(session: Session, code: str) -> Course:
    course = session.scalar(select(Course).where(Course.code == code))
    if course is None:
        raise HTTPException(404, f"Unknown course {code}")
    return course


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/courses", response_model=CourseOut, status_code=201)
def create_course(body: CourseIn, session: Session = Depends(get_session)):
    if session.scalar(select(Course).where(Course.code == body.code)):
        raise HTTPException(409, "Course already exists")
    course = Course(code=body.code, name=body.name)
    course.topics = [Topic(name=name) for name in dict.fromkeys(body.topics)]
    session.add(course)
    session.commit()
    return course


@router.get("/courses", response_model=list[CourseOut])
def list_courses(session: Session = Depends(get_session)):
    return session.scalars(select(Course).order_by(Course.code)).all()


@router.get("/courses/{code}/topics", response_model=list[str])
def list_topics(code: str, session: Session = Depends(get_session)):
    course = get_course(session, code)
    return [t.name for t in sorted(course.topics, key=lambda t: t.name)]


@router.get("/questions", response_model=QuestionPage)
def list_questions(
    course_code: str,
    topic: str | None = None,
    difficulty: int | None = Query(None, ge=1, le=5),
    offset: int = Query(0, ge=0),
    after: int | None = Query(None, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """List questions in id order.

    Prefer `after=<next_cursor>` (keyset pagination) over `offset`: it seeks
    straight to the page instead of scanning and discarding every earlier row.
    """
    course = get_course(session, course_code)
    if topic:
        topic_id = session.scalar(select(Topic.id).where(Topic.course_id == course.id, Topic.name == topic))
        if topic_id is None:
            return QuestionPage(items=[])
        # Resolve the topic first so the planner walks the (topic_id, question_id)
        # index in id order instead of scanning the whole link table.
        stmt = (
            select(Question)
            .join(question_topics, question_topics.c.question_id == Question.id)
            .where(question_topics.c.topic_id == topic_id)
            .order_by(question_topics.c.question_id)
        )
        id_col = question_topics.c.question_id
    else:
        stmt = select(Question).where(Question.course_id == course.id).order_by(Question.id)
        id_col = Question.id
    if difficulty is not None:
        stmt = stmt.where(Question.difficulty == difficulty)
    stmt = stmt.where(id_col > after) if after is not None else stmt.offset(offset)
    rows = session.scalars(stmt.options(selectinload(Question.topics)).limit(limit)).all()
    items = [to_out(q) for q in rows]
    return QuestionPage(items=items, next_cursor=items[-1].id if len(items) == limit else None)


@router.post("/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    course_code: str = Form(...),
    kind: str = Form("exam"),
    client_id: str = Form(""),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    data = await file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files are supported")

    course = get_course(session, course_code)
    doc = Document(course_id=course.id, filename=file.filename or "upload.pdf", kind=kind, status="processing")
    session.add(doc)
    session.flush()

    try:
        text = extract_text(data)
    except Exception as exc:  # corrupt or encrypted PDF
        doc.status = "failed"
        session.commit()
        raise HTTPException(422, f"Could not read PDF: {exc}") from exc

    pieces = segmenter.split_questions(text)
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


@router.post("/exams", response_model=ExamOut)
def generate_exam(body: ExamRequest, client_id: str = "", session: Session = Depends(get_session)):
    """Sample questions at random using the stored `rand` key.

    Pick a random threshold, read the next N matching rows in (course_id, rand)
    order, and wrap around to the start if fewer than N remain. Each question has
    the same chance of appearing; questions adjacent in `rand` order tend to
    appear together across exams, which is fine for practice exams.
    """
    course = get_course(session, body.course_code)
    base = (
        select(Question)
        .options(selectinload(Question.topics))
        .where(
            Question.course_id == course.id,
            Question.difficulty.between(body.min_difficulty, body.max_difficulty),
        )
    )
    if body.topics:
        topic_ids = select(Topic.id).where(Topic.course_id == course.id, Topic.name.in_(body.topics))
        base = base.where(
            Question.id.in_(select(question_topics.c.question_id).where(question_topics.c.topic_id.in_(topic_ids)))
        )

    n = body.num_questions
    threshold = random.random()
    questions = list(session.scalars(base.where(Question.rand >= threshold).order_by(Question.rand).limit(n)))
    if len(questions) < n:  # wrapped past the end of the index
        questions += session.scalars(
            base.where(Question.rand < threshold).order_by(Question.rand).limit(n - len(questions))
        )
    session.add(UsageEvent(kind="exam_generated", client_id=client_id))
    session.commit()
    return ExamOut(course_code=course.code, questions=[to_out(q) for q in questions])
