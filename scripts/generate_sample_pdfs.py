"""Generate PDF versions of the sample resumes for demo/testing purposes.

Run from the repository root:
    .venv/Scripts/python scripts/generate_sample_pdfs.py
"""

from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parent.parent
RESUME_DIR = ROOT / "sample-data" / "resumes"

FONT = "Helvetica"
SIZE = 10.5
LINE_HEIGHT = 14


def write_pdf(txt_path: Path, pdf_path: Path) -> None:
    lines: list[tuple[str, bool]] = []
    for raw in txt_path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            lines.append(("", False))
            continue
        is_heading = stripped.isupper() and len(stripped) < 40
        # Wrap long lines to page width.
        words = stripped.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) > 92:
                lines.append((current, is_heading))
                current = word
            else:
                current = candidate
        lines.append((current, is_heading))

    c = canvas.Canvas(str(pdf_path), pagesize=LETTER)
    width, height = LETTER

    def draw_page(page_lines):
        y = height - 60
        c.setFont(FONT + "-Bold", 13)
        for i, (text, heading) in enumerate(page_lines):
            if y < 60:
                return page_lines[i:]
            c.setFont(FONT + ("-Bold" if heading else ""), SIZE)
            c.drawString(64, y, text)
            y -= LINE_HEIGHT
        return []

    remaining = lines
    while remaining:
        remaining = draw_page(remaining)
        if remaining:
            c.showPage()
    c.save()
    print(f"Wrote {pdf_path.name}")


def main() -> None:
    for txt_path in sorted(RESUME_DIR.glob("*.txt")):
        pdf_path = txt_path.with_suffix(".pdf")
        if not pdf_path.exists():
            write_pdf(txt_path, pdf_path)


if __name__ == "__main__":
    main()
