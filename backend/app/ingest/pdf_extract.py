import re
from dataclasses import dataclass

import fitz  # PyMuPDF

# One column of indentation, in PDF points. Roughly the width of an average
# character at 12pt, so indentation in the output reads like the page did.
_COLUMN_PT = 6.0
# Lines whose tops are within this many points share a row.
_ROW_TOLERANCE_PT = 3.0
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


@dataclass(frozen=True)
class Line:
    """Where one line of extracted text sits in the PDF, in points."""

    page: int
    top: float
    bottom: float
    left: float
    right: float
    text: str


@dataclass(frozen=True)
class Layout:
    text: str
    lines: list[Line]  # one per line of `text`, in the same order


def _page_rows(page) -> list[tuple[float, str, tuple[float, float, float, float]]]:
    """Return (x, text, bbox) for each visual row of a page, top to bottom.

    `x` is where the first ink of the row starts. Indentation that the PDF
    encodes as leading spaces is converted to points and added to `x`, so
    callers see one kind of indentation whichever way the author produced it.
    """
    chunks: list[tuple[float, float, str, float, tuple]] = []  # (y, x, text, space width, bbox)
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = line["spans"]
            text = _CONTROL_CHARS.sub("", "".join(s["text"] for s in spans)).replace("\t", "    ")
            size = spans[0]["size"] if spans else 12.0
            chunks.append((line["bbox"][1], line["bbox"][0], text, size * 0.25, tuple(line["bbox"])))
    chunks.sort(key=lambda c: (c[0], c[1]))

    rows: list[list[tuple[float, float, str, float]]] = []
    for chunk in chunks:
        if rows and abs(chunk[0] - rows[-1][0][0]) <= _ROW_TOLERANCE_PT:
            rows[-1].append(chunk)
        else:
            rows.append([chunk])

    out: list[tuple[float, str, tuple[float, float, float, float]]] = []
    for row in rows:
        inked = sorted((c for c in row if c[2].strip()), key=lambda c: c[1])
        if not inked:
            out.append((0.0, "", row[0][4]))
            continue
        _, x, first, space, _ = inked[0]
        leading = len(first) - len(first.lstrip(" "))
        text = " ".join(c[2].strip() for c in inked)
        box = (
            min(c[4][0] for c in inked),
            min(c[4][1] for c in inked),
            max(c[4][2] for c in inked),
            max(c[4][3] for c in inked),
        )
        out.append((x + leading * space, text, box))
    return out


def extract_layout(data: bytes) -> Layout:
    """Return a PDF's text, keeping its line layout, and where each line is.

    Each visual row becomes one line, indented with spaces in proportion to
    how far it sits from the document's left margin.
    """
    with fitz.open(stream=data, filetype="pdf") as doc:
        pages = [_page_rows(page) for page in doc]
    margin = min((x for rows in pages for x, text, _ in rows if text), default=0.0)
    texts: list[str] = []
    lines: list[Line] = []
    for number, rows in enumerate(pages):
        for x, text, (left, top, right, bottom) in rows:
            indent = max(0, round((x - margin) / _COLUMN_PT)) if text else 0
            texts.append(" " * indent + text)
            lines.append(Line(number, top, bottom, left, right, text))
    return Layout("\n".join(texts), lines)


def extract_text(data: bytes) -> str:
    """Return the text of a PDF given its raw bytes, keeping its line layout."""
    return extract_layout(data).text
