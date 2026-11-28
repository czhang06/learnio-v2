from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_session
from ..deps import current_user, require_user
from ..models import User
from . import service
from .schemas import AttemptOut, AttemptSummary, ExamOut, ExamRequest, MarkIn

router = APIRouter(prefix="/api")


@router.post("/exams", response_model=ExamOut)
def generate_exam(
    body: ExamRequest,
    client_id: str = "",
    session: Session = Depends(get_session),
    user: User | None = Depends(current_user),
):
    return service.generate_exam(session, body, client_id, user)


@router.get("/attempts", response_model=list[AttemptSummary])
def history(
    course_code: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    return service.history(session, user, course_code, limit)


@router.get("/attempts/{attempt_id}", response_model=AttemptOut)
def get_attempt(attempt_id: int, user: User = Depends(require_user), session: Session = Depends(get_session)):
    return service.attempt_out(session, user, attempt_id)


@router.put("/attempts/{attempt_id}/answers/{question_id}", status_code=204)
def mark(
    attempt_id: int,
    question_id: int,
    body: MarkIn,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    service.mark(session, user, attempt_id, question_id, body.result)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptOut)
def submit(attempt_id: int, user: User = Depends(require_user), session: Session = Depends(get_session)):
    return service.submit(session, user, attempt_id)


@router.post("/attempts/{attempt_id}/retry", response_model=ExamOut)
def retry(attempt_id: int, user: User = Depends(require_user), session: Session = Depends(get_session)):
    return service.retry(session, user, attempt_id)
