/**
 * Turn a stored question body into blocks the UI can lay out like the exam did.
 *
 * The API keeps the PDF's line breaks and indentation. From those this module
 * recovers three things: prose paragraphs (wrapped lines are joined back up),
 * display blocks (indented material such as SQL, kept line for line), and
 * lettered sub-parts (a, b, c / i, ii, iii).
 */

export interface Marks {
  value: number;
  unit: "point" | "mark";
}

export interface Part {
  label: string;
  blocks: Block[];
}

export type Block =
  | { kind: "para"; text: string }
  | { kind: "display"; text: string }
  | { kind: "parts"; items: Part[] };

export interface ParsedQuestion {
  marks: Marks | null;
  blocks: Block[];
}

interface Line {
  indent: number;
  text: string; // "" for a blank line; otherwise the line without its indentation
}

type Sequence = "lower" | "upper" | "roman";

interface Label {
  raw: string; // the label and the spaces after it, as written
  name: string;
  style: string; // "a)" and "(a)" and "a." never mix within one list
}

// "(9 points)", "[5 marks]", "(10 pts):" at the very start of a question.
const MARKS = /^\s*[(\[]\s*(\d+(?:\.\d+)?)\s*(marks?|points?|pts?)\s*[)\]]\s*[:.]?\s*/i;
const LABEL = /^(\(?)([A-Za-z]|[ivx]{2,4})([).])(?:\s+|$)/;
const ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii"];
// A line indented at least this far past its surroundings is display material.
const DISPLAY_INDENT = 3;
// A line at least this fraction of the longest line was wrapped by the page
// edge, so the next line continues its sentence.
const WRAPPED_FRACTION = 0.6;

function toLines(text: string): Line[] {
  return text
    .replace(/\r/g, "")
    .split("\n")
    .map((raw) => {
      const line = raw.replace(/\t/g, "    ").trimEnd();
      const body = line.trimStart();
      return { indent: line.length - body.length, text: body };
    });
}

function matchLabel(line: Line): Label | null {
  const m = LABEL.exec(line.text);
  if (!m) return null;
  if (m[1] === "(" && m[3] !== ")") return null;
  return { raw: m[0], name: m[2], style: m[1] + m[3] };
}

function sequenceStart(name: string): Sequence | null {
  if (name === "a") return "lower";
  if (name === "A") return "upper";
  if (name === "i") return "roman";
  return null;
}

function nameAt(seq: Sequence, n: number): string | undefined {
  if (seq === "roman") return ROMAN[n];
  if (n > 25) return undefined;
  return String.fromCharCode((seq === "lower" ? 97 : 65) + n);
}

function minIndent(lines: Line[]): number {
  let min = Infinity;
  for (const l of lines) if (l.text && l.indent < min) min = l.indent;
  return min === Infinity ? 0 : min;
}

/** Prose and display blocks only; `base` is the indentation prose sits at. */
function flow(lines: Line[], base: number, wrapAt: number): Block[] {
  const out: Block[] = [];
  let para: string[] = [];
  let prevLength = 0;
  let display: Line[] = [];

  const flushPara = () => {
    if (para.length > 0) out.push({ kind: "para", text: para.join("") });
    para = [];
  };
  const flushDisplay = () => {
    if (display.length > 0) {
      const left = minIndent(display);
      out.push({ kind: "display", text: display.map((l) => " ".repeat(l.indent - left) + l.text).join("\n") });
    }
    display = [];
  };

  for (const line of lines) {
    if (!line.text) {
      flushPara();
      flushDisplay();
    } else if (line.indent >= base + DISPLAY_INDENT) {
      flushPara();
      display.push(line);
    } else {
      flushDisplay();
      if (para.length > 0) para.push(prevLength >= wrapAt ? " " : "\n");
      para.push(line.text.replace(/\s+/g, " "));
      prevLength = line.indent + line.text.length;
    }
  }
  flushPara();
  flushDisplay();
  return out;
}

/** Indexes of the lines that open each item of the list starting at `start`. */
function listItems(lines: Line[], start: number, base: number): { starts: number[]; end: number } | null {
  const first = matchLabel(lines[start]);
  const seq = first && sequenceStart(first.name);
  if (!first || !seq) return null;
  const at = lines[start].indent;
  const starts = [start];
  let end = lines.length;
  for (let j = start + 1; j < lines.length; j++) {
    const line = lines[j];
    if (!line.text) continue;
    // Text back out at the margin after an indented list closes the list.
    if (at > base && line.indent <= at - DISPLAY_INDENT) {
      end = j;
      break;
    }
    const label = matchLabel(line);
    if (
      label &&
      label.style === first.style &&
      label.name === nameAt(seq, starts.length) &&
      Math.abs(line.indent - at) <= 1
    ) {
      starts.push(j);
    }
  }
  // A lone "a)" is more likely a sentence fragment than a one-item list.
  return starts.length >= 2 ? { starts, end } : null;
}

function parseBlocks(lines: Line[], wrapAt: number, baseOverride?: number): Block[] {
  let from = 0;
  let to = lines.length;
  while (from < to && !lines[from].text) from++;
  while (to > from && !lines[to - 1].text) to--;
  lines = lines.slice(from, to);
  if (lines.length === 0) return [];
  const base = baseOverride ?? minIndent(lines);

  for (let i = 0; i < lines.length; i++) {
    if (!lines[i].text) continue;
    const list = listItems(lines, i, base);
    if (!list) continue;
    const items: Part[] = list.starts.map((s, k) => {
      const head = lines[s];
      const label = matchLabel(head) as Label;
      const rest = lines.slice(s + 1, k + 1 < list.starts.length ? list.starts[k + 1] : list.end);
      const content = head.text.slice(label.raw.length);
      // Prose in a part sits where the text after its label starts, or
      // further left when continuation lines wrap back toward the label.
      const column = head.indent + label.raw.length;
      const partBase = rest.some((l) => l.text) ? Math.min(column, minIndent(rest)) : column;
      const body = content ? [{ indent: partBase, text: content }, ...rest] : rest;
      return { label: label.raw.trim(), blocks: parseBlocks(body, wrapAt, partBase) };
    });
    return [
      ...flow(lines.slice(0, i), base, wrapAt),
      { kind: "parts", items },
      ...parseBlocks(lines.slice(list.end), wrapAt),
    ];
  }
  return flow(lines, base, wrapAt);
}

export function parseQuestion(text: string): ParsedQuestion {
  let marks: Marks | null = null;
  const m = MARKS.exec(text);
  if (m) {
    marks = { value: Number(m[1]), unit: m[2].toLowerCase().startsWith("m") ? "mark" : "point" };
    text = text.slice(m[0].length);
  }
  const lines = toLines(text);
  let longest = 0;
  for (const l of lines) longest = Math.max(longest, l.indent + l.text.length);
  return { marks, blocks: parseBlocks(lines, longest * WRAPPED_FRACTION) };
}

export function formatMarks(marks: Marks): string {
  return marks.value + " " + marks.unit + (marks.value === 1 ? "" : "s");
}
