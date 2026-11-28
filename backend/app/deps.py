"""Dependencies shared by several feature routers."""

import secrets

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_session
from .models import Course, User


def get_course(session: Session, code: str) -> Course:
    course = session.scalar(select(Course).where(Course.code == code))
    if course is None:
        raise HTTPException(404, f"Unknown course {code}")
    return course


def current_user(
    authorization: str | None = Header(None), session: Session = Depends(get_session)
) -> User | None:
    """The signed-in user, from an `Authorization: Bearer` token; None for guests."""
    from .users.service import user_from_token

    if not authorization or not settings.auth_api_secret:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Expected a bearer token")
    return user_from_token(session, token.strip())


def require_user(user: User | None = Depends(current_user)) -> User:
    if user is None:
        raise HTTPException(401, "Sign in to do this")
    return user


def require_admin(x_admin_key: str | None = Header(None), user: User | None = Depends(current_user)) -> None:
    """Allow writes from an admin account or with the admin key.

    With no admin key configured (local development, tests), writes are open.
    """
    if settings.admin_key is None:
        return
    if x_admin_key is not None and secrets.compare_digest(x_admin_key, settings.admin_key):
        return
    if user is not None and user.role == "admin":
        return
    raise HTTPException(403, "This demo is read-only. Adding courses and uploading need an admin account.")
