import random

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_course
from ..models import Question, Topic, UsageEvent, question_topics
from ..questions.service import to_out
from .schemas import ExamOut, ExamRequest


def generate_exam(session: Session, body: ExamRequest, client_id: str = "") -> ExamOut:
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
