"""Dependencies shared by several feature routers."""

import secrets

from fastapi import Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import Course


def get_course(session: Session, code: str) -> Course:
    course = session.scalar(select(Course).where(Course.code == code))
    if course is None:
        raise HTTPException(404, f"Unknown course {code}")
    return course


def require_admin(x_admin_key: str | None = Header(None)) -> None:
    """Reject writes without the admin key, when one is configured."""
    if settings.admin_key is None:
        return
    if x_admin_key is None or not secrets.compare_digest(x_admin_key, settings.admin_key):
        raise HTTPException(403, "This demo is read-only. Adding courses and uploading need the admin key.")
