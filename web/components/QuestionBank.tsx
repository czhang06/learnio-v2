"use client";

import type { KeyboardEvent } from "react";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import QuestionItem from "@/components/QuestionItem";
import { errorMessage, listQuestions, listTopics } from "@/lib/api";
import type { Question, QuestionPage } from "@/lib/api";
import { coursePath } from "@/lib/courses";

interface Props {
  course: string;
  /** From the server; null if it could not load them, then they load here. */
  topics: string[] | null;
  /** The topic filter, from the URL (?topic=). "" for all topics. */
  topic: string;
  /** The first page of questions, from the server; null to load it here. */
  initial: QuestionPage | null;
}

/**
 * The question bank. The first page arrives with the HTML; the topic filter
 * lives in the URL, so a filtered bank can be refreshed, shared and reached
 * with the back button. Changing it asks the server for the new first page;
 * "Show more" pages are loaded here.
 */
export default function QuestionBank({ course, topics: serverTopics, topic, initial }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [topics, setTopics] = useState<string[] | null>(serverTopics);
  const [items, setItems] = useState<Question[]>(initial?.items ?? []);
  const [cursor, setCursor] = useState<number | null>(initial?.next_cursor ?? null);
  const [loading, setLoading] = useState(initial === null);
  const [loaded, setLoaded] = useState(initial !== null);
  const [error, setError] = useState<string | null>(null);
  // The filter shows the newly picked topic at once, while its questions load.
  const [picked, setPicked] = useState(topic);
  const [changing, startChange] = useTransition();
  const seq = useRef(0);

  const load = useCallback(
    async (after: number | null) => {
      const my = ++seq.current;
      setLoading(true);
      setError(null);
      try {
        const page = await listQuestions({ courseCode: course, topic: topic || undefined, after });
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

  // The server could not load them in time (the API was waking up): load here.
  useEffect(() => {
    if (initial === null) void load(null);
  }, [initial, load]);
  useEffect(() => {
    if (serverTopics !== null) return;
    let cancelled = false;
    listTopics(course)
      .then((t) => !cancelled && setTopics(t))
      .catch(() => !cancelled && setTopics([]));
    return () => {
      cancelled = true;
    };
  }, [course, serverTopics]);

  function choose(next: string) {
    setPicked(next);
    const query = next ? "?topic=" + encodeURIComponent(next) : "";
    startChange(() => router.replace(pathname + query, { scroll: false }));
  }

  const options = [""].concat(topics ?? []);
  function onTopicKey(e: KeyboardEvent<HTMLDivElement>) {
    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[e.key];
    if (!step && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    const i = options.indexOf(picked);
    const next = e.key === "Home" ? 0 : e.key === "End" ? options.length - 1 : (i + (step ?? 0) + options.length) % options.length;
    choose(options[next]);
    const group = e.currentTarget;
    requestAnimationFrame(() => (group.querySelectorAll("button")[next] as HTMLButtonElement | undefined)?.focus());
  }

  const filtered = topic !== "";
  const waiting = changing || (loading && items.length === 0);
  const empty = loaded && !waiting && items.length === 0 && !error;
  const topicsReady = topics !== null;

  return (
    <section aria-label="Questions" className={!topicsReady || options.length > 1 ? "bank" : undefined}>
      {!topicsReady && <div className="filters filters-loading" aria-hidden="true" />}
      {topicsReady && options.length > 1 && (
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
                  aria-checked={picked === t}
                  tabIndex={picked === t ? 0 : -1}
                  className="option"
                  onClick={() => choose(t)}
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
              <Link className="text-button" href={coursePath(course, "upload")}>
                Upload a past exam
              </Link>{" "}
              and its questions will appear here, laid out as they were printed.
            </p>
          </div>
        )}
        {empty && filtered && (
          <div className="empty">
            <p className="empty-title">No questions on this topic yet</p>
            <p>
              <button type="button" className="text-button" onClick={() => choose("")}>
                Show all topics
              </button>
            </p>
          </div>
        )}

        <h2 id="question-list" className="sr-note" tabIndex={-1}>
          Questions{filtered ? " on " + topic : ""}
        </h2>
        {/* While a new topic's questions load, placeholder cards stand in for
            the list, so nothing jumps when they arrive. */}
        {waiting ? (
          <div className="sheet" aria-hidden="true">
            {[0, 1, 2].map((i) => (
              <div key={i} className="question-skeleton" />
            ))}
          </div>
        ) : (
          items.length > 0 && (
            <div className="sheet">
              <ol className="questions">
                {items.map((q, i) => (
                  <li key={q.id}>
                    <QuestionItem question={q} number={i + 1} />
                  </li>
                ))}
              </ol>
            </div>
          )
        )}

        <div className="below-sheet" aria-live="polite">
          {waiting && <p className="sr-note">Loading questions…</p>}
          {!waiting && loading && <p className="muted">Loading questions…</p>}
          {!waiting && !loading && cursor !== null && (
            <button type="button" className="btn-quiet" onClick={() => void load(cursor)}>
              Show more questions
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
