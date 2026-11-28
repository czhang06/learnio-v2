from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_session
from ..deps import require_user
from ..models import User
from ..questions.schemas import QuestionOut
from . import service
from .schemas import MeOut

router = APIRouter(prefix="/api/me")


@router.get("", response_model=MeOut)
def me(user: User = Depends(require_user)):
    return service.me(user)


@router.put("/courses/{code}", status_code=204)
def enroll(code: str, user: User = Depends(require_user), session: Session = Depends(get_session)):
    service.enroll(session, user, code)


@router.delete("/courses/{code}", status_code=204)
def unenroll(code: str, user: User = Depends(require_user), session: Session = Depends(get_session)):
    service.unenroll(session, user, code)


@router.get("/saved", response_model=list[QuestionOut])
def saved(course_code: str | None = None, user: User = Depends(require_user), session: Session = Depends(get_session)):
    return service.saved(session, user, course_code)


@router.put("/saved/{question_id}", status_code=204)
def save(question_id: int, user: User = Depends(require_user), session: Session = Depends(get_session)):
    service.save(session, user, question_id)


@router.delete("/saved/{question_id}", status_code=204)
def unsave(question_id: int, user: User = Depends(require_user), session: Session = Depends(get_session)):
    service.unsave(session, user, question_id)
