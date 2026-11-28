from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_session
from . import service
from .schemas import ExamOut, ExamRequest

router = APIRouter(prefix="/api")


@router.post("/exams", response_model=ExamOut)
def generate_exam(body: ExamRequest, client_id: str = "", session: Session = Depends(get_session)):
    return service.generate_exam(session, body, client_id)
