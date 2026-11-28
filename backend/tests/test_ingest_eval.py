"""Keep the hand-labelled ingestion test set (data/golden/) and its scorer honest.

Slicing each exam's text exactly at its labelled questions must score 100%,
and merging, cutting or repeating a question must be caught. This fails when a
label drifts from the PDF text (a typo, or a start phrase that also appears
inside another question) or when a scorer change stops detecting mistakes.
"""

import importlib.util
import json
import warnings
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("ingest_eval", REPO / "bench" / "ingest_eval.py")
ingest_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest_eval)
norm = ingest_eval.norm

GOLDEN_FILES = sorted(ingest_eval.GOLDEN.glob("*.json"))


def test_there_is_a_test_set():
    assert len(GOLDEN_FILES) >= 15


@pytest.fixture(params=GOLDEN_FILES, ids=lambda p: p.stem)
def labelled(request):
    """(questions, the exam's text cut exactly at the labelled questions)."""
    doc = json.loads(request.param.read_text())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        text = norm(ingest_eval.extract_text((ingest_eval.PDFS / doc["pdf"]).read_bytes()))
    pieces, pos = [], 0
    for q in doc["questions"]:
        start = text.find(norm(q["start"]), pos)
        assert start >= 0, f"question {q['number']}: start phrase not found after the previous question"
        end = text.find(norm(q["end"]), start)
        assert end >= 0, f"question {q['number']}: end phrase not found after its start"
        pos = end + len(norm(q["end"]))
        pieces.append(text[start:pos])
    return doc["questions"], pieces


def test_exact_labels_score_perfectly(labelled):
    questions, pieces = labelled
    r = ingest_eval.score("doc", questions, pieces)
    assert (r.correct, r.predicted, r.extra) == (len(questions), len(questions), 0), r


def test_merged_questions_are_caught(labelled):
    questions, pieces = labelled
    if len(pieces) < 2:
        pytest.skip("one question")
    r = ingest_eval.score("doc", questions, [pieces[0] + " " + pieces[1], *pieces[2:]])
    assert r.correct == len(questions) - 2
    assert r.merged == [questions[0]["number"], questions[1]["number"]]


def test_a_question_cut_in_two_is_caught(labelled):
    questions, pieces = labelled
    first = pieces[0]
    after_start = len(norm(questions[0]["start"]))
    before_end = len(first) - len(norm(questions[0]["end"]))
    if before_end <= after_start:
        pytest.skip("start and end phrases overlap")
    middle = (after_start + before_end) // 2
    r = ingest_eval.score("doc", questions, [first[:middle], first[middle:], *pieces[1:]])
    assert (r.correct, r.cut, r.extra) == (len(questions) - 1, [questions[0]["number"]], 2)


def test_a_repeated_copy_counts_against_precision(labelled):
    questions, pieces = labelled
    r = ingest_eval.score("doc", questions, [*pieces, pieces[0]])
    assert (r.correct, r.extra) == (len(questions), 1)


def test_totals():
    r = ingest_eval.DocResult(name="d", split="dev", gold=4, predicted=5, correct=3)
    t = ingest_eval.totals([r])
    assert (t["precision"], t["recall"], t["f1"]) == (0.6, 0.75, 0.667)
    assert ingest_eval.totals([]) == {
        "documents": 0, "gold": 0, "predicted": 0, "correct": 0,
        "precision": 0.0, "recall": 0.0, "f1": 0.0, "documents_all_correct": 0,
    }
