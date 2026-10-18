import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How LearnIO works",
  description: "How to build a question bank from past exams and generate practice exams with LearnIO.",
};

const STEPS = [
  {
    title: "Pick a course",
    body: (
      <>
        Choose a course in the top bar. Each course keeps its own question bank. If yours isn&apos;t there, use Add
        course and list the topics it covers, separated by commas. Those topics are what LearnIO tags questions with.
      </>
    ),
  },
  {
    title: "Upload a past exam",
    body: (
      <>
        Open Upload and drop in the exam as a PDF. LearnIO reads the text, splits it into individual questions, keeps
        their layout and code blocks, and tags each one with the course&apos;s topics. Uploading the same exam twice
        doesn&apos;t create duplicates.
      </>
    ),
  },
  {
    title: "Browse the questions",
    body: (
      <>
        Questions shows every question in the bank, laid out the way the exam printed it, with its marks and topics.
        Pick a topic on the left to see only those questions.
      </>
    ),
  },
  {
    title: "Generate a practice exam",
    body: (
      <>
        Open Practice exam, pick the topics you want to drill (or none for all of them) and how many questions, then
        generate. Questions are drawn at random from the bank. Print it or save it as a PDF to work through on paper.
      </>
    ),
  },
];

const HEADINGS = ["1.", "2)", "Question 3", "4 (10 marks)"];

export default function Guide() {
  return (
    <>
      <header className="topbar">
        <div className="topbar-inner">
          <Link href="/" className="wordmark">
            LearnIO
          </Link>
          <span className="course-nav" />
          <Link href="/" className="btn-quiet btn-small">
            Back to courses
          </Link>
        </div>
      </header>

      <main className="main guide">
        <h1 className="guide-title">How it works</h1>
        <p className="guide-lede">
          LearnIO turns a course&apos;s past exams into a question bank you can browse by topic, then draws practice
          exams from it.
        </p>

        <ol className="guide-steps">
          {STEPS.map((step, i) => (
            <li key={step.title} className="guide-step">
              <span className="guide-step-number" aria-hidden="true">
                {i + 1}
              </span>
              <div>
                <h2 className="guide-step-title">{step.title}</h2>
                <p>{step.body}</p>
              </div>
            </li>
          ))}
        </ol>

        <section className="guide-section" aria-labelledby="pdf-h">
          <h2 id="pdf-h" className="guide-heading">
            What your PDF needs
          </h2>
          <ul className="guide-list">
            <li>
              Real text, not a scan. LearnIO reads the text inside the PDF and can&apos;t read photos or scanned pages.
              If you can select words in your PDF viewer, it will work.
            </li>
            <li>
              Each question starts on its own line with a heading like one of these:
              <span className="guide-headings">
                {HEADINGS.map((h) => (
                  <code key={h}>{h}</code>
                ))}
              </span>
            </li>
            <li>20 MB or smaller.</li>
          </ul>
          <p className="muted">
            If an upload finds no questions, nothing is added and the error says so. Check the headings first.
          </p>
        </section>

        <section className="guide-section" aria-labelledby="slow-h">
          <h2 id="slow-h" className="guide-heading">
            Why the first load can be slow
          </h2>
          <p>
            The server runs on a free tier that sleeps after 15 minutes without visitors. The first visit after that
            wakes it up, which takes 30 to 50 seconds. Everything is quick after that.
          </p>
        </section>

        <Link href="/" className="btn">
          Go to the question bank
        </Link>
      </main>
    </>
  );
}
