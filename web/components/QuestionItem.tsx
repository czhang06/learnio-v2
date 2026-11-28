import { useMemo, useState } from "react";
import QuestionText from "@/components/QuestionText";
import { apiUrl } from "@/lib/api";
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

const MARKS: { value: Result; label: string }[] = [
  { value: "right", label: "Got it right" },
  { value: "wrong", label: "Got it wrong" },
  { value: "skipped", label: "Skipped" },
];

export default function QuestionItem({ question, number, result, onMark }: Props) {
  const parsed = useMemo(() => parseQuestion(question.text), [question.text]);
  const account = useAccount();
  const [saveError, setSaveError] = useState(false);
  const saved = account.saved.has(question.id);

  function toggleSave() {
    setSaveError(false);
    account.save(question.id, !saved).catch(() => setSaveError(true));
  }
  return (
    <article className="question">
      <span className="question-number" aria-hidden="true">
        {number}
      </span>
      <div>
        {question.image_url ? (
          <>
            {/* The question as printed: matrices, maths and figures survive
                here, unlike in the extracted text. */}
            <img
              className="question-image"
              src={apiUrl(question.image_url)}
              alt={"Question: " + question.text.replace(/\s+/g, " ").slice(0, 300)}
              loading="lazy"
            />
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
                className={"mark mark-" + m.value}
                aria-pressed={result === m.value}
                onClick={() => onMark(result === m.value ? null : m.value)}
              >
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
