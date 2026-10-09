import fitz  # PyMuPDF
from sqlalchemy import func, select

from app.config import settings
from app.models import Document, Question, UsageEvent

QUESTIONS = [
    "Explain how recursion works using a small example.",
    "Describe the difference between a stack and a queue.",
    "Compare breadth first search with depth first search on graphs.",
]


def make_pdf(questions=QUESTIONS, style="{n}. {q}") -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for n, q in enumerate(questions, start=1):
        page.insert_text((50, y), style.format(n=n, q=q), fontsize=10)
        y += 30
    data = doc.tobytes()
    doc.close()
    return data


def upload(client, data, *, filename="exam.pdf", course_code="CS101", **form):
    return client.post(
        "/api/documents",
        data={"course_code": course_code, **form},
        files={"file": (filename, data, "application/pdf")},
    )


def count(db_session, model):
    return db_session.scalar(select(func.count()).select_from(model))


def test_upload_stores_questions(client, make_course, db_session):
    make_course()
    r = upload(client, make_pdf())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["question_count"] == 3
    assert body["status"] == "done"
    assert body["filename"] == "exam.pdf"
    assert count(db_session, Question) == 3


def test_uploaded_questions_are_listed_and_keyword_tagged(client, make_course):
    make_course(topics=("recursion", "graphs", "sorting"))
    upload(client, make_pdf())
    items = client.get("/api/questions", params={"course_code": "CS101"}).json()["items"]
    assert len(items) == 3
    by_text = {q["text"]: q["topics"] for q in items}
    assert by_text[QUESTIONS[0]] == ["recursion"]
    assert by_text[QUESTIONS[1]] == []
    assert by_text[QUESTIONS[2]] == ["graphs"]


def test_question_n_style_is_parsed(client, make_course):
    make_course()
    r = upload(client, make_pdf(style="Question {n}: {q}"))
    assert r.json()["question_count"] == 3


def test_reupload_same_pdf_stores_no_new_questions(client, make_course, db_session):
    make_course()
    pdf = make_pdf()
    assert upload(client, pdf).json()["question_count"] == 3
    second = upload(client, pdf)
    assert second.status_code == 201
    assert second.json()["question_count"] == 0
    assert count(db_session, Question) == 3


def test_overlapping_pdf_only_stores_new_questions(client, make_course, db_session):
    make_course()
    upload(client, make_pdf(QUESTIONS[:2]))
    r = upload(client, make_pdf(QUESTIONS))
    assert r.json()["question_count"] == 1
    assert count(db_session, Question) == 3


def test_same_questions_in_other_course_are_stored_again(client, make_course, db_session):
    make_course("A")
    make_course("B")
    pdf = make_pdf()
    assert upload(client, pdf, course_code="A").json()["question_count"] == 3
    assert upload(client, pdf, course_code="B").json()["question_count"] == 3
    assert count(db_session, Question) == 6


def test_upload_writes_document_and_usage_event(client, make_course, db_session):
    make_course()
    upload(client, make_pdf(), client_id="abc", kind="syllabus")
    doc = db_session.scalars(select(Document)).one()
    assert doc.kind == "syllabus"
    assert doc.question_count == 3
    event = db_session.scalars(select(UsageEvent)).one()
    assert (event.kind, event.client_id) == ("upload", "abc")


def test_pdf_without_questions_gives_zero(client, make_course):
    make_course()
    r = upload(client, make_pdf(["just a plain sentence with no numbering"], style="{q}"))
    assert r.status_code == 201
    assert r.json()["question_count"] == 0


def test_non_pdf_filename_returns_415(client, make_course):
    make_course()
    r = upload(client, make_pdf(), filename="exam.txt")
    assert r.status_code == 415


def test_corrupt_pdf_returns_422(client, make_course, db_session):
    make_course()
    r = upload(client, b"this is definitely not a pdf", filename="broken.pdf")
    assert r.status_code == 422
    assert count(db_session, Question) == 0


def test_oversize_upload_returns_413(client, make_course, monkeypatch):
    make_course()
    monkeypatch.setattr(settings, "max_upload_mb", 0)
    r = upload(client, make_pdf())
    assert r.status_code == 413


def test_unknown_course_returns_404(client):
    r = upload(client, make_pdf(), course_code="NOPE")
    assert r.status_code == 404
