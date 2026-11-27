from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..db import get_session
from ..deps import require_admin
from . import service
from .schemas import DocumentOut

router = APIRouter(prefix="/api")


@router.post("/documents", response_model=DocumentOut, status_code=201, dependencies=[Depends(require_admin)])
async def upload_document(
    course_code: str = Form(...),
    kind: str = Form("exam"),
    client_id: str = Form(""),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    data = await file.read()
    return service.upload_document(
        session, course_code=course_code, kind=kind, client_id=client_id, filename=file.filename, data=data
    )
