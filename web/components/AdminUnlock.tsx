"use client";

import { useState } from "react";
import type { FormEvent } from "react";
import { checkAdminKey, errorMessage } from "@/lib/api";
import { setAdminKey } from "@/lib/adminKey";

interface Props {
  onUnlocked: () => void;
}

/** Shown in place of the upload form on the read-only demo. */
export default function AdminUnlock({ onUnlocked }: Props) {
  const [open, setOpen] = useState(false);
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (await checkAdminKey(key.trim())) {
        setAdminKey(key.trim());
        onUnlocked();
      } else {
        setError("That key isn't right. Check it and try again.");
      }
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Upload" className="upload">
      <div className="empty">
        <p className="empty-title">Uploading is turned off on this demo</p>
        <p>
          The question bank here is curated, so visitors can browse it and generate practice exams but can&apos;t add
          courses or upload PDFs. To try uploading, run LearnIO locally from the{" "}
          <a className="text-button" href="https://github.com/czhang06/learnio-v2">
            GitHub repo
          </a>
          .
        </p>
        {!open ? (
          <p>
            <button type="button" className="text-button" onClick={() => setOpen(true)}>
              I have an admin key
            </button>
          </p>
        ) : (
          <form onSubmit={submit} className="unlock">
            <label htmlFor="admin-key" className="label">
              Admin key
            </label>
            <div className="unlock-row">
              <input
                id="admin-key"
                type="password"
                autoComplete="current-password"
                autoFocus
                className="field"
                value={key}
                onChange={(e) => setKey(e.target.value)}
              />
              <button type="submit" className="btn" disabled={busy || key.trim() === ""}>
                {busy ? "Checking…" : "Unlock"}
              </button>
            </div>
            {error && (
              <p className="notice notice-error" role="alert">
                {error}
              </p>
            )}
          </form>
        )}
      </div>
    </section>
  );
}
