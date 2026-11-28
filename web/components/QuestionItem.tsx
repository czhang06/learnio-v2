import { useMemo } from "react";
import QuestionText from "@/components/QuestionText";
import { apiUrl } from "@/lib/api";
import type { Question } from "@/lib/api";
import { formatMarks, parseQuestion } from "@/lib/questionFormat";

interface Props {
  question: Question;
  number: number;
}

export default function QuestionItem({ question, number }: Props) {
  const parsed = useMemo(() => parseQuestion(question.text), [question.text]);
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
        <div className="question-meta no-print">
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
