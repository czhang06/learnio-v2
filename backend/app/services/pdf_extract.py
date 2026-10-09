import fitz  # PyMuPDF


def extract_text(data: bytes) -> str:
    """Return the plain text of a PDF given its raw bytes."""
    with fitz.open(stream=data, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)
