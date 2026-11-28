"""Load the MIT OpenCourseWare demo courses into a LearnIO API.

Creates each course in data/ocw/manifest.json with its topics, then uploads
every PDF through POST /api/documents, so each one goes through the same
ingestion (and storage) as a real upload. Uploads run one at a time: the
script waits for each document to finish before sending the next.

    python bench/seed_demo.py --api http://localhost:8000
    LEARNIO_ADMIN_KEY=... python bench/seed_demo.py --api https://learnio-api.onrender.com
    python bench/seed_demo.py --api ... --only "MIT 18.06" --dry-run

Courses that already exist are reused, so a run that stops part-way can be
started again; documents already uploaded would then be uploaded twice, but
their questions are deduplicated by the API.
"""

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent / "data" / "ocw"
SETTLED = {"published", "failed", "needs_review"}


def course_name(entries: list[dict]) -> str:
    """'Linear Algebra · MIT OpenCourseWare': the term is dropped when a course
    combines several runs, and the source is credited as the licence requires."""
    title = entries[0]["name"].split(" (")[0]
    return f"{title} · MIT OpenCourseWare"


def documents(entries: list[dict]):
    """(path, name shown in the app) for every PDF, exams first."""
    for entry in entries:
        term = entry["name"].split(" (")[-1].split(",")[0].rstrip(")")  # "Spring 2020"
        folder = ROOT / entry["slug"]
        for name in entry.get("exams", {}):
            yield folder / f"{name}.pdf", f"{name} ({term}).pdf"
        for name in entry.get("practice", {}):
            yield folder / "practice" / f"{name}.pdf", f"{name} ({term}).pdf"


def wait(client: httpx.Client, doc: dict, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while doc["status"] not in SETTLED and time.monotonic() < deadline:
        time.sleep(1.0)
        doc = client.get(f"/api/documents/{doc['id']}").raise_for_status().json()
    return doc


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", required=True, help="API base URL, e.g. http://localhost:8000")
    parser.add_argument("--only", action="append", default=[], help="course code to load (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="list what would be loaded, send nothing")
    parser.add_argument("--timeout", type=float, default=300, help="seconds to wait for each document")
    args = parser.parse_args()

    manifest = json.loads((ROOT / "manifest.json").read_text())
    courses: dict[str, list[dict]] = {}
    for entry in manifest["courses"]:
        if not args.only or entry["code"] in args.only:
            courses.setdefault(entry["code"], []).append(entry)
    if not courses:
        sys.exit(f"No course matches {args.only}")

    if args.dry_run:
        for code, entries in courses.items():
            docs = list(documents(entries))
            print(f"{code}: {course_name(entries)!r}, {len(entries[0]['topics'])} topics, {len(docs)} PDFs")
        return

    headers = {}
    if os.environ.get("LEARNIO_ADMIN_KEY"):
        headers["X-Admin-Key"] = os.environ["LEARNIO_ADMIN_KEY"]
    client = httpx.Client(base_url=args.api.rstrip("/"), headers=headers, timeout=120)

    for code, entries in courses.items():
        r = client.post("/api/courses", json={"code": code, "name": course_name(entries), "topics": entries[0]["topics"]})
        if r.status_code == 409:
            print(f"{code}: already exists, adding documents to it")
        else:
            r.raise_for_status()
            print(f"{code}: created")

        outcomes: Counter = Counter()
        added = 0
        for path, shown in documents(entries):
            with path.open("rb") as f:
                r = client.post(
                    "/api/documents",
                    data={"course_code": code, "kind": "exam", "client_id": "seed"},
                    files={"file": (shown, f, "application/pdf")},
                )
            if r.status_code != 202:
                outcomes["rejected"] += 1
                print(f"  {path.relative_to(ROOT)}: HTTP {r.status_code} {r.text[:200]}")
                continue
            doc = wait(client, r.json(), args.timeout)
            outcomes[doc["status"]] += 1
            added += doc["question_count"] if doc["status"] == "published" else 0
            if doc["status"] != "published":
                print(f"  {path.relative_to(ROOT)}: {doc['status']} {doc.get('error') or ''}")
        print(f"  {sum(outcomes.values())} PDFs: {dict(outcomes)}; {added} questions added")


if __name__ == "__main__":
    main()
