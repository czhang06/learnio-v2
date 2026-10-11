"""Split exam text into individual questions and tag topics.

Segmentation is rule-based so it is fast, free, and testable without network
access. Topic tagging uses Gemini when a key is configured and falls back to
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
# header line does not start a question.
_QUESTION_START = re.compile(
    r"(?:^|\f)[ \t\f]*(?:"
    r"(?:question|problem)\s*\d{1,3}\b[ \t]*[\.\):]?"
    r"|\d{1,3}[\.\):](?=\s)"
    r"|\d{1,3}(?=[ \t]*[\(\[][ \t]*\d+[ \t]*(?:marks?|points?|pts?)\b)"
    r")\s*",
    re.IGNORECASE | re.MULTILINE,
)
# Sign-offs after the last question: "--- The End ---", "Good luck!".
_SIGN_OFF = re.compile(
    r"(?:\s*(?:-{2,}\s*(?:the\s+)?end(?:\s+of\s+\w+)?\s*-{2,}|good\s+luck[!.]*))+\s*$",
    re.IGNORECASE,
)
_MIN_CHARS = 25


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def text_hash(text: str) -> str:
    return hashlib.sha256(normalize(text).lower().encode()).hexdigest()


def split_questions(raw: str) -> list[str]:
    matches = list(_QUESTION_START.finditer(raw))
    if not matches:
        return []
    questions: list[str] = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw)
        body = normalize(_SIGN_OFF.sub("", raw[m.end():end]))
        if len(body) >= _MIN_CHARS:
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
        + "\n".join(f"{i + 1}. {q[:400]}" for i, q in enumerate(questions))
    )
    response = client.models.generate_content(model=settings.gemini_model, contents=prompt)
    try:
        labels = json.loads(re.sub(r"^```(?:json)?|```$", "", response.text.strip(), flags=re.MULTILINE))
        allowed = set(topics)
        return [[t for t in row if t in allowed] for row in labels][: len(questions)]
    except (ValueError, TypeError):
        return [tag_topics_by_keyword(q, topics) for q in questions]
