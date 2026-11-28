"""Question images: cropping each question's region of its PDF."""

import fitz  # PyMuPDF
from sqlalchemy import select

from app.ingest import images, pipeline
from app.ingest.pdf_extract import extract_layout
from app.ingest.segmenter import split_questions_with_lines
from app.models import Question
from tests.test_api_documents import make_pdf, upload

A = "Explain how recursion works using a small example and its base case."
B = "Describe the difference between a stack and a queue with an example."
C = "Compare breadth first search with depth first search on weighted graphs."


def exam_pdf() -> bytes:
    """Two pages with a running header and page number. Question 1 has a drawn
    figure and a large blank answer space; question 2 runs onto page 2."""
    doc = fitz.open()
    for n in (1, 2):
        page = doc.new_page()
        page.insert_text((72, 40), "CS 101 Midterm", fontsize=9)
        page.insert_text((300, 780), str(n), fontsize=9)
    p1, p2 = doc[0], doc[1]
    p1.insert_text((72, 100), f"1. {A}", fontsize=10)
    p1.draw_rect(fitz.Rect(150, 120, 300, 200), color=(1, 0, 0), width=2)  # the figure
    p1.insert_text((72, 600), f"2. {B}", fontsize=10)
    p2.insert_text((72, 100), "(b) And now continue the second question here.", fontsize=10)
    p2.insert_text((72, 300), f"3. {C}", fontsize=10)
    data = doc.tobytes()
    doc.close()
    return data


def render(data: bytes):
    layout = extract_layout(data)
    found = split_questions_with_lines(layout.text)
    return layout, found, images.render_questions(data, layout.lines, [(a, b) for _, a, b in found])


def size(png: bytes) -> tuple[int, int]:
    pix = fitz.Pixmap(png)
    return pix.width, pix.height


def test_layout_has_one_position_per_line():
    layout = extract_layout(exam_pdf())
    lines = layout.text.split("\n")
    assert len(lines) == len(layout.lines)
    for text, line in zip(lines, layout.lines):
        assert text.strip() == line.text.strip()
    assert {line.page for line in layout.lines} == {0, 1}


def test_each_question_gets_an_image():
    _, found, pngs = render(exam_pdf())
    assert len(found) == len(pngs) == 3
    assert all(png and png.startswith(b"\x89PNG") for png in pngs)


def test_figures_are_kept_and_answer_space_is_collapsed():
    _, _, (first, second, third) = render(exam_pdf())
    width, height = size(first)
    # Question 1 spans y=100..600 on the page: text, the red figure, then about
    # 400pt of blank answer space that is dropped.
    assert 100 * 2 < height < 250 * 2
    pix = fitz.Pixmap(first)
    reds = sum(
        1
        for y in range(0, pix.height, 4)
        for x in range(0, pix.width, 4)
        if (lambda p: p[0] > 200 and p[1] < 80 and p[2] < 80)(pix.pixel(x, y))
    )
    assert reds > 0, "the drawn figure should be in the crop"


def test_running_headers_and_page_numbers_are_left_out():
    _, _, (_, second, _) = render(exam_pdf())
    # Question 2 crosses the page break: its line on page 1 and its part (b)
    # on page 2, without "CS 101 Midterm" or the page numbers in between.
    _, height = size(second)
    assert height < 120 * 2


def test_nothing_to_crop_gives_none():
    layout = extract_layout(exam_pdf())
    assert images.render_questions(exam_pdf(), layout.lines, [(0, 0)]) == [None]
    assert images.render_questions(exam_pdf(), [], [(0, 0)]) == [None]


def test_very_long_questions_are_capped(monkeypatch):
    monkeypatch.setattr(images, "_MAX_HEIGHT", 30.0)
    _, _, pngs = render(exam_pdf())
    assert all(size(p)[1] <= 30 * 2 + 2 for p in pngs)


def test_uploaded_questions_link_to_their_images(client, make_course):
    make_course()
    upload(client, make_pdf())
    items = client.get("/api/questions", params={"course_code": "CS101"}).json()["items"]
    assert all(q["image_url"].startswith("/api/images/") for q in items)
    r = client.get(items[0]["image_url"])
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert "immutable" in r.headers["cache-control"]
    assert r.content.startswith(b"\x89PNG")


def test_image_names_are_checked(client):
    assert client.get("/api/images/..%2Fdocuments%2F1.pdf").status_code == 404
    assert client.get("/api/images/notanimage.txt").status_code == 404
    assert client.get("/api/images/999-0.png").status_code == 404


def test_a_rendering_failure_keeps_the_questions(client, make_course, db_session, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("renderer crashed")

    monkeypatch.setattr(pipeline, "render_questions", broken)
    make_course()
    assert upload(client, make_pdf()).json()["status"] == "published"
    assert db_session.scalars(select(Question.image_key)).all() == [None, None, None]


def test_reupload_refreshes_the_image(client, make_course, db_session):
    make_course()
    pdf = make_pdf()
    upload(client, pdf)
    before = set(db_session.scalars(select(Question.image_key)))
    upload(client, pdf)
    db_session.expire_all()
    after = set(db_session.scalars(select(Question.image_key)))
    assert before.isdisjoint(after) and len(after) == 3
