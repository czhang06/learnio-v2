"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage, listQuestions } from "@/lib/api";
import type { Question } from "@/lib/api";

interface Props {
  course: string;
  topics: string[];
  refreshKey: number;
}

export default function QuestionBank({ course, topics, refreshKey }: Props) {
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [items, setItems] = useState<Question[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const seq = useRef(0);

  const load = useCallback(
    async (after: number | null) => {
      if (!course) return;
      const my = ++seq.current;
      setLoading(true);
      setError(null);
      try {
        const page = await listQuestions({
          courseCode: course,
          topic: topic || undefined,
          difficulty: difficulty ? Number(difficulty) : undefined,
          after,
        });
        if (my !== seq.current) return;
        setItems((prev) => (after === null ? page.items : prev.concat(page.items)));
        setCursor(page.next_cursor ?? null);
        setLoaded(true);
      } catch (err) {
        if (my !== seq.current) return;
        setError(errorMessage(err));
      } finally {
        if (my === seq.current) setLoading(false);
      }
    },
    [course, topic, difficulty]
  );

  // Reset the topic filter when the course changes.
  useEffect(() => {
    setTopic("");
  }, [course]);

  // Reload from the start whenever the filters, course or upload counter change.
  useEffect(() => {
    setItems([]);
    setCursor(null);
    setLoaded(false);
    if (course) {
      void load(null);
    }
  }, [load, course, refreshKey]);

  return (
    <section className="card no-print" aria-labelledby="bank-h">
      <h2 id="bank-h" className="mb-4 text-lg font-semibold">
        Question bank
      </h2>
      <div className="mb-4 grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="qb-topic" className="label">
            Topic
          </label>
          <select id="qb-topic" className="field" value={topic} onChange={(e) => setTopic(e.target.value)}>
            <option value="">All topics</option>
            {topics.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="qb-diff" className="label">
            Difficulty
          </label>
          <select id="qb-diff" className="field" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="">Any</option>
            {[1, 2, 3, 4, 5].map((d) => (
              <option key={d} value={String(d)}>
                {d}
              </option>
            ))}
          </select>
        </div>
      </div>

      {!course && <p className="muted text-sm">Select a course to browse its questions.</p>}
      {error && (
        <p className="alert-error mb-3" role="alert">
          {error}
        </p>
      )}
      {loaded && items.length === 0 && !error && <p className="muted text-sm">No questions match.</p>}

      <ol className="space-y-3">
        {items.map((q) => (
          <li key={q.id} className="rounded-lg border p-3 text-sm" style={{ borderColor: "var(--border)" }}>
            <p className="whitespace-pre-wrap">{q.text}</p>
            <p className="muted mt-2 text-xs">
              Difficulty {q.difficulty}
              {q.topics.length > 0 ? " | " + q.topics.join(", ") : ""}
            </p>
          </li>
        ))}
      </ol>

      <div className="mt-4" aria-live="polite">
        {loading && <p className="muted text-sm">Loading...</p>}
        {!loading && cursor !== null && (
          <button type="button" className="btn-secondary" onClick={() => void load(cursor)}>
            Load more
          </button>
        )}
      </div>
    </section>
  );
}
