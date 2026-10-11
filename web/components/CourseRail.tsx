"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { createCourse, errorMessage } from "@/lib/api";
import type { Course } from "@/lib/api";

interface Props {
  courses: Course[];
  selected: string;
  loading: boolean;
  error: string | null;
  onSelect: (code: string) => void;
  onCreated: (course: Course) => void;
}

export default function CourseRail({ courses, selected, loading, error, onSelect, onCreated }: Props) {
  const [adding, setAdding] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [topics, setTopics] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      const list = topics
        .split(",")
        .map((t) => t.trim())
        .filter((t) => t.length > 0);
      const course = await createCourse(code.trim(), name.trim(), list);
      setCode("");
      setName("");
      setTopics("");
      setAdding(false);
      onCreated(course);
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="rail no-print">
      <p className="wordmark">
        Learn<span>IO</span>
      </p>

      <nav aria-labelledby="courses-h">
        <h2 id="courses-h" className="rail-heading">
          Courses
        </h2>
        {error && (
          <p className="rail-note" role="alert">
            {error}
          </p>
        )}
        {loading && <p className="rail-note">Loading courses…</p>}
        {!loading && !error && courses.length === 0 && <p className="rail-note">No courses yet.</p>}
        <ul className="course-list">
          {courses.map((c) => (
            <li key={c.id}>
              <button
                type="button"
                className="course-link"
                aria-current={c.code === selected ? "true" : undefined}
                onClick={() => onSelect(c.code)}
              >
                <span className="course-code">{c.code}</span>
                {c.name && <span className="course-name">{c.name}</span>}
              </button>
            </li>
          ))}
        </ul>
      </nav>

      <div className="rail-add">
        {!adding ? (
          <button type="button" className="rail-add-toggle" onClick={() => setAdding(true)}>
            Add a course
          </button>
        ) : (
          <form onSubmit={submit} className="rail-form" aria-label="Add a course">
            <div>
              <label htmlFor="new-code" className="label">
                Course code
              </label>
              <input
                id="new-code"
                className="field"
                required
                autoFocus
                maxLength={32}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="CPSC 304"
              />
            </div>
            <div>
              <label htmlFor="new-name" className="label">
                Name <span className="hint">optional</span>
              </label>
              <input
                id="new-name"
                className="field"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Introduction to Databases"
              />
            </div>
            <div>
              <label htmlFor="new-topics" className="label">
                Topics <span className="hint">separated by commas</span>
              </label>
              <input
                id="new-topics"
                className="field"
                value={topics}
                onChange={(e) => setTopics(e.target.value)}
                placeholder="SQL, normalization, indexing"
              />
            </div>
            {formError && (
              <p className="notice notice-error" role="alert">
                {formError}
              </p>
            )}
            <div className="form-actions">
              <button type="submit" className="btn" disabled={busy || code.trim() === ""}>
                {busy ? "Adding…" : "Add course"}
              </button>
              <button type="button" className="text-button" onClick={() => setAdding(false)}>
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
    </aside>
  );
}
