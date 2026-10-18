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

export default function CourseBar({ courses, selected, loading, error, onSelect, onCreated }: Props) {
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
    <header className="topbar no-print">
      <div className="topbar-inner">
        <p className="wordmark">LearnIO</p>

        <nav aria-label="Courses" className="course-nav">
          {loading && <span className="topbar-note">Loading courses…</span>}
          {error && <span className="topbar-note">Courses unavailable</span>}
          <ul className="course-list">
            {courses.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  className="course-link"
                  title={c.name || undefined}
                  aria-current={c.code === selected ? "true" : undefined}
                  onClick={() => onSelect(c.code)}
                >
                  {c.code}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <div className="add">
          <button
            type="button"
            className="btn-quiet btn-small"
            aria-expanded={adding}
            aria-controls="add-course"
            onClick={() => setAdding((a) => !a)}
          >
            Add<span className="wide-only">&nbsp;course</span>
          </button>
          {adding && (
            <form
              id="add-course"
              onSubmit={submit}
              onKeyDown={(e) => {
                if (e.key === "Escape") setAdding(false);
              }}
              className="add-panel"
              aria-label="Add a course"
            >
              <p className="add-panel-title">Add a course</p>
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
      </div>
    </header>
  );
}
