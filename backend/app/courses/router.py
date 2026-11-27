from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_session
from ..deps import require_admin
from . import service
from .schemas import CourseIn, CourseOut

router = APIRouter(prefix="/api")


@router.post("/courses", response_model=CourseOut, status_code=201, dependencies=[Depends(require_admin)])
def create_course(body: CourseIn, session: Session = Depends(get_session)):
    return service.create_course(session, body)


@router.get("/courses", response_model=list[CourseOut])
def list_courses(session: Session = Depends(get_session)):
    return service.list_courses(session)


@router.get("/courses/{code}/topics", response_model=list[str])
def list_topics(code: str, session: Session = Depends(get_session)):
    return service.list_topic_names(session, code)
