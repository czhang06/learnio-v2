"""Shared fixtures. Runs against a real PostgreSQL given by DATABASE_URL."""

import os

DATABASE_URL = os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://learnio:learnio@localhost:5432/learnio"
)

import itertools  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, select, text  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from app import models  # noqa: E402,F401  (registers tables on Base.metadata)
from app.db import Base, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Course, Question, Topic  # noqa: E402
from app.services.segmenter import text_hash  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture(autouse=True)
def _clean_tables(engine):
    """Empty every table (and reset ids) before each test."""
    names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {names} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def db_session(engine):
    with Session(engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def client(engine):
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override():
        with factory() as session:
            yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def make_course(db_session):
    """make_course(code="CS101", topics=("arrays", "graphs")) -> Course"""

    def _make(code="CS101", name="Intro", topics=("arrays", "graphs")):
        course = Course(code=code, name=name, topics=[Topic(name=t) for t in topics])
        db_session.add(course)
        db_session.commit()
        return course

    return _make


@pytest.fixture
def add_questions(db_session):
    """add_questions(course, count, topics=(), difficulty=3) -> list of question ids.

    `difficulty` may be an int or a list that is cycled over the new questions.
    Every question gets unique text, so nothing collides on (course_id, text_hash).
    Returned ids are in insertion (= ascending id) order.
    """
    counter = itertools.count(1)

    def _add(course, count=1, *, topics=(), difficulty=3):
        topic_rows = []
        if topics:
            topic_rows = list(
                db_session.scalars(
                    select(Topic).where(Topic.course_id == course.id, Topic.name.in_(list(topics)))
                )
            )
            assert len(topic_rows) == len(set(topics)), "unknown topic in fixture call"
        difficulties = itertools.cycle([difficulty] if isinstance(difficulty, int) else difficulty)
        rows = []
        for _ in range(count):
            body = f"Seeded question number {next(counter)} about something testable"
            rows.append(
                Question(
                    course_id=course.id,
                    text=body,
                    text_hash=text_hash(body),
                    difficulty=next(difficulties),
                    topics=list(topic_rows),
                )
            )
        db_session.add_all(rows)
        db_session.commit()
        return [r.id for r in rows]

    return _add
