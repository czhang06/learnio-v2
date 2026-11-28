from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_session
from . import service
from .schemas import QuestionPage

router = APIRouter(prefix="/api")


@router.get("/questions", response_model=QuestionPage)
def list_questions(
    course_code: str,
    topic: str | None = None,
    offset: int = Query(0, ge=0),
    after: int | None = Query(None, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """List questions in id order.

    Prefer `after=<next_cursor>` (keyset pagination) over `offset`: it seeks
    straight to the page instead of scanning and discarding every earlier row.
    """
    return service.list_questions(
        session, course_code, topic=topic, offset=offset, after=after, limit=limit
    )
