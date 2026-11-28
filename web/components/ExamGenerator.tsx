"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import QuestionItem from "@/components/QuestionItem";
import { useAccount } from "@/lib/account";
import { errorMessage, generateExam, getAttempt, listAttempts, markAnswer, retryAttempt, submitAttempt } from "@/lib/api";
import type { Attempt, AttemptSummary, Exam, Result } from "@/lib/api";
import { formatMarks, parseQuestion } from "@/lib/questionFormat";
import type { Marks } from "@/lib/questionFormat";

interface Props {
  course: string;
  topics: string[];
  clientId: string;
}

function clamp(n: number, lo: number, hi: number): number {
  if (Number.isNaN(n)) return lo;
  return Math.min(hi, Math.max(lo, Math.round(n)));
}

/** The exam's total, when every question states its marks in the same unit. */
function totalMarks(exam: Exam): Marks | null {
  let total: Marks | null = null;
  for (const q of exam.questions) {
    const marks = parseQuestion(q.text).marks;
    if (!marks || (total && total.unit !== marks.unit)) return null;
    total = { value: (total ? total.value : 0) + marks.value, unit: marks.unit };
  }
  return total;
}

export default function ExamGenerator({ course, topics, clientId }: Props) {
  const [picked, setPicked] = useState<string[]>([]);
  const [num, setNum] = useState("10");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exam, setExam] = useState<Exam | null>(null);
  const account = useAccount();
  const signedIn = account.status === "signed-in";
  const [marks, setMarks] = useState<Record<number, Result | null>>({});
  const [results, setResults] = useState<Attempt | null>(null);
  const [history, setHistory] = useState<AttemptSummary[]>([]);
  const [historyKey, setHistoryKey] = useState(0);

  useEffect(() => {
    setPicked([]);
    setExam(null);
    setResults(null);
    setError(null);
  }, [course]);

  useEffect(() => {
    if (!signedIn || !course) {
      setHistory([]);
      return;
    }
    let cancelled = false;
    listAttempts(course)
      .then((list) => !cancelled && setHistory(list))
      .catch(() => !cancelled && setHistory([]));
    return () => {
      cancelled = true;
    };
  }, [signedIn, course, historyKey]);

  function show(next: Exam, nextMarks: Record<number, Result | null> = {}, done: Attempt | null = null) {
    setExam(next);
    setMarks(nextMarks);
    setResults(done);
  }

  function mark(questionId: number, result: Result | null) {
    if (!exam?.attempt_id) return;
    const previous = marks[questionId] ?? null;
    setMarks((m) => ({ ...m, [questionId]: result }));
    markAnswer(exam.attempt_id, questionId, result).catch((err) => {
      setMarks((m) => ({ ...m, [questionId]: previous }));
      setError(errorMessage(err));
    });
  }

  async function finish() {
    if (!exam?.attempt_id) return;
    setBusy(true);
    setError(null);
    try {
      setResults(await submitAttempt(exam.attempt_id));
      setHistoryKey((k) => k + 1);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    if (!exam?.attempt_id) return;
    setBusy(true);
    setError(null);
    try {
      show(await retryAttempt(exam.attempt_id));
      setHistoryKey((k) => k + 1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function reopen(id: number) {
    setError(null);
    try {
      const attempt = await getAttempt(id);
      const restored: Record<number, Result | null> = {};
      for (const q of attempt.questions) restored[q.id] = q.result;
      show(
        { course_code: attempt.course_code, questions: attempt.questions, attempt_id: attempt.id },
        restored,
        attempt.submitted_at ? attempt : null
      );
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  const total = useMemo(() => (exam ? totalMarks(exam) : null), [exam]);

  function toggle(t: string) {
    setPicked((prev) => (prev.indexOf(t) >= 0 ? prev.filter((x) => x !== t) : prev.concat(t)));
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!course) return;
    setBusy(true);
    setError(null);
    try {
      const result = await generateExam(
        {
          course_code: course,
          topics: picked,
          num_questions: clamp(Number(num), 1, 100),
        },
        clientId
      );
      show(result);
      if (result.attempt_id) setHistoryKey((k) => k + 1);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Practice exam">
      <form onSubmit={submit} className="setup no-print">
        {topics.length > 0 && (
          <fieldset>
            <legend className="label">
              Topics <span className="hint">leave all unpicked to draw from every topic</span>
            </legend>
            <div className="choices">
              {topics.map((t) => (
                <button
                  key={t}
                  type="button"
                  aria-pressed={picked.indexOf(t) >= 0}
                  className="choice"
                  onClick={() => toggle(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </fieldset>
        )}

        <div>
          <label htmlFor="ex-num" className="label">
            Questions
          </label>
          <input
            id="ex-num"
            type="number"
            min={1}
            max={100}
            className="field field-narrow"
            value={num}
            onChange={(e) => setNum(e.target.value)}
          />
        </div>

        {account.status === "guest" && account.canSignIn && (
          <p className="hint guest-hint">
            <button type="button" className="text-button" onClick={account.signIn}>
              Sign in
            </button>{" "}
            to mark your answers, see your results by topic, and get exams that lean toward what you find hard.
          </p>
        )}
        {error && (
          <p className="notice notice-error" role="alert">
            {error}
          </p>
        )}
        <div className="form-actions">
          <button type="submit" className="btn" disabled={busy || !course}>
            {busy ? "Generating…" : exam ? "Generate another exam" : "Generate exam"}
          </button>
          {exam && exam.questions.length > 0 && (
            <button type="button" className="btn-quiet" onClick={() => window.print()}>
              Print or save as PDF
            </button>
          )}
        </div>
      </form>

      <div aria-live="polite">
        {exam && exam.questions.length === 0 && (
          <div className="empty">
            <p className="empty-title">No questions match these settings</p>
            <p>Pick more topics, or none to draw from every topic, then generate again.</p>
          </div>
        )}
        {exam && exam.questions.length > 0 && (
          <div className="sheet">
            <header className="sheet-head">
              <h2 className="sheet-title">{exam.course_code} practice exam</h2>
              <p className="sheet-facts">
                {exam.questions.length} question{exam.questions.length === 1 ? "" : "s"}
                {total ? ", " + formatMarks(total) + " in total" : ""}
              </p>
            </header>
            <ol className="questions">
              {exam.questions.map((q, i) => (
                <li key={q.id}>
                  <QuestionItem
                    question={q}
                    number={i + 1}
                    result={marks[q.id] ?? null}
                    onMark={exam.attempt_id && !results ? (r) => mark(q.id, r) : undefined}
                  />
                </li>
              ))}
            </ol>
            {exam.attempt_id && !results && (
              <div className="form-actions sheet-foot no-print">
                <button type="button" className="btn" disabled={busy} onClick={finish}>
                  Finish and see results
                </button>
                <span className="hint">
                  {Object.values(marks).filter((m) => m).length} of {exam.questions.length} marked
                </span>
              </div>
            )}
          </div>
        )}
        {results && <Results attempt={results} busy={busy} onRetry={retry} />}
      </div>

      {signedIn && history.length > 0 && (
        <section className="history no-print" aria-label="Past attempts">
          <h2 className="label">Past attempts</h2>
          <ul className="history-list">
            {history.map((a) => (
              <li key={a.id}>
                <button type="button" className="text-button" onClick={() => reopen(a.id)}>
                  {new Date(a.created_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
                </button>
                <span className="hint">
                  {a.tally.right} right, {a.tally.wrong} wrong
                  {a.tally.skipped ? ", " + a.tally.skipped + " skipped" : ""}
                  {a.submitted_at ? "" : " (in progress)"}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}

function Results({ attempt, busy, onRetry }: { attempt: Attempt; busy: boolean; onRetry: () => void }) {
  const { right, wrong, skipped, unmarked } = attempt.tally;
  const marked = right + wrong;
  return (
    <section className="results no-print" aria-label="Results">
      <h2 className="sheet-title">Results</h2>
      <p className="results-score">
        {right} of {marked} right
        {skipped ? ", " + skipped + " skipped" : ""}
        {unmarked ? ", " + unmarked + " not marked" : ""}
      </p>
      {attempt.by_topic.length > 0 && (
        <>
        <h3 className="label" id="by-topic">By topic, weakest first</h3>
        <table className="results-table" aria-labelledby="by-topic">
          <thead>
            <tr>
              <th scope="col">Topic</th>
              <th scope="col">Right</th>
              <th scope="col">Wrong</th>
            </tr>
          </thead>
          <tbody>
            {attempt.by_topic.map((t) => (
              <tr key={t.topic}>
                <th scope="row">{t.topic}</th>
                <td>{t.right}</td>
                <td>{t.wrong}</td>
              </tr>
            ))}
          </tbody>
        </table>
        </>
      )}
      <p className="hint">Your next exams in this course lean toward the topics you got wrong.</p>
      {wrong + skipped > 0 && (
        <div className="form-actions">
          <button type="button" className="btn" disabled={busy} onClick={onRetry}>
            Retry the {wrong + skipped} you got wrong or skipped
          </button>
        </div>
      )}
    </section>
  );
}
