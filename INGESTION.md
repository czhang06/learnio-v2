# Ingestion accuracy

How well uploads are split into questions, measured on a fixed set of hand-labelled exams. This is tracked the way `BENCHMARKS.md` tracks latency: every segmenter change is scored against the same set, and the result is recorded here.

The Phase 2 target is **precision and recall of at least 95%**.

## Test set

17 documents from the MIT OpenCourseWare files in `data/ocw/` (CC BY-NC-SA), covering all six demo courses: 13 exams and quizzes, and 4 practice sheets (a quiz review, a problem set, a recitation and a tutorial). They hold 98 questions. They were chosen to cover the layouts the courses use, including the ones the segmenter handled worst in a first run.

Each `data/golden/<name>.json` names its PDF and lists the questions, each by a phrase from its first lines and one from its last lines. The labelling rules:

- A question is a top-level numbered problem. Its parts (a), (b), its numbered sub-steps and its multiple-choice options belong to it.
- Cover pages, grading grids, instructions, formula sheets, review notes, reading assignments and "write your name" items are not questions.
- A question repeated on a later answer page is the same question, so the copy is not a new one.
- Matrices and diagrams extract as scrambled text, so phrases are taken from readable text only.

The 2011 18.06 exam 3 and final are left out. Their fonts have no character mapping, so they extract as gibberish (2 of the 188 OCW files). They need OCR or the LLM fallback, not a better segmenter.

## Scoring

`bench/ingest_eval.py` runs the same extraction and segmentation as the ingestion worker. A returned question is **right** when it contains one labelled question's start and end phrases and no other labelled question's start. Each labelled question can be matched once. From that:

- **precision** = right / returned
- **recall** = right / labelled

Merged questions, questions cut in two, repeated copies and cover pages taken for questions all count as mistakes. `backend/tests/test_ingest_eval.py` checks in CI that the labels still match the PDFs and that the scorer catches each kind of mistake.

## Results

| Version | Returned | Right | Precision | Recall | F1 | Documents fully right |
|---|---:|---:|---:|---:|---:|---:|
| baseline (regex segmenter) | 209 | 74 | 35.4% | 75.5% | 48.2% | 7 / 17 |

Per-document results are in `bench/results/ingest/`.

### Where the baseline goes wrong

1. **Numbered lists inside a question start new questions.** This is the main cause of low precision. It covers operation lists ("1. MARK-YELLOW(i)"), multiple-choice options ("1. P and Q are equivalent"), numbered conditions and parts numbered "1. (10 points)". Examples: 6.041 quiz 1 returns 26 pieces for 2 questions, 6.034 final 2008 returns 66 for 12, and 6.046J quiz 1 returns 14 for 7.
2. **Headings the pattern does not know are missed.** Examples are "Quiz 1, Question 1, Rules (50 points)" and "1 Team Problem: A Mystery". Text before the first recognised heading is dropped, so 6.034 final 2008 loses its first four questions and the 6.042J recitation loses its only one.
3. **Repeated answer pages** (6.041 quiz 1) and **cover-page grading grids** add extra pieces.

## Reproduce

```bash
python bench/fetch_ocw.py                                         # PDFs, if not already in data/ocw/
python bench/ingest_eval.py -v                                    # table with each document's mistakes
python bench/ingest_eval.py --json bench/results/ingest/<name>.json
```
