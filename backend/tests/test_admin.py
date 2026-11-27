import fitz  # PyMuPDF
import pytest

from app.config import settings


def make_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page().insert_text((50, 72), "1. Explain how recursion works using a small example.", fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def upload(client, **headers):
    return client.post(
        "/api/documents",
        data={"course_code": "CS101"},
        files={"file": ("exam.pdf", make_pdf(), "application/pdf")},
        headers=headers,
    )


@pytest.fixture
def locked(monkeypatch):
    monkeypatch.setattr(settings, "admin_key", "s3cret")


def test_mode_is_open_without_an_admin_key(client):
    assert client.get("/api/mode").json() == {"read_only": False}


def test_mode_is_read_only_with_an_admin_key(client, locked):
    assert client.get("/api/mode").json() == {"read_only": True}


def test_locked_demo_rejects_course_creation_without_the_key(client, locked):
    r = client.post("/api/courses", json={"code": "CS101"})
    assert r.status_code == 403
    assert "read-only" in r.json()["detail"]
    assert client.get("/api/courses").json() == []


def test_locked_demo_rejects_a_wrong_key(client, locked):
    r = client.post("/api/courses", json={"code": "CS101"}, headers={"X-Admin-Key": "guess"})
    assert r.status_code == 403


def test_locked_demo_accepts_course_creation_with_the_key(client, locked):
    r = client.post("/api/courses", json={"code": "CS101"}, headers={"X-Admin-Key": "s3cret"})
    assert r.status_code == 201


def test_locked_demo_rejects_uploads_without_the_key(client, make_course, locked):
    make_course()
    assert upload(client).status_code == 403


def test_locked_demo_accepts_uploads_with_the_key(client, make_course, locked):
    make_course()
    r = upload(client, **{"X-Admin-Key": "s3cret"})
    assert r.status_code == 202, r.text
    assert r.json()["question_count"] == 1


def test_locked_demo_still_generates_exams(client, make_course, locked):
    make_course()
    r = client.post("/api/exams", json={"course_code": "CS101", "num_questions": 5})
    assert r.status_code == 200


def test_admin_check_reports_whether_a_key_is_accepted(client, locked):
    assert client.post("/api/admin/check", headers={"X-Admin-Key": "s3cret"}).status_code == 204
    assert client.post("/api/admin/check", headers={"X-Admin-Key": "nope"}).status_code == 403
