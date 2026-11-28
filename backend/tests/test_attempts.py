"""Practice attempts for signed-in users and exams that adapt to them."""

import random

from sqlalchemy import select

from app.exams import service
from app.models import Attempt


def _exam(client, headers=None, **body):
    payload = {"course_code": "CS101", "num_questions": 5, **body}
    r = client.post("/api/exams", json=payload, headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()


def test_guest_exams_record_no_attempt(client, make_course, add_questions, db_session):
    add_questions(make_course(), 10)
    assert _exam(client)["attempt_id"] is None
    assert db_session.scalars(select(Attempt)).all() == []


def test_signed_in_exams_are_attempts(client, token, make_course, add_questions):
    add_questions(make_course(), 10)
    me = token()
    exam = _exam(client, me, topics=["arrays"])
    attempt = client.get(f"/api/attempts/{exam['attempt_id']}", headers=me).json()
    assert [q["id"] for q in attempt["questions"]] == [q["id"] for q in exam["questions"]]
    assert attempt["topics"] == ["arrays"]
    assert attempt["tally"] == {"right": 0, "wrong": 0, "skipped": 0, "unmarked": 0} | {"unmarked": len(exam["questions"])}


def test_marking_submitting_and_results_by_topic(client, token, make_course, add_questions):
    course = make_course(topics=("arrays", "graphs"))
    add_questions(course, 2, topics=["arrays"])
    add_questions(course, 2, topics=["graphs"])
    me = token()
    exam = _exam(client, me, num_questions=4)
    ids = {q["id"]: q["topics"][0] for q in exam["questions"]}
    aid = exam["attempt_id"]
    for qid, topic in ids.items():
        result = "right" if topic == "arrays" else "wrong"
        assert client.put(f"/api/attempts/{aid}/answers/{qid}", json={"result": result}, headers=me).status_code == 204
    some = next(iter(ids))
    client.put(f"/api/attempts/{aid}/answers/{some}", json={"result": None}, headers=me)
    client.put(f"/api/attempts/{aid}/answers/{some}", json={"result": "skipped"}, headers=me)

    done = client.post(f"/api/attempts/{aid}/submit", headers=me).json()
    assert done["submitted_at"] is not None
    assert sum(done["tally"].values()) == 4 and done["tally"]["skipped"] == 1
    assert done["by_topic"][0]["topic"] == "graphs"  # weakest first
    assert client.post(f"/api/attempts/{aid}/submit", headers=me).json()["submitted_at"] == done["submitted_at"]


def test_marks_are_validated(client, token, make_course, add_questions):
    other_q = add_questions(make_course("MATH200"), 1)[0]
    add_questions(make_course(), 3)
    me = token()
    exam = _exam(client, me, num_questions=3)
    aid, qid = exam["attempt_id"], exam["questions"][0]["id"]
    assert client.put(f"/api/attempts/{aid}/answers/{qid}", json={"result": "maybe"}, headers=me).status_code == 422
    assert client.put(f"/api/attempts/{aid}/answers/{other_q}", json={"result": "right"}, headers=me).status_code == 404


def test_attempts_are_private(client, token, make_course, add_questions):
    add_questions(make_course(), 3)
    exam = _exam(client, token("ada"))
    bob = token("bob")
    aid, qid = exam["attempt_id"], exam["questions"][0]["id"]
    assert client.get(f"/api/attempts/{aid}", headers=bob).status_code == 404
    assert client.put(f"/api/attempts/{aid}/answers/{qid}", json={"result": "right"}, headers=bob).status_code == 404
    assert client.get("/api/attempts", headers=bob).json() == []
    assert client.get(f"/api/attempts/{aid}").status_code == 401


def test_history_newest_first(client, token, make_course, add_questions):
    add_questions(make_course(), 3)
    add_questions(make_course("MATH200"), 3)
    me = token()
    first = _exam(client, me)["attempt_id"]
    second = _exam(client, me)["attempt_id"]
    other = _exam(client, me, course_code="MATH200")["attempt_id"]
    assert [a["id"] for a in client.get("/api/attempts", headers=me).json()] == [other, second, first]
    assert [a["id"] for a in client.get("/api/attempts", params={"course_code": "CS101"}, headers=me).json()] == [
        second,
        first,
    ]


def test_retry_wrong_and_skipped(client, token, make_course, add_questions):
    add_questions(make_course(), 3)
    me = token()
    exam = _exam(client, me, num_questions=3)
    aid = exam["attempt_id"]
    a, b, c = (q["id"] for q in exam["questions"])
    for qid, result in ((a, "right"), (b, "wrong"), (c, "skipped")):
        client.put(f"/api/attempts/{aid}/answers/{qid}", json={"result": result}, headers=me)
    again = client.post(f"/api/attempts/{aid}/retry", headers=me).json()
    assert [q["id"] for q in again["questions"]] == [b, c]
    assert again["attempt_id"] != aid
    assert client.post(f"/api/attempts/{again['attempt_id']}/retry", headers=me).status_code == 409


def test_exams_lean_toward_weak_topics(client, token, make_course, add_questions):
    course = make_course(topics=("arrays", "graphs"))
    add_questions(course, 30, topics=["arrays"])
    add_questions(course, 30, topics=["graphs"])
    me = token()
    # Mark six graph questions wrong and six array questions right.
    marked = {"arrays": 0, "graphs": 0}
    while min(marked.values()) < 6:
        exam = _exam(client, me, num_questions=10)
        for q in exam["questions"]:
            topic = q["topics"][0]
            if marked[topic] < 6:
                marked[topic] += 1
                result = "wrong" if topic == "graphs" else "right"
                client.put(f"/api/attempts/{exam['attempt_id']}/answers/{q['id']}", json={"result": result}, headers=me)
    random.seed(7)
    graphs = sum(q["topics"] == ["graphs"] for _ in range(20) for q in _exam(client, me, num_questions=10)["questions"])
    assert graphs > 140  # of 200; an unweighted exam would average 100


def test_recently_seen_questions_are_less_likely():
    class Q:
        def __init__(self, id):
            self.id, self.topics = id, []

    assert service._weight(Q(1), {}, seen={1}) == service.SEEN_WEIGHT
    assert service._weight(Q(2), {}, seen={1}) == 1


def test_two_accounts_get_different_exams(client, token, make_course, add_questions):
    """Phase 3 done-when, part 2: the same course gives each account its own exam."""
    add_questions(make_course(), 40)
    ada, bob = token("ada"), token("bob")
    random.seed(1)
    first_ada = {q["id"] for q in _exam(client, ada, num_questions=10)["questions"]}
    # Ada's next exam steers away from what she just saw; Bob, with no
    # history, is drawn independently.
    random.seed(1)
    second_ada = {q["id"] for q in _exam(client, ada, num_questions=10)["questions"]}
    random.seed(1)
    bob_exam = {q["id"] for q in _exam(client, bob, num_questions=10)["questions"]}
    assert len(first_ada & second_ada) < 5
    assert bob_exam != second_ada
