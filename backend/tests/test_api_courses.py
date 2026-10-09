def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_course(client):
    r = client.post("/api/courses", json={"code": "CS101", "name": "Intro", "topics": ["arrays", "graphs"]})
    assert r.status_code == 201
    body = r.json()
    assert body["code"] == "CS101"
    assert body["name"] == "Intro"
    assert isinstance(body["id"], int)


def test_create_course_deduplicates_topics(client):
    client.post("/api/courses", json={"code": "CS101", "topics": ["arrays", "arrays", "graphs"]})
    r = client.get("/api/courses/CS101/topics")
    assert r.json() == ["arrays", "graphs"]


def test_create_course_requires_code(client):
    assert client.post("/api/courses", json={"code": "", "name": "x"}).status_code == 422
    assert client.post("/api/courses", json={"name": "x"}).status_code == 422


def test_duplicate_course_returns_409(client):
    assert client.post("/api/courses", json={"code": "CS101"}).status_code == 201
    r = client.post("/api/courses", json={"code": "CS101", "name": "Other"})
    assert r.status_code == 409
    assert len(client.get("/api/courses").json()) == 1


def test_list_courses_empty(client):
    assert client.get("/api/courses").json() == []


def test_list_courses_sorted_by_code(client):
    for code in ("MATH2", "CS101", "BIO1"):
        client.post("/api/courses", json={"code": code})
    codes = [c["code"] for c in client.get("/api/courses").json()]
    assert codes == ["BIO1", "CS101", "MATH2"]


def test_list_topics_sorted(client):
    client.post("/api/courses", json={"code": "CS101", "topics": ["trees", "arrays", "graphs"]})
    assert client.get("/api/courses/CS101/topics").json() == ["arrays", "graphs", "trees"]


def test_list_topics_only_for_that_course(client):
    client.post("/api/courses", json={"code": "A", "topics": ["x"]})
    client.post("/api/courses", json={"code": "B", "topics": ["y"]})
    assert client.get("/api/courses/B/topics").json() == ["y"]


def test_topics_of_unknown_course_returns_404(client):
    assert client.get("/api/courses/NOPE/topics").status_code == 404
