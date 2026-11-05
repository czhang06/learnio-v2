"""Locust port of LearnIO's k6 scenarios (bench/k6/list.js and bench/k6/exam.js).

Run from the repo root: locust -f bench/locust/locustfile.py --host http://localhost:8000

Env vars (same meaning as the k6 scripts):
  COURSE       course code to query         (default COURSE001)
  TOPIC        optional topic filter         (e.g. topic-3)
  PAGINATION   offset | cursor               (cursor needs tag opt-3-keyset or later)
  DEEP_OFFSET  how deep the listed page sits (default 10000)

Pick one scenario with --tags list or --tags exam (default: both, 50/50).
Run against a LOCAL API only (http://localhost:8000), never the deployed site.
"""
import os

from locust import HttpUser, constant, events, tag, task

COURSE = os.getenv("COURSE", "COURSE001")
TOPIC = os.getenv("TOPIC", "")
MODE = os.getenv("PAGINATION", "offset")
DEEP_OFFSET = int(os.getenv("DEEP_OFFSET", "10000"))

# Same idea as k6's setup(): find the id sitting DEEP_OFFSET rows in, so cursor
# mode requests the same logical page as offset mode. Computed once per run.
_cursor = {"id": 0}


def _params(**extra):
    p = {"course_code": COURSE, "limit": 20, **extra}
    if TOPIC:
        p["topic"] = TOPIC
    return p


@events.test_start.add_listener
def find_cursor(environment, **_):
    import requests

    r = requests.get(
        f"{environment.host}/api/questions",
        params={**_params(offset=DEEP_OFFSET - 1), "limit": 1},
        timeout=60,
    )
    items = r.json().get("items") or []
    _cursor["id"] = items[0]["id"] if items else 0


class LearnIOUser(HttpUser):
    # k6's constant-vus loops with no pause; constant(0) matches that.
    wait_time = constant(0)

    @tag("list")
    @task
    def list_deep_page(self):
        params = _params(after=_cursor["id"]) if MODE == "cursor" else _params(offset=DEEP_OFFSET)
        with self.client.get("/api/questions", params=params, name="GET /api/questions (deep page)",
                             catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"status {r.status_code}")
            elif len(r.json().get("items") or []) != 20:
                r.failure("expected 20 items")

    @tag("exam")
    @task
    def generate_exam(self):
        body = {"course_code": COURSE, "num_questions": 20}
        if TOPIC:
            body["topics"] = [TOPIC]
        with self.client.post("/api/exams", json=body, name="POST /api/exams",
                              catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"status {r.status_code}")
            elif len(r.json().get("questions") or []) != 20:
                r.failure("expected 20 questions")
