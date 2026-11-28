# Ingestion accuracy

How well uploads are split into questions, measured on a fixed set of hand-labelled exams. This is tracked the way `BENCHMARKS.md` tracks latency: every segmenter change is scored against the same set, and the result is recorded here.

The Phase 2 target is **precision and recall of at least 95%**.

## Test set

24 documents from the MIT OpenCourseWare files in `data/ocw/` (CC BY-NC-SA), covering all six demo courses and holding 129 questions, in two parts:

- **dev**: 17 documents, 98 questions. These were used while developing the segmenter: 13 exams and quizzes, and 4 practice sheets (a quiz review, a problem set, a recitation and a tutorial). They were chosen to cover the layouts the courses use, including the ones the baseline handled worst.
- **heldout**: 7 documents, 31 questions. These were labelled after the segmenter was written and scored without looking at its output first. Each file has `"split": "heldout"`.

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

| Version | Set | Returned | Right | Precision | Recall | F1 | Documents fully right |
|---|---|---:|---:|---:|---:|---:|---:|
| baseline (regex segmenter) | dev | 209 | 74 | 35.4% | 75.5% | 48.2% | 7 / 17 |
| heading chains, first held-out run | heldout | 30 | 29 | 96.7% | 93.5% | 95.1% | 6 / 7 |
| heading chains | dev | 98 | 98 | 100% | 100% | 100% | 17 / 17 |
| heading chains | heldout | 31 | 31 | 100% | 100% | 100% | 7 / 7 |

The baseline was not scored on the held-out set, which was labelled later. Per-document results are in `bench/results/ingest/`.

**Read the 100% rows with care.** The dev set shaped the rules. The held-out set's first run (96.7% / 93.5%) is the honest estimate for unseen exams. Its one miss was a heading style the rules did not know: the dagger-marked graduate problems "G1†" that 10 of the 6.041 problem sets use. The rule added for it is specific to that convention. The next layout-specific change should be checked against freshly labelled exams, not these.

### How the heading-chain segmenter works

Every line that could start a question is a candidate:

- keyword headings, including "Quiz 2, Question 1", "Problem 3-1" and "1 Team Problem:"
- numbers with a separator ("1.", "2)")
- numbers before a mark count ("4 (10 marks)")
- short numbered title lines ("2 Double Sums")
- dagger-marked extra problems ("G1†.")

Any of these may follow a bullet. Candidates are grouped by style: keyword headings by numbering depth, and numbered ones by indentation. The questions are the group whose numbers run 1, 2, 3… furthest, with explicit Problem or Question headings preferred. A list inside a question restarts at 1, so it can never outrun the questions' own numbering. That removes the baseline's main failure without needing font sizes or bold.

After the main run, a later run of the same style is handled in one of two ways:

- A run that repeats earlier questions (answer pages), or has almost no text or says "tear off" (tear-off sheets), ends the question before it.
- Any other run is kept as a further section.

Separately, ingestion now rejects PDFs whose extracted text is gibberish (fonts with no character map) with an error asking for another copy, instead of storing nonsense. The two 2011 18.06 files are the only ones in the OCW set it flags.

### Remaining gaps

- **Unnumbered single problems** (6.041 recitation 22) return no questions, and the upload fails with "No questions found".
- **Unreadable PDFs** need OCR or the LLM fallback.
- **Long problems with many parts** stay one question, per the labelling rules: 6.041's Fall 2010 final returns 2 questions with 8 and 9 parts each. Splitting them into parts is a product decision for later.

### Where the baseline went wrong

1. **Numbered lists inside a question start new questions.** This is the main cause of low precision. It covers operation lists ("1. MARK-YELLOW(i)"), multiple-choice options ("1. P and Q are equivalent"), numbered conditions and parts numbered "1. (10 points)". Examples: 6.041 quiz 1 returns 26 pieces for 2 questions, 6.034 final 2008 returns 66 for 12, and 6.046J quiz 1 returns 14 for 7.
2. **Headings the pattern does not know are missed.** Examples are "Quiz 1, Question 1, Rules (50 points)" and "1 Team Problem: A Mystery". Text before the first recognised heading is dropped, so 6.034 final 2008 loses its first four questions and the 6.042J recitation loses its only one.
3. **Repeated answer pages** (6.041 quiz 1) and **cover-page grading grids** add extra pieces.

## Reproduce

```bash
python bench/fetch_ocw.py                                         # PDFs, if not already in data/ocw/
python bench/ingest_eval.py -v                                    # table with each document's mistakes
python bench/ingest_eval.py --json bench/results/ingest/<name>.json
```
