import re

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from ..db import get_session
from ..deps import require_admin
from . import service
from .schemas import DocumentOut, DraftOut
from .storage import get_storage

_IMAGE_NAME = re.compile(r"\d{1,10}-\d{1,5}\.png")

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


@router.get("/images/{name}")
def question_image(name: str):
    """A question's PNG, as linked from `image_url`. Names are never reused
    (document id and position), so browsers may cache them for good."""
    if not _IMAGE_NAME.fullmatch(name):
        raise HTTPException(404, "Unknown image")
    try:
        data = get_storage().get(f"images/{name}")
    except Exception as exc:
        raise HTTPException(404, "Unknown image") from exc
    return Response(data, media_type="image/png", headers={"Cache-Control": "public, max-age=31536000, immutable"})
