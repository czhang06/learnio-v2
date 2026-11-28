"""Download the MIT OpenCourseWare exams listed in data/ocw/manifest.json.

Each manifest entry names an OCW resource page; this resolves it to the PDF it
links and saves it as data/ocw/<course slug>/<exam name>.pdf. Files already on
disk are skipped, so re-running only fetches what is missing.

    python bench/fetch_ocw.py            # everything in the manifest
    python bench/fetch_ocw.py 18-06      # only courses whose slug starts with this
"""

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://ocw.mit.edu"
ROOT = Path(__file__).resolve().parent.parent / "data" / "ocw"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "learnio-ocw-fetch"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def pdf_url(slug: str, resource: str) -> str:
    page = fetch(f"{BASE}/courses/{slug}/resources/{resource}/").decode("utf-8", "replace")
    links = re.findall(rf'href="(/courses/{re.escape(slug)}/[^"]+\.pdf)"', page)
    if not links:
        raise RuntimeError(f"no PDF linked from resource {resource}")
    return BASE + links[0]


def main(prefixes: list[str]) -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text())
    for course in manifest["courses"]:
        if prefixes and not any(course["slug"].startswith(p) for p in prefixes):
            continue
        folder = ROOT / course["slug"]
        folder.mkdir(exist_ok=True)
        for name, resource in course["exams"].items():
            target = folder / f"{name}.pdf"
            if target.exists():
                continue
            data = fetch(pdf_url(course["slug"], resource))
            if not data.startswith(b"%PDF"):
                raise RuntimeError(f"{resource} did not return a PDF")
            target.write_bytes(data)
            print(f"{course['code']:<11} {name:<18} {len(data) // 1024:>5} KB")
            time.sleep(0.5)  # be gentle with OCW


if __name__ == "__main__":
    main(sys.argv[1:])
