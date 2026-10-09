"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { errorMessage, uploadDocument } from "@/lib/api";
import type { Course, DocumentOut } from "@/lib/api";

interface Props {
  courses: Course[];
  selected: string;
  clientId: string;
  onUploaded: () => void;
}

export default function UploadForm({ courses, selected, clientId, onUploaded }: Props) {
  const [course, setCourse] = useState("");
  const [kind, setKind] = useState("exam");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentOut | null>(null);
  const [inputKey, setInputKey] = useState(0);

  const effectiveCourse = course || selected;

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file || !effectiveCourse) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const doc = await uploadDocument(effectiveCourse, kind, clientId, file);
      setResult(doc);
      setFile(null);
      setInputKey((k) => k + 1);
      onUploaded();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card no-print" aria-labelledby="upload-h">
      <h2 id="upload-h" className="mb-4 text-lg font-semibold">
        Upload a PDF
      </h2>
      <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2">
        <div>
          <label htmlFor="up-course" className="label">
            Course
          </label>
          <select
            id="up-course"
            className="field"
            value={effectiveCourse}
            onChange={(e) => setCourse(e.target.value)}
            disabled={courses.length === 0}
          >
            {courses.length === 0 && <option value="">No courses</option>}
            {courses.map((c) => (
              <option key={c.id} value={c.code}>
                {c.code}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="up-kind" className="label">
            Kind
          </label>
          <select id="up-kind" className="field" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="exam">Exam</option>
            <option value="syllabus">Syllabus</option>
          </select>
        </div>
        <div className="sm:col-span-2">
          <label htmlFor="up-file" className="label">
            PDF file
          </label>
          <input
            key={inputKey}
            id="up-file"
            type="file"
            accept="application/pdf,.pdf"
            className="field"
            onChange={(e) => setFile(e.target.files && e.target.files.length > 0 ? e.target.files[0] : null)}
          />
        </div>
        <div className="sm:col-span-2">
          <button type="submit" className="btn" disabled={busy || !file || !effectiveCourse}>
            {busy ? "Uploading and processing..." : "Upload"}
          </button>
        </div>
        <div className="sm:col-span-2" aria-live="polite">
          {error && (
            <p className="alert-error" role="alert">
              {error}
            </p>
          )}
          {result && (
            <p className="alert-ok">
              {result.filename}: {result.status}. {result.question_count} new question
              {result.question_count === 1 ? "" : "s"} added.
            </p>
          )}
        </div>
      </form>
    </section>
  );
}
