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
from dataclasses import dataclass

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
# A candidate heading at the start of a line (or page). Which candidates are
# real question boundaries is decided afterwards, from how they are numbered.
#   - "Quiz 2, Question 1" / "Quiz 5, Problem 3"           (two-level keyword)
#   - "Question 1", "Problem 2:", "Problem 3-1."           (keyword)
#   - "1 Team Problem:"                                     (number, then keyword)
#   - "1." / "2)" / "3:"                                    (number with separator)
#   - "4 (10 marks)"                                        (number, then mark count)
#   - "G1† ."                                               (dagger-marked extra problem)
#   - "2 Double Sums"                                       (number and a short title line)
# Any of these may follow a bullet ("• Question 1.").
_HEADING = re.compile(
    r"(?:^|\f)(?P<indent>[ \t\f]*)(?:[•●▪◦][ \t]*)?(?:" + _LEADING_MARKS + r")?(?:"
    r"quiz[ \t]*(?P<quiz>\d{1,2})[ \t]*,[ \t]*(?:question|problem)[ \t]*(?P<sub>\d{1,3})\b[ \t]*[\.\):,]?"
    r"|(?:question|problem)\s*(?P<kw>\d{1,3})(?:-(?P<kwsub>\d{1,3}))?\b[ \t]*[\.\):]?"
    r"|(?P<named>\d{1,3})[ \t]+(?:[a-z]+[ \t]+)?(?:question|problem)\b[ \t]*:?"
    r"|(?P<dot>\d{1,3})[\.\):](?=\s)"
    r"|(?P<pts>\d{1,3})(?=[ \t]*[\(\[][ \t]*\d+[ \t]*(?:marks?|points?|pts?)\b)"
    r"|(?P<extra>[A-Z]\d{1,2})[ \t]*†[ \t]*[\.\):]"
    # A title: capitalized, short, alone on its line, not ending in a number
    # (which would make it a table row such as "1 True or False 40 10").
    r"|(?P<title>\d{1,2})[ \t]+(?=[A-Z][^\n]{2,58}$)(?![^\n]*\d[ \t]*$)"
    r")",
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
_TEAR_OFF = re.compile(r"\btear[\s-]*off\b", re.IGNORECASE)
_NAME_ONLY = re.compile(r"\bwrite\s+your\s+name\b", re.IGNORECASE)
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


@dataclass
class _Heading:
    match: re.Match
    family: str  # "keyword" | "dot" | "pts" | "title" | "extra"
    number: tuple[int, ...]
    indent: int
    body_start: int = 0  # after the heading and the whitespace following it
    body: str = ""  # text up to the next candidate, used for filtering


def _candidates(raw: str) -> list[_Heading]:
    found = []
    for m in _HEADING.finditer(raw):
        if m["quiz"]:
            family, number = "keyword", (int(m["quiz"]), int(m["sub"]))
        elif m["kw"]:
            family, number = "keyword", (int(m["kw"]), int(m["kwsub"])) if m["kwsub"] else (int(m["kw"]),)
        elif m["named"]:
            family, number = "keyword", (int(m["named"]),)
        elif m["extra"]:
            family, number = "extra", (int(m["extra"][1:]),)
        elif m["dot"]:
            family, number = "dot", (int(m["dot"]),)
        elif m["title"]:
            family, number = "title", (int(m["title"]),)
        else:
            family, number = "pts", (int(m["pts"]),)
        indent = len(m["indent"].replace("\f", "").expandtabs(4))
        # The whitespace after a heading is skipped here, not matched by the
        # pattern, so a heading on the very next line is still found.
        body_start = re.compile(r"\s*").match(raw, m.end()).end()
        found.append(_Heading(m, family, number, indent, body_start))
    for i, h in enumerate(found):
        end = found[i + 1].match.start() if i + 1 < len(found) else len(raw)
        h.body = raw[h.body_start : max(end, h.body_start)]
    return found


def _follows(prev: tuple[int, ...], nxt: tuple[int, ...]) -> bool:
    """Whether `nxt` is the heading number that comes right after `prev`."""
    if len(prev) != len(nxt):
        return False
    if prev[:-1] == nxt[:-1] and nxt[-1] == prev[-1] + 1:
        return True
    return len(nxt) == 2 and nxt[0] == prev[0] + 1 and nxt[1] <= 1  # "Quiz 2, Question 1" after Quiz 1


def _longest_chain(heads: list[_Heading]) -> list[_Heading]:
    """Longest run of headings numbered 1, 2, 3... in order, skipping strays."""
    best: list[int] = []
    back: list[int] = []
    for i, h in enumerate(heads):
        best.append(1)
        back.append(-1)
        for j in range(i):
            if best[j] + 1 > best[i] and _follows(heads[j].number, h.number):
                best[i], back[i] = best[j] + 1, j
    if not heads:
        return []
    i = max(range(len(heads)), key=lambda k: (best[k], -k))
    chain = []
    while i >= 0:
        chain.append(heads[i])
        i = back[i]
    return chain[::-1]


def _groups(heads: list[_Heading]) -> list[list[_Heading]]:
    """Headings of one style. Keyword headings form one group per numbering
    depth; numbered ones are also split by indentation, so a list nested
    inside a question does not join the questions' own numbering."""
    groups: dict[tuple, list[_Heading]] = {}
    for h in heads:
        if h.family == "keyword":
            key: tuple = (h.family, len(h.number))
        else:
            column = next((c for (f, c) in groups if f == h.family and abs(c - h.indent) <= 2), h.indent)
            key = (h.family, column)
        groups.setdefault(key, []).append(h)
    return list(groups.values())


def _is_instruction(h: _Heading) -> bool:
    body = h.body
    if _NAME_ONLY.search(body) and len(normalize(body)) < 200:
        return True  # "Write your name on every page", even when it carries a point
    return not h.match["marks"] and bool(_INSTRUCTION.search(body)) and not _MARKS_ANYWHERE.search(body)


def _opening(text: str) -> str:
    return normalize(text).lower()[:80]


def split_questions(raw: str) -> list[str]:
    """Split exam text into question bodies.

    Every line that could start a question is a candidate. Candidates are
    grouped by style, and the group whose numbers run 1, 2, 3... furthest is
    taken as the questions, preferring explicit "Problem"/"Question" headings.
    Numbered lists inside a question restart at 1, so they cannot outrun the
    questions' own numbering. A later run that repeats earlier questions (an
    answer booklet copy) or carries almost no text (tear-off sheets) is cut.
    """
    raw = _PAGE_LINE.sub("", raw)
    heads = [h for h in _candidates(raw) if not _is_instruction(h)]
    # Problems marked with a dagger ("G1†.", graduate-only problems in some
    # problem sets) are questions in their own right, numbered apart from the rest.
    extras = [h for h in heads if h.family == "extra"]
    heads = [h for h in heads if h.family != "extra"]
    if not heads:
        heads, extras = extras, []
    if not heads:
        return []
    groups = _groups(heads)
    chains = {id(g): _longest_chain(g) for g in groups}
    group = max(
        groups,
        key=lambda g: (
            g[0].family == "keyword" and len(chains[id(g)]) >= 2,
            len(chains[id(g)]),
            g[0].family == "keyword",
            -min(h.indent for h in g),
            -g[0].match.start(),
        ),
    )
    chain = chains[id(group)]

    # Runs of the same style outside the main chain: further sections are
    # kept, repeated or near-empty ones end the question before them.
    kept, cuts = list(chain), []
    openings = {_opening(h.body) for h in chain}
    rest = [h for h in group if h.match.start() < chain[0].match.start() or h.match.start() > chain[-1].match.start()]
    run: list[_Heading] = []
    for h in [*rest, None]:
        if h is not None and run and _follows(run[-1].number, h.number) and (
            (run[-1].match.start() < chain[0].match.start()) == (h.match.start() < chain[0].match.start())
        ):
            run.append(h)
            continue
        if len(run) >= 2:
            repeated = any(_opening(r.body) in openings for r in run)
            thin = sum(len(normalize(r.body)) for r in run) / len(run) < 40 or any(
                _TEAR_OFF.search(r.body) for r in run
            )
            if repeated or thin:
                cuts.append(run[0].match.start())
            else:
                kept.extend(run)
                openings |= {_opening(r.body) for r in run}
        run = [h] if h is not None else []
    kept.extend(h for h in extras if h.match.start() > chain[0].match.start())
    kept.sort(key=lambda h: h.match.start())
    stops = sorted([h.match.start() for h in kept] + cuts)

    questions: list[str] = []
    for h in kept:
        start = h.match.start()
        end = next((s for s in stops if s > start), len(raw))
        m, begin = h.match, h.body_start
        hang = begin - (max(raw.rfind("\n", 0, begin), raw.rfind("\f", 0, begin)) + 1)
        body = clean_layout(_SIGN_OFF.sub("", raw[begin:end]), hang)
        body = re.sub(r"^[,;:]\s*", "", body)  # "Quiz 1, Question 1, Rules": drop the joining comma
        body = _marks_prefix(m["marks"]) + body
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
