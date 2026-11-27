from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from ..db import get_session
from ..deps import require_admin
from . import service
from .schemas import DocumentOut, DraftOut

router = APIRouter(prefix="/api")


@router.post("/documents", response_model=DocumentOut, status_code=202, dependencies=[Depends(require_admin)])
async def upload_document(
    course_code: str = Form(...),
    kind: str = Form("exam"),
    client_id: str = Form(""),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Store the PDF and queue it. Poll GET /documents/{id} for the outcome."""
    data = await file.read()
    return service.upload_document(
        session, course_code=course_code, kind=kind, client_id=client_id, filename=file.filename, data=data
    )


@router.get("/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, session: Session = Depends(get_session)):
    return service.get_document(session, document_id)


@router.get("/documents/{document_id}/drafts", response_model=list[DraftOut], dependencies=[Depends(require_admin)])
def list_drafts(document_id: int, session: Session = Depends(get_session)):
    return service.get_document(session, document_id).drafts


@router.post("/documents/{document_id}/publish", response_model=DocumentOut, dependencies=[Depends(require_admin)])
def publish_document(document_id: int, session: Session = Depends(get_session)):
    return service.publish_document(session, service.get_document(session, document_id))


@router.post("/documents/{document_id}/retry", response_model=DocumentOut, dependencies=[Depends(require_admin)])
def retry_document(document_id: int, session: Session = Depends(get_session)):
    return service.retry_document(session, service.get_document(session, document_id))
