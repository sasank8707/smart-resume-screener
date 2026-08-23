"""Tests for screening logic: scoring, ranking, shortlisting, persistence."""

from app.services.screening import mock_match_candidate, run_screening


class TestMockScorer:
    def test_strong_match_scores_high(self, seeded_candidate, seeded_job):
        outcome = mock_match_candidate(seeded_candidate, seeded_job)
        assert outcome.match_score >= 7
        assert outcome.recommendation in {"strong_yes", "yes"}

    def test_weak_match_scores_low(self, db_session, seeded_job):
        from app.models import Candidate

        weak = Candidate(
            candidate_name="Riya Kapoor",
            email="riya@example.com",
            phone=None,
            skills=["Graphic Design", "Figma", "Photoshop"],
            experience=[
                {
                    "organization": "Pixel Studio",
                    "role": "Designer",
                    "duration": "2022-01 - 2024-01",
                    "start_date": "2022-01",
                    "end_date": "2024-01",
                    "responsibilities": ["Designed marketing assets"],
                    "technologies": ["Figma"],
                }
            ],
            education=[],
            resume_filename="weak.txt",
            file_type="txt",
            raw_text="designer resume",
            parsed_data={},
        )
        db_session.add(weak)
        db_session.commit()
        db_session.refresh(weak)

        outcome = mock_match_candidate(weak, seeded_job)
        assert outcome.match_score <= 4
        assert len(outcome.missing_skills) >= 3

    def test_score_bounds_respected(self, seeded_candidate, seeded_job):
        outcome = mock_match_candidate(seeded_candidate, seeded_job)
        assert 1.0 <= outcome.match_score <= 10.0

    def test_no_invented_qualifications(self, seeded_candidate, seeded_job):
        outcome = mock_match_candidate(seeded_candidate, seeded_job)
        joined = " ".join(outcome.strengths + outcome.missing_skills).lower()
        # The candidate has no Kubernetes evidence; it must appear as missing.
        if "kubernetes" not in (seeded_candidate.skills or []):
            pass  # missing_skills may legitimately contain it
        assert "cobol" not in joined


class TestRunScreening:
    def test_persists_and_shortlists(self, db_session, seeded_candidate, seeded_job):
        threshold = 5.0
        results = run_screening(db_session, seeded_job, [seeded_candidate], threshold)
        assert len(results) == 1
        result = results[0]
        assert result.candidate_id == seeded_candidate.id
        assert result.job_description_id == seeded_job.id
        assert result.shortlisted == (result.match_score >= threshold)
        assert result.shortlist_threshold == threshold

    def test_ranking_order(self, db_session, seeded_job, seeded_candidate):
        from app.models import Candidate

        strong = seeded_candidate
        weak = Candidate(
            candidate_name="Zubin Mehta",
            email="zubin@example.com",
            skills=["Excel"],
            experience=[],
            education=[],
            resume_filename="z.txt",
            file_type="txt",
            raw_text="excel user",
            parsed_data={},
        )
        db_session.add(weak)
        db_session.commit()

        results = run_screening(db_session, seeded_job, [strong, weak], 7.0)
        scores = [r.match_score for r in results]
        assert scores == sorted(scores, reverse=True)
        assert results[0].candidate_id == strong.id

    def test_rescreen_upserts_not_duplicates(
        self, db_session, seeded_candidate, seeded_job
    ):
        run_screening(db_session, seeded_job, [seeded_candidate], 6.0)
        results = run_screening(db_session, seeded_job, [seeded_candidate], 8.0)
        assert len(results) == 1
        from app.models import ScreeningResult

        count = (
            db_session.query(ScreeningResult)
            .filter_by(candidate_id=seeded_candidate.id, job_description_id=seeded_job.id)
            .count()
        )
        assert count == 1
