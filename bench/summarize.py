#!/usr/bin/env python3
"""Turn k6 --summary-export JSON files into Markdown tables.

Usage: bench/summarize.py bench/results > table.md
Result files are named <tag>__<scenario>.json, e.g. baseline__list_topic.json.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

TAG_ORDER = ["baseline", "opt-1-indexes", "opt-2-eager-load", "opt-3-keyset", "opt-4-exam-sampling"]
SCENARIOS = {
    "list": "List questions (deep page)",
    "list_topic": "List questions (deep page, topic filter)",
    "exam": "Generate exam",
    "exam_topic": "Generate exam (topic filter)",
}


def load(path: Path) -> dict:
    metrics = json.loads(path.read_text())["metrics"]
    dur = metrics["http_req_duration"]
    return {
        "p50": dur["med"],
        "p95": dur["p(95)"],
        "p99": dur.get("p(99)", float("nan")),
        "rps": metrics["http_reqs"]["rate"],
        "failed": metrics.get("http_req_failed", {}).get("value", 0.0),
    }


def main(results_dir: str) -> None:
    runs: dict[str, dict[str, dict]] = defaultdict(dict)
    for f in sorted(Path(results_dir).glob("*__*.json")):
        tag, scenario = f.stem.split("__", 1)
        runs[scenario][tag] = load(f)

    for scenario, title in SCENARIOS.items():
        if scenario not in runs:
            continue
        print(f"### {title}\n")
        print("| Version | p50 (ms) | p95 (ms) | p99 (ms) | Requests/s | Failed |")
        print("|---|---:|---:|---:|---:|---:|")
        for tag in TAG_ORDER:
            r = runs[scenario].get(tag)
            if r:
                print(f"| {tag} | {r['p50']:.1f} | {r['p95']:.1f} | {r['p99']:.1f} | {r['rps']:.0f} | {r['failed'] * 100:.1f}% |")
        print()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "bench/results")
