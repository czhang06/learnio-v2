from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

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
    difficulty: int | None = None,
    offset: int = 0,
    limit: int = 20,
    session: Session = Depends(get_session),
):
    course = get_course(session, course_code)
    stmt = select(Question).where(Question.course_id == course.id)
    if topic:
        stmt = stmt.join(question_topics).join(Topic).where(Topic.name == topic)
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    stmt = stmt.order_by(Question.id).offset(offset).limit(min(limit, 100))
    items = [to_out(q) for q in session.scalars(stmt).all()]
    return QuestionPage(items=items)


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
    course = get_course(session, body.course_code)
    stmt = select(Question).where(
        Question.course_id == course.id,
        Question.difficulty.between(body.min_difficulty, body.max_difficulty),
    )
    if body.topics:
        stmt = stmt.where(
            Question.id.in_(
                select(question_topics.c.question_id)
                .join(Topic, Topic.id == question_topics.c.topic_id)
                .where(Topic.name.in_(body.topics))
            )
        )
    questions = session.scalars(stmt.order_by(func.random()).limit(body.num_questions)).all()
    session.add(UsageEvent(kind="exam_generated", client_id=client_id))
    session.commit()
    return ExamOut(course_code=course.code, questions=[to_out(q) for q in questions])
