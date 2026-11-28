"use client";

import { usePathname } from "next/navigation";

/** First tab stop: jump past the course bar (and, on the question bank, the
 * topic filter) to the content. Pages without a bank pass bank={false}. */
export default function SkipLink({ bank = true }: { bank?: boolean }) {
  const onBank = bank && /^\/c\/[^/]+\/?$/.test(usePathname());
  return (
    <a className="skip-link" href={onBank ? "#question-list" : "#main"}>
      Skip to {onBank ? "questions" : "content"}
    </a>
  );
}
