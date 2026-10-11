"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import QuestionItem from "@/components/QuestionItem";
import { errorMessage, listQuestions } from "@/lib/api";
import type { Question } from "@/lib/api";

interface Props {
  course: string;
  topics: string[];
  refreshKey: number;
  onUploadClick: () => void;
}

export default function QuestionBank({ course, topics, refreshKey, onUploadClick }: Props) {
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

  // Reset the filters when the course changes.
  useEffect(() => {
    setTopic("");
    setDifficulty("");
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

  const filtered = topic !== "" || difficulty !== "";
  const empty = loaded && items.length === 0 && !error;

  return (
    <section aria-label="Questions">
      <div className="filters">
        {topics.length > 0 && (
          <div className="filter-row">
            <span id="qb-topic" className="filter-name">
              Topic
            </span>
            <div className="choices" role="radiogroup" aria-labelledby="qb-topic">
              {[""].concat(topics).map((t) => (
                <button
                  key={t}
                  type="button"
                  role="radio"
                  aria-checked={topic === t}
                  className="choice"
                  onClick={() => setTopic(t)}
                >
                  {t || "All"}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="filter-row">
          <span id="qb-diff" className="filter-name">
            Difficulty
          </span>
          <div className="choices" role="radiogroup" aria-labelledby="qb-diff">
            {["", "1", "2", "3", "4", "5"].map((d) => (
              <button
                key={d}
                type="button"
                role="radio"
                aria-checked={difficulty === d}
                className="choice"
                onClick={() => setDifficulty(d)}
              >
                {d || "Any"}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <p className="notice notice-error" role="alert">
          {error}
        </p>
      )}

      {empty && !filtered && (
        <div className="sheet sheet-empty">
          <p>This course has no questions yet.</p>
          <p>
            <button type="button" className="text-button" onClick={onUploadClick}>
              Upload a past exam
            </button>{" "}
            and its questions will appear here, laid out as they were printed.
          </p>
        </div>
      )}
      {empty && filtered && (
        <div className="sheet sheet-empty">
          <p>No questions match these filters.</p>
          <p>
            <button
              type="button"
              className="text-button"
              onClick={() => {
                setTopic("");
                setDifficulty("");
              }}
            >
              Clear filters
            </button>
          </p>
        </div>
      )}

      {items.length > 0 && (
        <div className="sheet">
          <ol className="questions">
            {items.map((q, i) => (
              <li key={q.id}>
                <QuestionItem question={q} number={i + 1} />
              </li>
            ))}
          </ol>
        </div>
      )}

      <div className="below-sheet" aria-live="polite">
        {loading && <p className="muted">Loading questions…</p>}
        {!loading && cursor !== null && (
          <button type="button" className="btn-quiet" onClick={() => void load(cursor)}>
            Show more questions
          </button>
        )}
      </div>
    </section>
  );
}
