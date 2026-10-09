from sqlalchemy import func, select

from app.models import UsageEvent


def _exam(client, **body):
    body.setdefault("course_code", "CS101")
    return client.post("/api/exams", json=body)


def _ids(response):
    return [q["id"] for q in response.json()["questions"]]


def test_exam_has_requested_size(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 30)
    r = _exam(client, num_questions=10)
    assert r.status_code == 200
    assert r.json()["course_code"] == "CS101"
    assert len(r.json()["questions"]) == 10


def test_exam_has_no_duplicates(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 40)
    for _ in range(5):
        ids = _ids(_exam(client, num_questions=30))
        assert len(ids) == len(set(ids)) == 30


def test_exam_returns_fewer_when_pool_is_small(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 4)
    assert len(_ids(_exam(client, num_questions=20))) == 4


def test_exam_with_empty_pool(client, make_course):
    make_course()
    r = _exam(client, num_questions=5)
    assert r.status_code == 200
    assert r.json()["questions"] == []


def test_exam_respects_difficulty_range(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 20, difficulty=[1, 2, 3, 4, 5])
    r = _exam(client, num_questions=100, min_difficulty=2, max_difficulty=4)
    difficulties = {q["difficulty"] for q in r.json()["questions"]}
    assert difficulties <= {2, 3, 4}
    assert len(r.json()["questions"]) == 12  # 4 each of 2, 3, 4


def test_exam_respects_topic_filter(client, make_course, add_questions):
    course = make_course()
    wanted = add_questions(course, 5, topics=["arrays"])
    add_questions(course, 5, topics=["graphs"])
    add_questions(course, 5)
    r = _exam(client, num_questions=100, topics=["arrays"])
    assert sorted(_ids(r)) == wanted
    assert all("arrays" in q["topics"] for q in r.json()["questions"])


def test_exam_with_several_topics_has_no_duplicates(client, make_course, add_questions):
    course = make_course()
    both = add_questions(course, 5, topics=["arrays", "graphs"])
    only_graphs = add_questions(course, 3, topics=["graphs"])
    ids = _ids(_exam(client, num_questions=100, topics=["arrays", "graphs"]))
    assert sorted(ids) == sorted(both + only_graphs)
    assert len(ids) == len(set(ids))


def test_exam_combines_topic_and_difficulty(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 3, topics=["arrays"], difficulty=1)
    wanted = add_questions(course, 3, topics=["arrays"], difficulty=5)
    add_questions(course, 3, topics=["graphs"], difficulty=5)
    r = _exam(client, num_questions=100, topics=["arrays"], min_difficulty=4)
    assert sorted(_ids(r)) == wanted


def test_exam_only_uses_questions_of_its_course(client, make_course, add_questions):
    a = make_course("A", topics=("x",))
    b = make_course("B", topics=("x",))
    ids_a = add_questions(a, 3)
    add_questions(b, 5)
    r = _exam(client, course_code="A", num_questions=100)
    assert sorted(_ids(r)) == ids_a


def test_exam_topics_are_name_strings(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 1, topics=["graphs"])
    assert _exam(client, num_questions=1).json()["questions"][0]["topics"] == ["graphs"]


def test_exam_unknown_course_returns_404(client):
    assert _exam(client, course_code="NOPE").status_code == 404


def test_exam_rejects_invalid_num_questions(client, make_course):
    make_course()
    assert _exam(client, num_questions=0).status_code == 422
    assert _exam(client, num_questions=101).status_code == 422


def test_each_exam_writes_a_usage_event(client, make_course, add_questions, db_session):
    course = make_course()
    add_questions(course, 5)
    _exam(client, num_questions=2)
    _exam(client, num_questions=2)
    count = db_session.scalar(
        select(func.count()).select_from(UsageEvent).where(UsageEvent.kind == "exam_generated")
    )
    assert count == 2


def test_usage_event_records_client_id(client, make_course, add_questions, db_session):
    course = make_course()
    add_questions(course, 2)
    r = client.post("/api/exams", params={"client_id": "abc"}, json={"course_code": "CS101"})
    assert r.status_code == 200
    event = db_session.scalars(select(UsageEvent)).one()
    assert event.client_id == "abc"


def test_unknown_course_writes_no_usage_event(client, db_session):
    _exam(client, course_code="NOPE")
    assert db_session.scalar(select(func.count()).select_from(UsageEvent)) == 0
