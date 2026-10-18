"use client";

import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import QuestionItem from "@/components/QuestionItem";
import { errorMessage, generateExam } from "@/lib/api";
import type { Exam } from "@/lib/api";
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

  useEffect(() => {
    setPicked([]);
    setExam(null);
    setError(null);
  }, [course]);

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
      setExam(result);
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
                  <QuestionItem question={q} number={i + 1} />
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </section>
  );
}
