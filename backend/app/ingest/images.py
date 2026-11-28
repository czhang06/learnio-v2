"""Render each question as an image cropped from its original PDF.

Extracted text loses what makes many exam questions readable: matrices and
fractions come out as scrambled rows of numbers, and figures disappear. The
question's region of the page keeps both. For each question this finds the
parts of its pages that carry ink (text, drawings, embedded images), drops
running headers, footers and page numbers, collapses the blank space left for
answers, and stacks what remains, across page breaks, into one PNG.
"""

import io
import re
from collections import Counter
from dataclasses import dataclass

import fitz  # PyMuPDF
from PIL import Image, ImageChops

from .pdf_extract import Line

_DPI = 216  # 3x the PDF's 72 points per inch: sharp when shown enlarged on high-density screens
# How large to show a question, in CSS px per PDF point. Every question is
# shown at the same scale, so exams with small and large type keep their
# relative sizes instead of each being stretched to the column width.
DISPLAY_SCALE = 1.35
_PAD = 6.0  # points kept around the ink
_GAP = 10.0  # points between bands that were apart on the page
_MIN_GAP = 24.0  # blank space taller than this is collapsed
_EDGE = 0.12  # top and bottom share of a page where running headers and footers live
_MAX_HEIGHT = 2400.0  # points; a very long question is cut off at this height


@dataclass
class _Band:
    page: int
    top: float
    bottom: float


def _running_lines(lines: list[Line], heights: list[float]) -> set[tuple[int, float]]:
    """(page, top) of header and footer lines: near the top or bottom edge of
    their page and repeated, digits aside, on other pages; or page numbers."""
    def key(line: Line) -> str:
        return re.sub(r"\d+", "#", line.text.strip().lower())

    def at_edge(line: Line) -> bool:
        h = heights[line.page]
        return line.top < h * _EDGE or line.bottom > h * (1 - _EDGE)

    pages_with = Counter()
    for k, pages in _group(lines, key, at_edge).items():
        pages_with[k] = len(pages)
    running = set()
    for line in lines:
        if not at_edge(line) or not line.text.strip():
            continue
        if line.text.strip().isdigit() or pages_with[key(line)] >= 2:
            running.add((line.page, line.top))
    return running


def _group(lines, key, keep) -> dict[str, set[int]]:
    out: dict[str, set[int]] = {}
    for line in lines:
        if line.text.strip() and keep(line):
            out.setdefault(key(line), set()).add(line.page)
    return out


def _page_ink(page) -> list[tuple[float, float]]:
    """Vertical extents of drawings and images, minus page-sized frames."""
    area = page.rect
    spans = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.width > area.width * 0.9 and r.height > area.height * 0.8:
            continue
        spans.append((r.y0, r.y1))
    for info in page.get_image_info():
        x0, y0, x1, y1 = info["bbox"]
        spans.append((y0, y1))
    return spans


def _bands(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[list[float]] = []
    for top, bottom in sorted(spans):
        if merged and top - merged[-1][1] < _MIN_GAP:
            merged[-1][1] = max(merged[-1][1], bottom)
        else:
            merged.append([top, bottom])
    return [(t, b) for t, b in merged]


def render_questions(
    data: bytes, lines: list[Line], ranges: list[tuple[int, int]]
) -> list[bytes | None]:
    """A PNG for each (first line, end line) range of `lines`, or None where
    nothing could be cropped.

    On each page a question covers, its crop runs from its first line (or,
    on later pages, the bottom of the running header) to the next question's
    first line (or the top of the running footer).
    """
    with fitz.open(stream=data, filetype="pdf") as doc:
        heights = [p.rect.height for p in doc]
        running = _running_lines(lines, heights)
        is_content = lambda ln: bool(ln.text.strip()) and (ln.page, ln.top) not in running  # noqa: E731
        content = [ln for ln in lines if is_content(ln)]
        if not content:
            return [None] * len(ranges)
        left = max(0.0, min(ln.left for ln in content) - _PAD)
        right = max(ln.right for ln in content) + _PAD

        header_bottom = [0.0] * len(heights)
        footer_top = list(heights)
        for ln in lines:
            if (ln.page, ln.top) in running:
                if ln.top < heights[ln.page] / 2:
                    header_bottom[ln.page] = max(header_bottom[ln.page], ln.bottom)
                else:
                    footer_top[ln.page] = min(footer_top[ln.page], ln.top)

        ink: dict[int, list[tuple[float, float]]] = {}
        starts = [next((ln for ln in lines[a:b] if is_content(ln)), None) for a, b in ranges]
        images: list[bytes | None] = []
        for i, (first, end) in enumerate(ranges):
            own = [ln for ln in lines[first:end] if is_content(ln)]
            if not own:
                images.append(None)
                continue
            following = next((s for s in starts[i + 1 :] if s is not None), None)
            bands: list[_Band] = []
            for page_no in sorted({ln.page for ln in own}):
                on_page = [ln for ln in own if ln.page == page_no]
                top = on_page[0].top if page_no == own[0].page else header_bottom[page_no]
                limit = footer_top[page_no]
                if following is not None and following.page == page_no:
                    limit = following.top
                if page_no not in ink:
                    ink[page_no] = _page_ink(doc[page_no])
                spans = [(ln.top, ln.bottom) for ln in on_page]
                spans += [(t, b) for t, b in ink[page_no] if b > top and t < limit]
                for t, b in _bands(spans):
                    t, b = max(t, top) - _PAD, min(b, limit) + _PAD
                    if b > t:
                        bands.append(_Band(page_no, t, b))
            images.append(_compose(doc, bands, left, right))
        return images


def _compose(doc, bands: list[_Band], left: float, right: float) -> bytes | None:
    if not bands:
        return None
    width = right - left
    height, kept = 0.0, []
    for band in bands:
        h = band.bottom - band.top
        if height + h > _MAX_HEIGHT:
            h = _MAX_HEIGHT - height
            if h <= _PAD * 2:
                break
            band = _Band(band.page, band.top, band.top + h)
        kept.append(band)
        height += h + _GAP
    height -= _GAP
    with fitz.open() as out:
        page = out.new_page(width=width, height=height)
        y = 0.0
        for band in kept:
            h = band.bottom - band.top
            clip = fitz.Rect(left, band.top, right, band.bottom)
            page.show_pdf_page(fitz.Rect(0, y, width, y + h), doc, band.page, clip=clip)
            y += h + _GAP
        return page.get_pixmap(dpi=_DPI).tobytes("png")


@dataclass
class WebImage:
    data: bytes
    width: int  # pixels
    height: int
    media_type: str = "image/webp"
    extension: str = "webp"


def to_web(png: bytes) -> WebImage:
    """Re-encode a rendered question for the browser: lossless WebP, so text
    stays exactly as sharp, and greyscale unless the question has colour (a
    coloured figure). About a third of the PNG's size on exam pages."""
    with Image.open(io.BytesIO(png)) as source:
        rgb = source.convert("RGB")
    r, g, b = rgb.split()
    colourful = max(ImageChops.difference(r, g).getextrema()[1], ImageChops.difference(g, b).getextrema()[1]) > 48
    image = rgb if colourful else rgb.convert("L")
    out = io.BytesIO()
    image.save(out, "WEBP", lossless=True, method=4)
    return WebImage(out.getvalue(), image.width, image.height)


def display_size(width: int, height: int) -> tuple[int, int]:
    """The CSS size to show a rendered question at, from its size in pixels:
    its size in PDF points, scaled by DISPLAY_SCALE."""
    factor = DISPLAY_SCALE * 72 / _DPI
    return round(width * factor), round(height * factor)
