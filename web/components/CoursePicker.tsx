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

export default function CoursePicker({ courses, selected, loading, error, onSelect, onCreated }: Props) {
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
      onCreated(course);
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card no-print" aria-labelledby="course-h">
      <h2 id="course-h" className="mb-4 text-lg font-semibold">
        Course
      </h2>
      {error && (
        <p className="alert-error mb-3" role="alert">
          {error}
        </p>
      )}
      <label htmlFor="course-select" className="label">
        Select a course
      </label>
      <select
        id="course-select"
        className="field"
        value={selected}
        disabled={loading || courses.length === 0}
        onChange={(e) => onSelect(e.target.value)}
      >
        {courses.length === 0 && <option value="">{loading ? "Loading..." : "No courses yet"}</option>}
        {courses.map((c) => (
          <option key={c.id} value={c.code}>
            {c.code}
            {c.name ? " - " + c.name : ""}
          </option>
        ))}
      </select>

      <form onSubmit={submit} className="mt-6 grid gap-3 sm:grid-cols-2" aria-label="Create course">
        <h3 className="text-sm font-semibold sm:col-span-2">Create a course</h3>
        <div>
          <label htmlFor="new-code" className="label">
            Code
          </label>
          <input
            id="new-code"
            className="field"
            required
            maxLength={32}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="CS101"
          />
        </div>
        <div>
          <label htmlFor="new-name" className="label">
            Name
          </label>
          <input
            id="new-name"
            className="field"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Intro to Computer Science"
          />
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="new-topics" className="label">
            Topics (comma-separated)
          </label>
          <input
            id="new-topics"
            className="field"
            value={topics}
            onChange={(e) => setTopics(e.target.value)}
            placeholder="recursion, sorting, graphs"
          />
        </div>
        {formError && (
          <p className="alert-error sm:col-span-2" role="alert">
            {formError}
          </p>
        )}
        <div className="sm:col-span-2">
          <button type="submit" className="btn" disabled={busy || code.trim() === ""}>
            {busy ? "Creating..." : "Create course"}
          </button>
        </div>
      </form>
    </section>
  );
}
