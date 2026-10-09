def _ids(page):
    return [q["id"] for q in page["items"]]


def _get(client, **params):
    params.setdefault("course_code", "CS101")
    r = client.get("/api/questions", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_unknown_course_returns_404(client):
    assert client.get("/api/questions", params={"course_code": "NOPE"}).status_code == 404


def test_empty_course_returns_no_items(client, make_course):
    make_course()
    page = _get(client)
    assert page["items"] == []
    assert page["next_cursor"] is None


def test_topics_are_returned_as_name_strings(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 1, topics=["arrays", "graphs"])
    item = _get(client)["items"][0]
    assert sorted(item["topics"]) == ["arrays", "graphs"]
    assert set(item) >= {"id", "text", "difficulty", "topics"}


def test_default_order_is_by_id(client, make_course, add_questions):
    course = make_course()
    ids = add_questions(course, 5)
    assert _ids(_get(client)) == ids


def test_only_questions_of_requested_course(client, make_course, add_questions):
    a = make_course("A", topics=("x",))
    b = make_course("B", topics=("x",))
    ids_a = add_questions(a, 2)
    add_questions(b, 3)
    assert _ids(_get(client, course_code="A")) == ids_a


def test_filter_by_topic(client, make_course, add_questions):
    course = make_course()
    arrays = add_questions(course, 3, topics=["arrays"])
    add_questions(course, 2, topics=["graphs"])
    add_questions(course, 2)
    assert _ids(_get(client, topic="arrays")) == arrays


def test_filter_by_difficulty(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 2, difficulty=2)
    hard = add_questions(course, 3, difficulty=5)
    page = _get(client, difficulty=5)
    assert _ids(page) == hard
    assert {q["difficulty"] for q in page["items"]} == {5}


def test_filter_by_topic_and_difficulty(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 2, topics=["arrays"], difficulty=1)
    wanted = add_questions(course, 2, topics=["arrays"], difficulty=4)
    add_questions(course, 2, topics=["graphs"], difficulty=4)
    assert _ids(_get(client, topic="arrays", difficulty=4)) == wanted


def test_unknown_topic_returns_empty(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 2)
    assert _get(client, topic="nonexistent")["items"] == []


def test_offset_pagination(client, make_course, add_questions):
    course = make_course()
    ids = add_questions(course, 7)
    assert _ids(_get(client, limit=3, offset=0)) == ids[0:3]
    assert _ids(_get(client, limit=3, offset=3)) == ids[3:6]
    assert _ids(_get(client, limit=3, offset=6)) == ids[6:7]
    assert _get(client, limit=3, offset=7)["items"] == []


def test_offset_pagination_with_topic(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 2)
    ids = add_questions(course, 6, topics=["graphs"])
    assert _ids(_get(client, topic="graphs", limit=2, offset=2)) == ids[2:4]


def test_keyset_matches_equivalent_offset_page(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 12)
    first = _get(client, limit=5)
    by_offset = _get(client, limit=5, offset=5)
    by_cursor = _get(client, limit=5, after=first["next_cursor"])
    assert _ids(by_cursor) == _ids(by_offset)
    assert by_cursor["items"] == by_offset["items"]


def test_keyset_with_topic_matches_offset(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 3)
    add_questions(course, 8, topics=["arrays"])
    add_questions(course, 3, topics=["graphs"])
    first = _get(client, topic="arrays", limit=3)
    by_offset = _get(client, topic="arrays", limit=3, offset=3)
    by_cursor = _get(client, topic="arrays", limit=3, after=first["next_cursor"])
    assert _ids(by_cursor) == _ids(by_offset)
    assert all(q["topics"] == ["arrays"] for q in by_cursor["items"])


def test_after_returns_only_larger_ids(client, make_course, add_questions):
    course = make_course()
    ids = add_questions(course, 6)
    page = _get(client, after=ids[2], limit=100)
    assert _ids(page) == ids[3:]


def test_after_with_difficulty_filter(client, make_course, add_questions):
    course = make_course()
    ids = add_questions(course, 6, difficulty=[1, 2])
    page = _get(client, after=ids[0], difficulty=2, limit=100)
    assert _ids(page) == [ids[1], ids[3], ids[5]]


def test_walking_cursors_visits_everything_once(client, make_course, add_questions):
    course = make_course()
    ids = add_questions(course, 11)
    seen, cursor = [], None
    for _ in range(10):
        params = {"limit": 4}
        if cursor is not None:
            params["after"] = cursor
        page = _get(client, **params)
        seen += _ids(page)
        cursor = page["next_cursor"]
        if cursor is None:
            break
    assert seen == ids


def test_next_cursor_is_last_id_when_page_is_full(client, make_course, add_questions):
    course = make_course()
    ids = add_questions(course, 6)
    page = _get(client, limit=4)
    assert page["next_cursor"] == ids[3]


def test_next_cursor_null_on_partial_page(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 3)
    assert _get(client, limit=4)["next_cursor"] is None


def test_next_cursor_null_after_last_page(client, make_course, add_questions):
    course = make_course()
    ids = add_questions(course, 5)
    page = _get(client, limit=5, after=ids[-1])
    assert page["items"] == []
    assert page["next_cursor"] is None


def test_limit_of_100_is_allowed(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 105)
    page = _get(client, limit=100)
    assert len(page["items"]) == 100
    assert page["next_cursor"] == page["items"][-1]["id"]


def test_limit_above_100_is_rejected(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 105)
    r = client.get("/api/questions", params={"course_code": "CS101", "limit": 500})
    assert r.status_code == 422


def test_default_limit_is_20(client, make_course, add_questions):
    course = make_course()
    add_questions(course, 25)
    assert len(_get(client)["items"]) == 20
