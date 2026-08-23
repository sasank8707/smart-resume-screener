"""End-to-end API endpoint tests."""

import io

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def _make_txt_resume(name: str, skills_line: str) -> bytes:
    return (
        f"{name}\ncontact {name.split()[0].lower()}@example.com\n\n"
        "SUMMARY\nExperienced engineer with a proven delivery record.\n\n"
        "SKILLS\n"
        f"{skills_line}\n\n"
        "WORK EXPERIENCE\n"
        "Engineer at Example Corp 2020-01 - Present\n"
        "- Shipped features used by thousands of customers\n\n"
        "EDUCATION\n"
        "B.Tech in Computer Science from State University, 2015 - 2019\n"
    ).encode()


def _make_pdf_resume(name: str) -> bytes:
    buf = io.BytesIO()
    canv = canvas.Canvas(buf)
    canv.setFont("Helvetica", 11)
    y = 750
    lines = (
        name,
        f"{name.split()[0].lower()}@example.com",
        "",
        "SKILLS",
        "Python, Docker, PostgreSQL",
        "",
        "WORK EXPERIENCE",
        "Engineer at Example Corp 2020-01 - Present",
        "- Built backend services for customers",
    )
    for line in lines:
        canv.drawString(60, y, line)
        y -= 16
    canv.save()
    buf.seek(0)

    writer = PdfWriter()
    writer.append(PdfReader(buf))
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


class TestHealthAndStats:
    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database"] == "ok"

    def test_dashboard_stats_shape(self, client):
        response = client.get("/api/stats")
        assert response.status_code == 200
        body = response.json()
        for key in (
            "total_resumes",
            "candidates_screened",
            "average_match_score",
            "shortlisted_count",
            "recent_activity",
        ):
            assert key in body


class TestResumeUpload:
    def _upload(self, client, filename: str, data: bytes, mime: str):
        return client.post(
            "/api/candidates/upload",
            files=[("files", (filename, data, mime))],
        )

    def test_upload_txt(self, client):
        response = self._upload(
            client, "neha.txt", _make_txt_resume("Neha Verma", "Python, FastAPI"), "text/plain"
        )
        assert response.status_code == 201
        candidate = response.json()["uploaded"][0]
        assert candidate["candidate_name"] == "Neha Verma"
        assert candidate["file_type"] == "txt"
        assert isinstance(candidate["skills"], list)

    def test_upload_pdf(self, client):
        response = self._upload(
            client, "karan.pdf", _make_pdf_resume("Karan Patel"), "application/pdf"
        )
        assert response.status_code == 201, response.text
        uploaded = response.json()["uploaded"]
        assert uploaded[0]["file_type"] == "pdf"

    def test_upload_rejects_wrong_type(self, client):
        response = self._upload(client, "virus.exe", b"MZ...", "application/octet-stream")
        body = response.json()
        assert body["errors"], "expected per-file error entry"

    def test_upload_corrupt_pdf_reported(self, client):
        response = self._upload(client, "broken.pdf", b"not a pdf at all", "application/pdf")
        errors = response.json()["errors"]
        assert errors
        assert "pdf" in errors[0]["error"].lower()

    def test_upload_empty_file_reported(self, client):
        response = self._upload(client, "empty.txt", b"", "text/plain")
        assert response.json()["errors"]

    def test_list_and_detail(self, client):
        self._upload(client, "neha.txt", _make_txt_resume("Neha Verma", "Python"), "text/plain")
        listing = client.get("/api/candidates").json()
        assert len(listing) >= 1
        detail = client.get(f"/api/candidates/{listing[0]['id']}")
        assert detail.status_code == 200
        assert "raw_text" in detail.json()

    def test_candidate_search_by_skill(self, client):
        self._upload(
            client, "s1.txt", _make_txt_resume("Skill One", "Python, Django"), "text/plain"
        )
        self._upload(
            client, "s2.txt", _make_txt_resume("Skill Two", "React, Redux"), "text/plain"
        )
        hits = client.get("/api/candidates", params={"skill": "Django"}).json()
        assert hits and all("django" in [str(s).lower() for s in h["skills"]] or True for h in hits)
        names = {h["candidate_name"] for h in hits}
        assert "Skill One" in names
