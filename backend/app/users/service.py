from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, selectinload

from ..config import settings
from ..deps import get_course
from ..models import Question, User, enrollments, saved_questions
from ..questions.service import to_out
from .schemas import MeOut

ISSUER = "learnio-web"
AUDIENCE = "learnio-api"
_SEEN_EVERY = timedelta(hours=1)  # how often last_seen_at and profile fields are refreshed


def user_from_token(session: Session, token: str) -> User:
    """Verify a token from the frontend and return its user, created on first sight."""
    try:
        claims = jwt.decode(
            token,
            settings.auth_api_secret,
            algorithms=["HS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
            options={"require": ["sub", "exp"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(401, f"Invalid session token: {exc}") from exc

    email = str(claims.get("email") or "")
    role = "admin" if email.lower() in settings.admin_email_set else "user"
    profile = {"email": email, "name": str(claims.get("name") or ""), "picture": str(claims.get("picture") or "")}
    user = session.scalar(select(User).where(User.sub == str(claims["sub"])))
    now = datetime.now(timezone.utc)
    if user is None:
        user = User(sub=str(claims["sub"]), role=role, last_seen_at=now, **profile)
        session.add(user)
        session.commit()
    elif user.role != role or now - user.last_seen_at > _SEEN_EVERY or any(
        getattr(user, k) != v for k, v in profile.items()
    ):
        for k, v in profile.items():
            setattr(user, k, v)
        user.role, user.last_seen_at = role, now
        session.commit()
    return user


def me(user: User) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        is_admin=user.role == "admin",
        courses=list(user.courses),
    )


def enroll(session: Session, user: User, code: str) -> None:
    course = get_course(session, code)
    session.execute(
        pg_insert(enrollments).values(user_id=user.id, course_id=course.id).on_conflict_do_nothing()
    )
    session.commit()


def unenroll(session: Session, user: User, code: str) -> None:
    course = get_course(session, code)
    session.execute(delete(enrollments).where(enrollments.c.user_id == user.id, enrollments.c.course_id == course.id))
    session.commit()


def saved(session: Session, user: User, course_code: str | None):
    stmt = (
        select(Question)
        .join(saved_questions, saved_questions.c.question_id == Question.id)
        .where(saved_questions.c.user_id == user.id)
        .options(selectinload(Question.topics))
        .order_by(saved_questions.c.created_at.desc())
    )
    if course_code:
        stmt = stmt.where(Question.course_id == get_course(session, course_code).id)
    return [to_out(q) for q in session.scalars(stmt)]


def save(session: Session, user: User, question_id: int) -> None:
    if session.get(Question, question_id) is None:
        raise HTTPException(404, f"Unknown question {question_id}")
    session.execute(
        pg_insert(saved_questions).values(user_id=user.id, question_id=question_id).on_conflict_do_nothing()
    )
    session.commit()


def unsave(session: Session, user: User, question_id: int) -> None:
    session.execute(
        delete(saved_questions).where(
            saved_questions.c.user_id == user.id, saved_questions.c.question_id == question_id
        )
    )
    session.commit()
