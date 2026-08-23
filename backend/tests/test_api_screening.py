"""API tests for job descriptions and the screening workflow."""

from tests.test_api import _make_txt_resume


def _create_job(client) -> dict:
    payload = {
        "title": "Backend Engineer",
        "description_text": (
            "Build robust services for our platform.\n\nRequirements:\n"
            "- 3+ years of experience\n- Python and REST APIs\n"
            "- SQL databases like PostgreSQL\n\nNice-to-have:\n- Redis"
        ),
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 201
    return response.json()


class TestJobEndpoints:
    def test_create_and_list(self, client):
        job = _create_job(client)
        listing = client.get("/api/jobs").json()
        assert any(j["id"] == job["id"] for j in listing)
        required = {s.lower() for s in job["requirements"]["required_skills"]}
        assert "python" in required

    def test_create_validation(self, client):
        response = client.post(
            "/api/jobs", json={"title": "X", "description_text": "short"}
        )
        assert response.status_code == 422

    def test_get_missing_job_404(self, client):
        assert client.get("/api/jobs/99999").status_code == 404

    def test_update_reextracts_requirements(self, client):
        job = _create_job(client)
        updated = client.patch(
            f"/api/jobs/{job['id']}",
            json={
                "description_text": (
                    "Frontend Engineer role.\nRequirements:\n- React and "
                    "TypeScript expertise\n- 4+ years of experience"
                )
            },
        ).json()
        required = {s.lower() for s in updated["requirements"]["required_skills"]}
        assert "react" in required and "python" not in required

    def test_delete_job(self, client):
        job = _create_job(client)
        assert client.delete(f"/api/jobs/{job['id']}").status_code == 204
        assert client.get(f"/api/jobs/{job['id']}").status_code == 404


class TestScreeningEndpoints:
    def _seed_candidate(self, client, name: str, skills: str) -> int:
        data = _make_txt_resume(name, skills)
        response = client.post(
            "/api/candidates/upload",
            files=[("files", ("resume.txt", data, "text/plain"))],
        )
        return response.json()["uploaded"][0]["id"]

    def test_run_screening_ranks_and_shortlists(self, client):
        job_id = _create_job(client)["id"]
        strong_id = self._seed_candidate(client, "Isha Rao", "Python, REST APIs, PostgreSQL")
        weak_id = self._seed_candidate(client, "Manav Singh", "Figma, Photoshop")

        response = client.post(
            "/api/screening/run",
            json={"job_description_id": job_id, "candidate_ids": [strong_id, weak_id]},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["threshold"] == 7.0  # default threshold
        results = body["results"]
        assert len(results) == 2
        scores = [r["match_score"] for r in results]
        assert scores == sorted(scores, reverse=True)
        assert results[0]["rank"] == 1
        top = results[0]
        assert top["candidate_name"] == "Isha Rao"
        for field in (
            "explanation",
            "strengths",
            "missing_skills",
            "experience_alignment",
            "education_alignment",
            "recommendation",
        ):
            assert field in top
        assert results[0]["shortlisted"] is (scores[0] >= 7.0)

    def test_screening_unknown_candidates_400(self, client):
        job_id = _create_job(client)["id"]
        response = client.post(
            "/api/screening/run",
            json={"job_description_id": job_id, "candidate_ids": [987654]},
        )
        assert response.status_code == 400

    def test_screening_unknown_job_404(self, client):
        response = client.post(
            "/api/screening/run",
            json={"job_description_id": 99999, "candidate_ids": [1]},
        )
        assert response.status_code == 404

    def test_results_filters_and_sorting(self, client):
        job_id = _create_job(client)["id"]
        strong_id = self._seed_candidate(client, "Filter A", "Python, PostgreSQL, REST APIs")
        self._seed_candidate(client, "Filter B", "Excel, PowerPoint")
        client.post(
            "/api/screening/run",
            json={"job_description_id": job_id, "candidate_ids": [strong_id]},
        )

        all_results = client.get("/api/screening/results").json()
        assert all_results

        filtered = client.get(
            "/api/screening/results", params={"min_score": 5.0}
        ).json()
        assert all(r["match_score"] >= 5.0 for r in filtered)

        shortlist_only = client.get(
            "/api/screening/results", params={"shortlisted_only": True}
        ).json()
        assert all(r["shortlisted"] for r in shortlist_only)

        by_name = client.get(
            "/api/screening/results", params={"sort_by": "name", "order": "asc"}
        ).json()
        names = [r["candidate_name"] or "" for r in by_name]
        assert names == sorted(names)

        by_date = client.get(
            "/api/screening/results", params={"sort_by": "date"}
        ).json()
        dates = [r["created_at"] for r in by_date]
        assert dates == sorted(dates, reverse=True)

        name_search = client.get(
            "/api/screening/results", params={"q": "Filter A"}
        ).json()
        assert all("Filter A" in (r["candidate_name"] or "") for r in name_search)

    def test_custom_threshold_respected(self, client):
        job_id = _create_job(client)["id"]
        candidate_id = self._seed_candidate(client, "Thresh Old", "Python")
        body = client.post(
            "/api/screening/run",
            json={
                "job_description_id": job_id,
                "candidate_ids": [candidate_id],
                "threshold": 9.5,
            },
        ).json()
        assert body["threshold"] == 9.5
        assert body["results"][0]["shortlisted"] is False
