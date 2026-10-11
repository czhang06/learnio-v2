import type { Block } from "@/lib/questionFormat";

function Blocks({ blocks }: { blocks: Block[] }) {
  return (
    <>
      {blocks.map((block, i) => {
        if (block.kind === "para") {
          return (
            <p key={i} className="q-para">
              {block.text}
            </p>
          );
        }
        if (block.kind === "display") {
          return (
            <pre key={i} className="q-display" tabIndex={0}>
              {block.text}
            </pre>
          );
        }
        return (
          <ol key={i} className="q-parts">
            {block.items.map((part, j) => (
              <li key={j} className="q-part">
                <span className="q-part-label">{part.label}</span>
                <div className="q-part-body">
                  <Blocks blocks={part.blocks} />
                </div>
              </li>
            ))}
          </ol>
        );
      })}
    </>
  );
}

/** A question body laid out the way the exam printed it. */
export default function QuestionText({ blocks }: { blocks: Block[] }) {
  return (
    <div className="q-text">
      <Blocks blocks={blocks} />
    </div>
  );
}
