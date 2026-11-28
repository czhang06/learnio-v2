"""The ingestion job lifecycle: queue, claim, process, review, publish, retry."""

import asyncio
from datetime import datetime, timedelta, timezone

import fitz  # PyMuPDF
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.ingest import segmenter, worker
from app.main import app
from app.models import Document, Question
from tests.test_api_documents import QUESTIONS, make_pdf, upload


@pytest.fixture
def factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def queued(monkeypatch):
    """Uploads only queue the job; the test runs the worker by hand."""
    monkeypatch.setattr(settings, "ingest_inline", False)


@pytest.fixture
def review(monkeypatch):
    monkeypatch.setattr(settings, "auto_publish", False)


def questions(client):
    return client.get("/api/questions", params={"course_code": "CS101"}).json()["items"]


def status(client, doc_id):
    return client.get(f"/api/documents/{doc_id}").json()


def test_upload_returns_before_the_job_runs(client, make_course, queued, factory):
    make_course()
    r = upload(client, make_pdf())
    assert r.status_code == 202
    doc_id = r.json()["id"]
    assert r.json()["status"] == "queued"
    assert questions(client) == []

    assert worker.run_once(factory) is True
    assert status(client, doc_id) | {"id": 0} == {
        "id": 0, "filename": "exam.pdf", "status": "published", "question_count": 3, "error": None,
    }
    assert len(questions(client)) == 3
    assert worker.run_once(factory) is False


def test_uploaded_pdf_is_stored_for_reruns(client, make_course, queued, db_session):
    from app.ingest.storage import get_storage

    make_course()
    pdf = make_pdf()
    doc_id = upload(client, pdf).json()["id"]
    doc = db_session.get(Document, doc_id)
    assert doc.storage_key == f"documents/{doc_id}.pdf"
    assert get_storage().get(doc.storage_key) == pdf


def test_review_holds_questions_until_published(client, make_course, review):
    make_course(topics=("recursion", "graphs"))
    body = upload(client, make_pdf()).json()
    assert (body["status"], body["question_count"]) == ("needs_review", 3)
    assert questions(client) == []

    drafts = client.get(f"/api/documents/{body['id']}/drafts").json()
    assert [d["text"] for d in drafts] == QUESTIONS
    assert drafts[0]["topic_names"] == ["recursion"]

    published = client.post(f"/api/documents/{body['id']}/publish").json()
    assert (published["status"], published["question_count"]) == ("published", 3)
    assert {q["text"]: q["topics"] for q in questions(client)}[QUESTIONS[2]] == ["graphs"]
    assert client.get(f"/api/documents/{body['id']}/drafts").json() == []


def test_review_count_excludes_questions_already_in_the_course(client, make_course, review):
    make_course()
    first = upload(client, make_pdf(QUESTIONS[:2])).json()
    client.post(f"/api/documents/{first['id']}/publish")
    assert upload(client, make_pdf()).json()["question_count"] == 1


def test_only_documents_in_review_can_be_published(client, make_course):
    make_course()
    doc_id = upload(client, make_pdf()).json()["id"]
    r = client.post(f"/api/documents/{doc_id}/publish")
    assert r.status_code == 409
    assert "published" in r.json()["detail"]


def test_unexpected_error_fails_the_job_and_retry_reruns_it(client, make_course, queued, factory, monkeypatch):
    make_course()
    doc_id = upload(client, make_pdf()).json()["id"]
    real = segmenter.split_questions

    def boom(text):
        raise RuntimeError("segmenter exploded")

    monkeypatch.setattr(segmenter, "split_questions", boom)
    worker.run_once(factory)
    assert (status(client, doc_id)["status"], status(client, doc_id)["error"]) == ("failed", "segmenter exploded")

    monkeypatch.setattr(segmenter, "split_questions", real)
    retried = client.post(f"/api/documents/{doc_id}/retry").json()
    assert (retried["status"], retried["error"]) == ("queued", None)
    worker.run_once(factory)
    assert status(client, doc_id)["status"] == "published"
    assert len(questions(client)) == 3


def test_only_failed_documents_can_be_retried(client, make_course):
    make_course()
    doc_id = upload(client, make_pdf()).json()["id"]
    assert client.post(f"/api/documents/{doc_id}/retry").status_code == 409


def test_documents_without_a_stored_pdf_cannot_be_retried(client, make_course, db_session):
    course = make_course()
    doc = Document(course_id=course.id, filename="old.pdf", status="failed")
    db_session.add(doc)
    db_session.commit()
    r = client.post(f"/api/documents/{doc.id}/retry")
    assert r.status_code == 409
    assert "upload it again" in r.json()["detail"]


def test_unknown_document_returns_404(client):
    assert client.get("/api/documents/99").status_code == 404


def test_password_protected_pdf_is_rejected_at_upload(client, make_course):
    make_course()
    doc = fitz.open()
    doc.new_page().insert_text((50, 72), "1. A secret question.")
    data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="pw")
    doc.close()
    r = upload(client, data)
    assert r.status_code == 422
    assert "password" in r.json()["detail"]


def _stale(db_session, doc_id, attempts):
    doc = db_session.get(Document, doc_id)
    doc.status = "processing"
    doc.attempts = attempts
    doc.locked_at = datetime.now(timezone.utc) - timedelta(seconds=settings.job_timeout_seconds + 60)
    db_session.commit()


