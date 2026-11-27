from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import get_course
from ..models import Course, Topic
from .schemas import CourseIn


def create_course(session: Session, body: CourseIn) -> Course:
    if session.scalar(select(Course).where(Course.code == body.code)):
        raise HTTPException(409, "Course already exists")
    course = Course(code=body.code, name=body.name)
    course.topics = [Topic(name=name) for name in dict.fromkeys(body.topics)]
    session.add(course)
    session.commit()
    return course


def list_courses(session: Session) -> Sequence[Course]:
    return session.scalars(select(Course).order_by(Course.code)).all()


def list_topic_names(session: Session, code: str) -> list[str]:
    course = get_course(session, code)
    return [t.name for t in sorted(course.topics, key=lambda t: t.name)]
