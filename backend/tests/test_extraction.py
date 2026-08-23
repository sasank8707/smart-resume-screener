"""Tests for PDF/TXT text extraction."""

import io

import pytest
from pypdf import PdfWriter

from app.services.extraction import (
    ExtractionError,
    detect_file_type,
    extract_resume_text,
    extract_text_from_pdf,
)


def _build_pdf(text: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class TestFileTypeDetection:
    def test_detects_pdf(self):
        assert detect_file_type("resume.PDF") == "pdf"

    def test_detects_txt_variants(self):
        for name in ("resume.txt", "resume.text", "resume.md"):
            assert detect_file_type(name) == "txt"

    def test_rejects_docx(self):
        with pytest.raises(ExtractionError):
            detect_file_type("resume.docx")

    def test_rejects_no_extension(self):
        with pytest.raises(ExtractionError):
            detect_file_type("resume")


class TestTxtExtraction:
    def test_valid_txt(self):
        text = "Jane Doe\n" + "Experienced Python developer with Docker skills. " * 2
        raw, file_type = extract_resume_text(text.encode(), "resume.txt")
        assert file_type == "txt"
        assert "Jane Doe" in raw

    def test_latin1_fallback(self):
        text = "Café experience résumé " * 5
        raw, _ = extract_resume_text(text.encode("latin-1"), "r.txt")
        assert "Café" in raw

    def test_empty_file_raises(self):
        with pytest.raises(ValueError):
            extract_resume_text(b"", "empty.txt")

    def test_tiny_file_raises(self):
        with pytest.raises(ExtractionError):
            extract_resume_text(b"hi", "tiny.txt")


class TestPdfExtraction:
    def test_invalid_pdf_raises(self):
        with pytest.raises(ExtractionError):
            extract_resume_text(b"%PDF-1.4 this is not really a pdf", "fake.pdf")

    def test_scanned_pdf_without_text_raises(self):
        data = _build_pdf("")
        with pytest.raises(ExtractionError):
            extract_resume_text(data, "scanned.pdf")

    def test_oversized_file_raises(self):
        big = b"x" * (20 * 1024 * 1024 + 1)
        with pytest.raises(ValueError):
            extract_resume_text(big, "big.txt")
