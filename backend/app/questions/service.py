from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..deps import get_course
from ..models import Question, Topic, question_topics
from .schemas import QuestionOut, QuestionPage


def to_out(q: Question) -> QuestionOut:
    return QuestionOut(id=q.id, text=q.text, topics=[t.name for t in q.topics])


def list_questions(
    session: Session,
    course_code: str,
    *,
    topic: str | None,
    offset: int,
    after: int | None,
    limit: int,
) -> QuestionPage:
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
    stmt = stmt.where(id_col > after) if after is not None else stmt.offset(offset)
    rows = session.scalars(stmt.options(selectinload(Question.topics)).limit(limit)).all()
    items = [to_out(q) for q in rows]
    return QuestionPage(items=items, next_cursor=items[-1].id if len(items) == limit else None)
