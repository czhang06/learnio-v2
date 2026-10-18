"use client";

import { useEffect, useState } from "react";
import type { DragEvent, FormEvent } from "react";
import { errorMessage, uploadDocument } from "@/lib/api";
import type { DocumentOut } from "@/lib/api";

interface Props {
  course: string;
  clientId: string;
  onUploaded: () => void;
  onViewQuestions: () => void;
}

const KINDS = [
  { value: "exam", label: "Past exam" },
  { value: "syllabus", label: "Syllabus" },
];

function isPdf(file: File): boolean {
  return file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
}

export default function UploadForm({ course, clientId, onUploaded, onViewQuestions }: Props) {
  const [kind, setKind] = useState("exam");
  const [file, setFile] = useState<File | null>(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DocumentOut | null>(null);
  const [inputKey, setInputKey] = useState(0);

  useEffect(() => {
    setFile(null);
    setError(null);
    setResult(null);
    setInputKey((k) => k + 1);
  }, [course]);

  function choose(next: File | null) {
    setResult(null);
    if (next && !isPdf(next)) {
      setFile(null);
      setError(next.name + " is not a PDF. Choose a file ending in .pdf.");
      return;
    }
    setError(null);
    setFile(next);
  }

  function drop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setOver(false);
    choose(e.dataTransfer.files.length > 0 ? e.dataTransfer.files[0] : null);
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!file || !course) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const doc = await uploadDocument(course, kind, clientId, file);
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
    <section aria-label="Upload" className="upload">
      <form onSubmit={submit} className="form">
        <label
          htmlFor="up-file"
          className={over ? "dropzone dropzone-over" : "dropzone"}
          onDragOver={(e) => {
            e.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={drop}
        >
          <input
            key={inputKey}
            id="up-file"
            type="file"
            accept="application/pdf,.pdf"
            className="sr-only-input"
            onChange={(e) => choose(e.target.files && e.target.files.length > 0 ? e.target.files[0] : null)}
          />
          {file ? (
            <>
              <span className="dropzone-file">{file.name}</span>
              <span className="muted">Choose a different PDF</span>
            </>
          ) : (
            <>
              <span className="dropzone-file">Drop a PDF here</span>
              <span className="muted">or choose one from your computer</span>
            </>
          )}
        </label>

        <fieldset>
          <legend className="label">This PDF is a</legend>
          <div className="choices" role="radiogroup">
            {KINDS.map((k) => (
              <button
                key={k.value}
                type="button"
                role="radio"
                aria-checked={kind === k.value}
                className="choice"
                onClick={() => setKind(k.value)}
              >
                {k.label}
              </button>
            ))}
          </div>
        </fieldset>

        <div className="form-actions">
          <button type="submit" className="btn" disabled={busy || !file || !course}>
            {busy ? "Reading the PDF…" : "Upload to " + (course || "course")}
          </button>
          {busy && <span className="muted">Splitting it into questions. Long exams take a moment.</span>}
        </div>

        <div aria-live="polite">
          {error && (
            <p className="notice notice-error" role="alert">
              {error}
            </p>
          )}
          {result && (
            <p className="notice notice-ok">
              Uploaded {result.filename}.{" "}
              {result.question_count === 0
                ? "No new questions: everything in it is already in the bank."
                : result.question_count + " new question" + (result.question_count === 1 ? "" : "s") + " added."}{" "}
              <button type="button" className="text-button" onClick={onViewQuestions}>
                View questions
              </button>
            </p>
          )}
        </div>
      </form>
    </section>
  );
}
