from fastapi import APIRouter, Depends

from ..config import settings
from ..deps import require_admin

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/mode")
def mode():
    """Tell the frontend whether to offer course creation and uploads."""
    return {"read_only": settings.admin_key is not None}


@router.post("/admin/check", status_code=204, dependencies=[Depends(require_admin)])
def check_admin_key():
    """204 when the X-Admin-Key header is accepted, so the frontend can verify a key once."""
