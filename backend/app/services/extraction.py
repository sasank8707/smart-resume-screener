"""Text extraction for PDF and plain-text resumes.

Extraction failures are surfaced as `ExtractionError` so the API can return
meaningful errors to the user instead of failing silently.
"""

import re
from pathlib import Path

MAX_FILE_BYTES = 20 * 1024 * 1024  # hard safety ceiling (config enforces a lower limit)

PDF_SUFFIXES = {".pdf"}
TXT_SUFFIXES = {".txt", ".text", ".md"}


class ExtractionError(ValueError):
    """Raised when a resume file cannot be read or contains no usable text."""


def detect_file_type(filename: str) -> str:
    """Return 'pdf' or 'txt' based on the file extension."""
    suffix = Path(filename).suffix.lower()
    if suffix in PDF_SUFFIXES:
        return "pdf"
    if suffix in TXT_SUFFIXES:
        return "txt"
    raise ExtractionError(
        f"Unsupported file type '{suffix or filename}'. Allowed: PDF, TXT."
    )


def _normalise_whitespace(text: str) -> str:
    """Collapse noisy whitespace produced by PDF extraction."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(data: bytes) -> str:
    """Extract text from PDF bytes using pypdf.

    Raises:
        ExtractionError: if the file is not a valid PDF or yields no text
            (e.g. scanned images without an OCR layer).
    """
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as exc:  # pragma: no cover - dependency always installed
        raise ExtractionError("PDF support is not installed on the server.") from exc

    try:
        reader = PdfReader(__import__("io").BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception as exc:  # noqa: BLE001 - password protected files
                raise ExtractionError(
                    "The PDF is password protected and cannot be read."
                ) from exc
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise ExtractionError(f"The PDF file appears to be corrupted: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ExtractionError(f"Failed to read the PDF file: {exc}") from exc

    text = _normalise_whitespace("\n".join(pages))
    if len(text) < 40:
        raise ExtractionError(
            "No readable text found in the PDF. It may be a scanned image; "
            "please upload a text-based PDF or a TXT file."
        )
    return text


def extract_text_from_txt(data: bytes) -> str:
    """Decode UTF-8 (or latin-1 fallback) plain-text resumes."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except Exception as exc:  # noqa: BLE001
            raise ExtractionError("The TXT file could not be decoded.") from exc
    text = _normalise_whitespace(text)
    if len(text) < 40:
        raise ExtractionError("The TXT file contains too little text to be a resume.")
    return text


def extract_resume_text(data: bytes, filename: str) -> tuple[str, str]:
    """Extract text from an uploaded resume.

    Returns:
        (raw_text, file_type)

    Raises:
        ValueError: if the file is empty/too large.
        ExtractionError: for unsupported types or unreadable content.
    """
    if not data:
        raise ValueError("The uploaded file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("The uploaded file exceeds the maximum size of 20 MB.")

    file_type = detect_file_type(filename)
    if file_type == "pdf":
        return extract_text_from_pdf(data), "pdf"
    return extract_text_from_txt(data), "txt"
