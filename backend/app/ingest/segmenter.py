"""Split exam text into individual questions and tag topics.

Segmentation is rule-based so it is fast, free, and testable without network
access. Question bodies keep the line breaks and indentation of the source so
the frontend can lay out sub-parts and code the way the exam did; deduplication
hashes a whitespace-normalized copy, so layout never creates duplicates. Topic tagging uses Gemini when a key is configured and falls back to
keyword matching against the course's known topics otherwise.
"""

import hashlib
import json
import re

from ..config import settings

# A new question begins at the start of a line (or of a page: PDF extractors
# emit "\f" at page breaks, which "^" alone does not treat as a line start) with:
#   - a keyword heading: "Question 1", "Problem 2:" (separator optional)
#   - a bare number with a separator: "1." / "2)" / "3:"
#   - a bare number followed by a mark count: "4 (10 marks)"
# A plain number needs the separator or the mark count so that "2004" in a
# header line does not start a question. Any of these may be preceded by the
# question's marks, as many exams print them in the margin: "(10 points) 1.",
# "[9] 1.", "15 marks 1.". Those are captured so they stay with the question.
_LEADING_MARKS = (
    r"(?P<marks>"
    r"[\(\[][ \t]*\d{1,3}(?:[ \t]*(?:marks?|points?|pts?))?[ \t]*[\)\]]"
    r"|\d{1,3}[ \t]*(?:marks?|points?|pts?)\b"
    r")[ \t]*"
)
_QUESTION_START = re.compile(
    r"(?:^|\f)[ \t\f]*(?:" + _LEADING_MARKS + r")?(?:"
    r"(?:question|problem)\s*\d{1,3}\b[ \t]*[\.\):]?"
    r"|\d{1,3}[\.\):](?=\s)"
    r"|\d{1,3}(?=[ \t]*[\(\[][ \t]*\d+[ \t]*(?:marks?|points?|pts?)\b)"
    r")\s*",
    re.IGNORECASE | re.MULTILINE,
)
_MARK_COUNT = re.compile(r"(\d{1,3})[ \t]*(marks?|points?|pts?)", re.IGNORECASE)
# Running headers and footers repeated on every page: "MATH 302 Page 3 of 12".
_PAGE_LINE = re.compile(r"^[^\n]*\bpage\s+\d+\s+of\s+\d+\b[^\n]*$", re.IGNORECASE | re.MULTILINE)
# Numbered items that are exam instructions rather than questions: the
# university's rules for formal examinations on the cover page, and the usual
# "answer all questions" notes. Only unmarked items are dropped, so a real
# question that happens to use one of these phrases survives if it has marks.
# Words are joined by \s+ because PDFs often space them with non-breaking spaces.
_INSTRUCTION = re.compile(
    r"\bcandidates?\b.{0,200}?\b(?:invigilators?|examination\s+room|examiners?|AMS\s+card|"
    r"library\s+card|examination\s+(?:material|papers?|rules)|dishonest)"
    r"|\bsmoking\s+is\s+not\s+permitted\b"
    r"|\banswer\s+all\s+(?:the\s+)?questions\b"
    r"|\bwrite\s+your\s+(?:name|student)"
    r"|\byou\s+have\s+\d+\s+minutes\b"
    r"|\bpoint\s+form\b",
    re.IGNORECASE | re.DOTALL,
)
_MARKS_ANYWHERE = re.compile(r"[\(\[\{]\s*\d{1,3}\s*(?:marks?|points?|pts?)\b", re.IGNORECASE)
# Sign-offs after the last question: "--- The End ---", "Good luck!".
_SIGN_OFF = re.compile(
    r"(?:\s*(?:-{2,}\s*(?:the\s+)?end(?:\s+of\s+\w+)?\s*-{2,}|good\s+luck[!.]*))+\s*$",
    re.IGNORECASE,
)
_MIN_CHARS = 25


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_layout(text: str, hang: int | None = None) -> str:
    """Tidy a question body while keeping its line breaks and indentation.

    The first line follows the question number, so it carries no indentation
    of its own. `hang` is the column that first line started at; the remaining
    lines are shifted left by at most that much, which undoes a hanging indent
    under the number without flattening code or sub-parts that sit deeper.
    With no `hang`, they shift until the shallowest one sits at the margin.
    """
    lines = [line.rstrip() for line in text.replace("\f", "\n").expandtabs(4).split("\n")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines:
        return ""
    rest = lines[1:]
    shift = min((len(line) - len(line.lstrip()) for line in rest if line), default=0)
    if hang is not None:
        shift = min(shift, hang)
    out = [lines[0].lstrip()]
    for line in rest:
        line = line[shift:]
        if line or out[-1]:  # collapse runs of blank lines (answer space) to one
            out.append(line)
    return "\n".join(out)


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).lower().encode()).hexdigest()


def _marks_prefix(marks: str | None) -> str:
    """Restate margin marks the way a question body conventionally opens."""
    if not marks:
        return ""
    count = _MARK_COUNT.search(marks)
    if count:
        return "(" + count.group(1) + " " + count.group(2).lower() + ") "
    return marks.strip() + " "  # "[9]": a count with no unit, kept as printed


def split_questions(raw: str) -> list[str]:
    raw = _PAGE_LINE.sub("", raw)
    matches = list(_QUESTION_START.finditer(raw))
    if not matches:
        return []
    questions: list[str] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        hang = m.end() - (max(raw.rfind("\n", 0, m.end()), raw.rfind("\f", 0, m.end())) + 1)
        body = clean_layout(_SIGN_OFF.sub("", raw[m.end():end]), hang)
        marks = _marks_prefix(m.group("marks"))
        if not marks and _INSTRUCTION.search(body) and not _MARKS_ANYWHERE.search(body):
            continue
        body = marks + body
        if len(normalize(body)) >= _MIN_CHARS:
            questions.append(body)
    return questions


def tag_topics_by_keyword(question: str, topics: list[str]) -> list[str]:
    lowered = question.lower()
    return [t for t in topics if t.lower() in lowered]


def tag_topics_with_llm(questions: list[str], topics: list[str]) -> list[list[str]]:
    """Ask Gemini to label each question with zero or more known topics."""
    if not settings.gemini_api_key or not topics:
        return [tag_topics_by_keyword(q, topics) for q in questions]

    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = (
        "Label each exam question with zero or more topics chosen ONLY from this list: "
        f"{json.dumps(topics)}. Return JSON: a list with one list of topics per question, "
        "in the same order.\n\nQuestions:\n"
        + "\n".join(f"{i + 1}. {normalize(q)[:400]}" for i, q in enumerate(questions))
    )
    response = client.models.generate_content(model=settings.gemini_model, contents=prompt)
    try:
        labels = json.loads(re.sub(r"^```(?:json)?|```$", "", response.text.strip(), flags=re.MULTILINE))
        allowed = set(topics)
        return [[t for t in row if t in allowed] for row in labels][: len(questions)]
    except (ValueError, TypeError):
        return [tag_topics_by_keyword(q, topics) for q in questions]
