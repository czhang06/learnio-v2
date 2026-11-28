"use client";

import type { KeyboardEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import QuestionItem from "@/components/QuestionItem";
import { errorMessage, listQuestions } from "@/lib/api";
import type { Question } from "@/lib/api";

interface Props {
  course: string;
  topics: string[];
  /** False while the course's topics load: their space is held so nothing jumps. */
  topicsReady: boolean;
  refreshKey: number;
  onUploadClick: () => void;
}

export default function QuestionBank({ course, topics, topicsReady, refreshKey, onUploadClick }: Props) {
  const [topic, setTopic] = useState("");
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
    [course, topic]
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

  const filtered = topic !== "";
  const options = [""].concat(topics);

  function onTopicKey(e: KeyboardEvent<HTMLDivElement>) {
    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
    if (!step && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    const i = options.indexOf(topic);
    const next = e.key === "Home" ? 0 : e.key === "End" ? options.length - 1 : (i + (step ?? 0) + options.length) % options.length;
    setTopic(options[next]);
    const group = e.currentTarget;
    requestAnimationFrame(() => (group.querySelectorAll("button")[next] as HTMLButtonElement | undefined)?.focus());
  }
  const empty = loaded && items.length === 0 && !error;

  return (
    <section aria-label="Questions" className={topics.length > 0 || !topicsReady ? "bank" : undefined}>
      {!topicsReady && <div className="filters filters-loading" aria-hidden="true" />}
      {topicsReady && topics.length > 0 && (
        <section className="filters" aria-label="Filter questions">
          <div>
            <p id="qb-topic" className="filter-name">
              Topic
            </p>
            {/* One tab stop for the whole group; arrow keys move between topics. */}
            <div className="options" role="radiogroup" aria-labelledby="qb-topic" onKeyDown={onTopicKey}>
              {options.map((t) => (
                <button
                  key={t}
                  type="button"
                  role="radio"
                  aria-checked={topic === t}
                  tabIndex={topic === t ? 0 : -1}
                  className="option"
                  onClick={() => setTopic(t)}
                >
                  {t || "All topics"}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      <div>
        {error && (
          <p className="notice notice-error" role="alert">
            {error}
          </p>
        )}

        {empty && !filtered && (
          <div className="empty">
            <p className="empty-title">No questions yet</p>
            <p>
              <button type="button" className="text-button" onClick={onUploadClick}>
                Upload a past exam
              </button>{" "}
              and its questions will appear here, laid out as they were printed.
            </p>
          </div>
        )}
        {empty && filtered && (
          <div className="empty">
            <p className="empty-title">No questions on this topic yet</p>
            <p>
              <button
                type="button"
                className="text-button"
                onClick={() => setTopic("")}
              >
                Show all topics
              </button>
            </p>
          </div>
        )}

        <h2 id="question-list" className="sr-note" tabIndex={-1}>
          Questions{filtered ? " on " + topic : ""}
        </h2>
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

        {/* First load: placeholder cards hold the questions' place, so nothing
            jumps when they arrive. The status line is for screen readers then. */}
        {loading && items.length === 0 && (
          <div className="sheet" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="question-skeleton" />
            ))}
          </div>
        )}

        <div className="below-sheet" aria-live="polite">
          {loading && <p className={items.length === 0 ? "sr-note" : "muted"}>Loading questions…</p>}
          {!loading && cursor !== null && (
            <button type="button" className="btn-quiet" onClick={() => void load(cursor)}>
              Show more questions
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
