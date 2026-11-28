import { useMemo, useState } from "react";
import QuestionText from "@/components/QuestionText";
import { imageUrl } from "@/lib/api";
import { useAccount } from "@/lib/account";
import type { Question, Result } from "@/lib/api";
import { formatMarks, parseQuestion } from "@/lib/questionFormat";

interface Props {
  question: Question;
  number: number;
  /** In an exam attempt: how the user marked themselves, and how to change it. */
  result?: Result | null;
  onMark?: (result: Result | null) => void;
}

// Class names are written out in full: Tailwind keeps only the class names it
// finds as literal strings in the source, so "mark-" + value would be dropped.
const MARKS: { value: Result; label: string; className: string; numberClass: string; spoken: string }[] = [
  { value: "right", label: "Got it right", className: "mark mark-right", numberClass: "question-number is-right", spoken: "marked right" },
  { value: "wrong", label: "Got it wrong", className: "mark mark-wrong", numberClass: "question-number is-wrong", spoken: "marked wrong" },
  { value: "skipped", label: "Skipped", className: "mark mark-skipped", numberClass: "question-number is-skipped", spoken: "skipped" },
];

function MarkIcon({ value }: { value: Result }) {
  return (
    <svg className="mark-icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2.25" strokeLinecap="round" strokeLinejoin="round">
      {value === "right" && <path d="M3 8.5l3.2 3L13 4.5" />}
      {value === "wrong" && <path d="M4 4l8 8M12 4l-8 8" />}
      {value === "skipped" && <path d="M3.5 8h9" />}
    </svg>
  );
}

export default function QuestionItem({ question, number, result, onMark }: Props) {
  const parsed = useMemo(() => parseQuestion(question.text), [question.text]);
  const account = useAccount();
  const [saveError, setSaveError] = useState(false);
  const saved = account.saved.has(question.id);

  function toggleSave() {
    setSaveError(false);
    account.save(question.id, !saved).catch(() => setSaveError(true));
  }
  const marked = MARKS.find((m) => m.value === result);
  return (
    <article className="question">
      <span className={marked ? marked.numberClass : "question-number"} aria-hidden="true">
        {marked ? <MarkIcon value={marked.value} /> : number}
      </span>
      <div>
        {question.image_url ? (
          <>
            {/* The question as printed: matrices, maths and figures survive
                here, unlike in the extracted text. */}
            <div className="question-paper">
              <img
                className="question-image"
                src={imageUrl(question.image_url)}
                alt={"Question " + number + ": " + question.text.replace(/\s+/g, " ").slice(0, 300)}
                width={question.image_width ?? undefined}
                height={question.image_height ?? undefined}
                loading={number <= 2 ? "eager" : "lazy"}
                decoding="async"
                // The first question is usually the largest thing on screen: fetch it first.
                // (Plain attribute: React 18 doesn't know the camelCase prop.)
                {...(number === 1 ? { fetchpriority: "high" } : {})}
              />
            </div>
            <details className="question-as-text no-print">
              <summary>Show as text</summary>
              <QuestionText blocks={parsed.blocks} />
            </details>
          </>
        ) : (
          <>
            {parsed.marks && <span className="question-marks">{formatMarks(parsed.marks)}</span>}
            <QuestionText blocks={parsed.blocks} />
          </>
        )}
        {onMark && (
          <div className="marks no-print" role="group" aria-label={"How did question " + number + " go?"}>
            {MARKS.map((m) => (
              <button
                key={m.value}
                type="button"
                className={m.className}
                aria-pressed={result === m.value}
                onClick={() => onMark(result === m.value ? null : m.value)}
              >
                <MarkIcon value={m.value} />
                {m.label}
              </button>
            ))}
          </div>
        )}
        <div className="question-meta no-print">
          {account.status === "signed-in" && (
            <button type="button" className="text-button save-button" aria-pressed={saved} onClick={toggleSave}>
              {saved ? "Saved" : "Save"}
              {saveError && <span className="sr-note"> (could not save, try again)</span>}
            </button>
          )}
          {question.topics.length > 0 && (
            <span className="topic-tags">
              {question.topics.map((t) => (
                <span key={t} className="topic-tag">
                  {t}
                </span>
              ))}
            </span>
          )}
        </div>
      </div>
    </article>
  );
}