def test_job_abandoned_mid_run_is_claimed_again(client, make_course, queued, factory, db_session):
    make_course()
    doc_id = upload(client, make_pdf()).json()["id"]
    _stale(db_session, doc_id, attempts=1)
    assert worker.run_once(factory) is True
    assert status(client, doc_id)["status"] == "published"
    db_session.expire_all()
    assert db_session.get(Document, doc_id).attempts == 2


def test_recently_claimed_job_is_left_alone(client, make_course, queued, factory, db_session):
    make_course()
    doc_id = upload(client, make_pdf()).json()["id"]
    doc = db_session.get(Document, doc_id)
    doc.status, doc.locked_at = "processing", datetime.now(timezone.utc)
    db_session.commit()
    assert worker.run_once(factory) is False


def test_job_that_keeps_dying_is_given_up_on(client, make_course, queued, factory, db_session):
    make_course()
    doc_id = upload(client, make_pdf()).json()["id"]
    _stale(db_session, doc_id, attempts=settings.max_attempts)
    assert worker.run_once(factory) is False
    assert status(client, doc_id)["status"] == "failed"
    assert "Gave up" in status(client, doc_id)["error"]


def test_a_job_locked_by_another_worker_is_skipped(client, make_course, queued, factory):
    make_course()
    upload(client, make_pdf())
    with factory() as other:
        other.scalar(select(Document).with_for_update())  # another worker holds the row
        assert worker.run_once(factory) is False
    assert worker.run_once(factory) is True


def test_worker_loop_processes_jobs_until_stopped(client, make_course, queued, factory, monkeypatch, db_session):
    make_course()
    upload(client, make_pdf())
    monkeypatch.setattr(settings, "worker_poll_seconds", 0.01)

    async def main():
        stop = asyncio.Event()
        task = asyncio.create_task(worker.run_forever(stop, factory))
        for _ in range(500):
            await asyncio.sleep(0.01)
            with factory() as s:
                if s.scalar(select(Document.status)) == "published":
                    break
        stop.set()
        await asyncio.wait_for(task, 5)

    asyncio.run(main())
    assert len(db_session.scalars(select(Question)).all()) == 3


def test_worker_loop_survives_a_failing_iteration(monkeypatch):
    monkeypatch.setattr(settings, "worker_poll_seconds", 0.01)
    calls = 0

    def broken_factory():
        nonlocal calls
        calls += 1
        raise ConnectionError("database unreachable")

    async def main():
        stop = asyncio.Event()
        task = asyncio.create_task(worker.run_forever(stop, broken_factory))
        while calls < 2:
            await asyncio.sleep(0.01)
        stop.set()
        await asyncio.wait_for(task, 5)

    asyncio.run(main())
    assert calls >= 2


def test_app_starts_and_stops_the_worker(monkeypatch):
    monkeypatch.setattr(settings, "run_worker", True)
    monkeypatch.setattr(settings, "worker_poll_seconds", 0.01)
    with TestClient(app) as c:
        assert c.get("/api/health").json() == {"status": "ok"}


def test_storage_failure_returns_a_readable_error(client, make_course, db_session, monkeypatch):
    from app.ingest import service

    class BrokenStorage:
        def put(self, key, data):
            raise PermissionError("InvalidAccessKeyId")

    monkeypatch.setattr(service, "get_storage", lambda: BrokenStorage())
    make_course()
    r = upload(client, make_pdf())
    assert r.status_code == 503
    assert "InvalidAccessKeyId" in r.json()["detail"]
    assert db_session.scalars(select(Document)).all() == []


def test_unexpected_errors_keep_cors_headers(client, make_course, monkeypatch):
    from app.ingest import service

    def boom(*args, **kwargs):
        raise RuntimeError("unexpected")

    monkeypatch.setattr(service, "upload_document", boom)
    make_course()
    r = client.post(
        "/api/documents",
        data={"course_code": "CS101"},
        files={"file": ("exam.pdf", make_pdf(), "application/pdf")},
        headers={"Origin": "https://learnio.example"},
    )
    assert r.status_code == 500
    assert r.headers["access-control-allow-origin"] == "*"
    assert "went wrong" in r.json()["detail"]


def test_auto_publish_never_commits_the_review_state(client, make_course, queued, factory, db_session, monkeypatch):
    """Staging and publishing are one transaction: if publishing fails, the job
    fails as a whole rather than being left visible in needs_review."""
    from app.ingest import service

    def broken_publish(session, doc):
        raise RuntimeError("publish failed")

    monkeypatch.setattr(service, "publish_document", broken_publish)
    make_course()
    doc_id = upload(client, make_pdf()).json()["id"]
    worker.run_once(factory)
    body = status(client, doc_id)
    assert (body["status"], body["error"]) == ("failed", "publish failed")
    assert client.get(f"/api/documents/{doc_id}/drafts").json() == []
    assert questions(client) == []


def test_pdf_with_unreadable_text_fails_with_an_explanation(client, make_course, monkeypatch):
    from app.ingest import pipeline

    gibberish = " ".join(["Q~¤ ¥§~} yG9<QyHE ­y{ ~{98:8¤"] * 30)
    monkeypatch.setattr(pipeline, "extract_text", lambda data: "1. " + gibberish)
    make_course()
    body = upload(client, make_pdf()).json()
    assert body["status"] == "failed"
    assert "OCR" in body["error"]


def test_readable_text_is_not_flagged_as_unreadable():
    from app.ingest.pipeline import looks_unreadable

    assert not looks_unreadable(" ".join(QUESTIONS * 10))
    assert not looks_unreadable("x = 2y + 3")  # too short to judge
