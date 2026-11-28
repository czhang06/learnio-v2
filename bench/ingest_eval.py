"""Score question segmentation against the hand-labelled exams in data/golden/.

Each golden file names a PDF under data/ocw/ and lists its questions, each by a
phrase from its first lines (`start`) and one from its last lines (`end`).
Text is compared after Unicode normalization, lower-casing and collapsing
whitespace, so layout and ligatures do not matter.

A predicted question is correct when it contains one golden question's start
and end and no other golden question's start. Each golden question can be
matched once; anything else the segmenter returns counts against precision.
So a merged pair, a question cut in two, a repeated copy, or a cover page
taken for a question all lower the score.

    python bench/ingest_eval.py              # table + totals
    python bench/ingest_eval.py --json out   # also write results as JSON
    python bench/ingest_eval.py -v 6041      # show mistakes for matching files
"""

import argparse
import json
import re
import sys
import unicodedata
import warnings
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
warnings.filterwarnings("ignore", category=FutureWarning)  # PyMuPDF's fitz alias

from app.ingest.pdf_extract import extract_text  # noqa: E402
from app.ingest.segmenter import split_questions  # noqa: E402

GOLDEN = ROOT / "data" / "golden"
PDFS = ROOT / "data" / "ocw"


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text)).strip().lower()


def segment(pdf: bytes) -> list[str]:
    """The segmentation under test: the same steps the ingestion worker runs."""
    return split_questions(extract_text(pdf))


@dataclass
class DocResult:
    name: str
    gold: int
    predicted: int
    correct: int
    merged: list[str] = field(default_factory=list)  # gold numbers sharing a piece with another start
    cut: list[str] = field(default_factory=list)  # start found but its end is not in that piece
    missed: list[str] = field(default_factory=list)  # start in no piece at all
    extra: int = 0  # pieces that matched nothing

    @property
    def precision(self) -> float:
        return self.correct / self.predicted if self.predicted else 0.0

    @property
    def recall(self) -> float:
        return self.correct / self.gold if self.gold else 0.0


def score(name: str, gold: list[dict], pieces: list[str]) -> DocResult:
    starts = [norm(q["start"]) for q in gold]
    ends = [norm(q["end"]) for q in gold]
    texts = [norm(p) for p in pieces]
    result = DocResult(name=name, gold=len(gold), predicted=len(pieces), correct=0)
    matched_piece: set[int] = set()
    for i, q in enumerate(gold):
        holders = [j for j, t in enumerate(texts) if starts[i] in t]
        if not holders:
            result.missed.append(q["number"])
            continue
        hit = next(
            (
                j
                for j in holders
                if j not in matched_piece
                and ends[i] in texts[j][texts[j].index(starts[i]) :]
                and not any(starts[k] in texts[j] for k in range(len(gold)) if k != i)
            ),
            None,
        )
        if hit is not None:
            matched_piece.add(hit)
            result.correct += 1
        elif any(any(starts[k] in texts[j] for k in range(len(gold)) if k != i) for j in holders):
            result.merged.append(q["number"])
        else:
            result.cut.append(q["number"])
    result.extra = len(pieces) - len(matched_piece)
    return result


def run(pattern: str = "") -> list[DocResult]:
    results = []
    for path in sorted(GOLDEN.glob("*.json")):
        if pattern not in path.stem:
            continue
        doc = json.loads(path.read_text())
        pieces = segment((PDFS / doc["pdf"]).read_bytes())
        results.append(score(path.stem, doc["questions"], pieces))
    return results


def totals(results: list[DocResult]) -> dict:
    gold = sum(r.gold for r in results)
    predicted = sum(r.predicted for r in results)
    correct = sum(r.correct for r in results)
    precision = correct / predicted if predicted else 0.0
    recall = correct / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "documents": len(results),
        "gold": gold,
        "predicted": predicted,
        "correct": correct,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "documents_all_correct": sum(r.correct == r.gold == r.predicted for r in results),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("pattern", nargs="?", default="", help="only golden files whose name contains this")
    parser.add_argument("--json", metavar="PATH", help="write per-document results and totals as JSON")
    parser.add_argument("-v", "--verbose", action="store_true", help="list merged, cut and missed questions")
    args = parser.parse_args()

    results = run(args.pattern)
    print(f"{'document':<20} {'gold':>4} {'found':>5} {'right':>5} {'prec':>5} {'recall':>6}  problems")
    for r in results:
        problems = []
        if r.merged:
            problems.append(f"merged {','.join(r.merged)}")
        if r.cut:
            problems.append(f"cut {','.join(r.cut)}")
        if r.missed:
            problems.append(f"missed {','.join(r.missed)}")
        if r.extra:
            problems.append(f"{r.extra} extra")
        line = f"{r.name:<20} {r.gold:>4} {r.predicted:>5} {r.correct:>5} {r.precision:>5.0%} {r.recall:>6.0%}"
        print(line + ("  " + "; ".join(problems) if args.verbose or len(problems) <= 2 else f"  {len(problems)} kinds"))
    t = totals(results)
    print(
        f"\n{t['documents']} documents, {t['gold']} questions: found {t['predicted']}, {t['correct']} right. "
        f"precision {t['precision']:.1%}, recall {t['recall']:.1%}, F1 {t['f1']:.1%}; "
        f"{t['documents_all_correct']} documents fully right."
    )
    if args.json:
        Path(args.json).write_text(
            json.dumps({"totals": t, "documents": [asdict(r) for r in results]}, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
