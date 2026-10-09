"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { errorMessage, generateExam } from "@/lib/api";
import type { Exam } from "@/lib/api";

interface Props {
  course: string;
  topics: string[];
  clientId: string;
}

function clamp(n: number, lo: number, hi: number): number {
  if (Number.isNaN(n)) return lo;
  return Math.min(hi, Math.max(lo, Math.round(n)));
}

export default function ExamGenerator({ course, topics, clientId }: Props) {
  const [picked, setPicked] = useState<string[]>([]);
  const [num, setNum] = useState("20");
  const [minD, setMinD] = useState("1");
  const [maxD, setMaxD] = useState("5");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exam, setExam] = useState<Exam | null>(null);

  useEffect(() => {
    setPicked([]);
    setExam(null);
    setError(null);
  }, [course]);

  function toggle(t: string) {
    setPicked((prev) => (prev.indexOf(t) >= 0 ? prev.filter((x) => x !== t) : prev.concat(t)));
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!course) return;
    const lo = clamp(Number(minD), 1, 5);
    const hi = clamp(Number(maxD), 1, 5);
    if (lo > hi) {
      setError("Minimum difficulty cannot be greater than maximum difficulty.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await generateExam(
        {
          course_code: course,
          topics: picked,
          num_questions: clamp(Number(num), 1, 100),
          min_difficulty: lo,
          max_difficulty: hi,
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
    <section aria-labelledby="exam-h" className="space-y-4">
      <div className="card no-print">
        <h2 id="exam-h" className="mb-4 text-lg font-semibold">
          Exam generator
        </h2>
        <form onSubmit={submit} className="grid gap-4">
          <fieldset>
            <legend className="label">Topics (none selected means all)</legend>
            {topics.length === 0 ? (
              <p className="muted text-sm">This course has no topics.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {topics.map((t, i) => (
                  <label
                    key={t}
                    htmlFor={"ex-topic-" + i}
                    className="flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-1.5 text-sm"
                    style={{ borderColor: "var(--border)" }}
                  >
                    <input
                      id={"ex-topic-" + i}
                      type="checkbox"
                      checked={picked.indexOf(t) >= 0}
                      onChange={() => toggle(t)}
                    />
                    {t}
                  </label>
                ))}
              </div>
            )}
          </fieldset>

          <div className="grid gap-3 sm:grid-cols-3">
            <div>
              <label htmlFor="ex-num" className="label">
                Number of questions (1-100)
              </label>
              <input
                id="ex-num"
                type="number"
                min={1}
                max={100}
                className="field"
                value={num}
                onChange={(e) => setNum(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="ex-min" className="label">
                Min difficulty (1-5)
              </label>
              <input
                id="ex-min"
                type="number"
                min={1}
                max={5}
                className="field"
                value={minD}
                onChange={(e) => setMinD(e.target.value)}
              />
            </div>
            <div>
              <label htmlFor="ex-max" className="label">
                Max difficulty (1-5)
              </label>
              <input
                id="ex-max"
                type="number"
                min={1}
                max={5}
                className="field"
                value={maxD}
                onChange={(e) => setMaxD(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <p className="alert-error" role="alert">
              {error}
            </p>
          )}
          <div>
            <button type="submit" className="btn" disabled={busy || !course}>
              {busy ? "Generating..." : "Generate exam"}
            </button>
          </div>
        </form>
      </div>

      {exam && (
        <div className="card print-area" aria-live="polite">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-lg font-semibold">Practice exam: {exam.course_code}</h3>
            <button type="button" className="btn-secondary no-print" onClick={() => window.print()}>
              Print / Save as PDF
            </button>
          </div>
          {exam.questions.length === 0 ? (
            <p className="muted text-sm">No questions matched those settings.</p>
          ) : (
            <ol className="list-decimal space-y-5 pl-6">
              {exam.questions.map((q) => (
                <li key={q.id} className="text-sm leading-relaxed">
                  <p className="whitespace-pre-wrap">{q.text}</p>
                  <p className="muted no-print mt-1 text-xs">
                    Difficulty {q.difficulty}
                    {q.topics.length > 0 ? " | " + q.topics.join(", ") : ""}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </section>
  );
}
