from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from shared.cv_loader import JobProfile
from job_search.ingest_common import mark_stale_jobs_inactive
from job_search.ingest_nav_jobs import effective_if_modified_since
from job_search.job_db import connect, init_schema, set_state, upsert_job
from job_search.job_filters import term_matches
from job_search.location_preferences import match_preferred_location
from job_search.nav_feed_client import http_get_json
from job_search.score_jobs import score_profile


def make_profile(
    *,
    locations: list[str] | None = None,
    keywords: list[str] | None = None,
    skills: list[str] | None = None,
    track: str = "industry",
) -> JobProfile:
    return JobProfile(
        track=track,
        source_path=Path("shared/cv/industry.demo.md"),
        front_matter={
            "locations_preferred": locations or [],
            "keywords": keywords or [],
            "skills": skills or [],
        },
        body_markdown="",
    )


class _FakeResponse:
    def __init__(self, body: dict[str, object]) -> None:
        self.status = 200
        self.headers = {"ETag": "abc"}
        self._body = json.dumps(body).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class JobSearchPipelineTests(unittest.TestCase):
    def test_term_matches_reduces_substring_false_positives(self) -> None:
        self.assertTrue(term_matches("we use sql and python", "sql"))
        self.assertFalse(term_matches("experience with sequel server", "sql"))
        self.assertTrue(term_matches("building services in go", "go"))
        self.assertFalse(term_matches("google cloud platform", "go"))
        self.assertFalse(term_matches("bli en del av lederteamet i cut'n go haugesund", "go"))
        self.assertTrue(term_matches("data engineer for pipelines", "data"))
        self.assertFalse(term_matches("administer the production database", "data"))
        self.assertFalse(term_matches("experience with databases and sql", "data"))

    def test_match_preferred_location_ignores_broad_country_only_values(self) -> None:
        broad_only = match_preferred_location(["Norway"], municipal="Oslo", county="Oslo")
        self.assertFalse(broad_only.matched)

        rogaland = match_preferred_location(["Norway", "Rogaland"], municipal="Stavanger", county="Rogaland")
        self.assertTrue(rogaland.matched)
        self.assertEqual(rogaland.label, "Rogaland")

    def test_score_profile_counts_strong_matches_without_location_boost(self) -> None:
        profile = make_profile(locations=["Oslo"], keywords=["sql", "machine learning"], skills=["python", "go"])
        row = {
            "title": "Data Engineer",
            "jobtitle": "",
            "description_text": "Working with Python and machine learning data pipelines, not sequel tooling.",
            "employer_name": "Example AS",
            "municipal": "Oslo",
            "county": "Oslo",
            "feed_municipal": "OSLO",
            "in_rogaland": 0,
        }
        result = score_profile(profile, row, tek_by_norm={})
        self.assertEqual(result["boost_rogaland"], 0.0)
        self.assertEqual(result["matched_skills"], "python")
        self.assertEqual(result["matched_keywords"], "machine learning")
        # Distinct strong hits: machine learning + python → score_base 2
        self.assertEqual(result["score_base"], 2.0)
        self.assertEqual(result["score_total"], 2.0)

    def test_score_profile_salon_location_only_is_zero(self) -> None:
        profile = make_profile(locations=["Rogaland"], keywords=["python", "go"], skills=["machine learning"])
        row = {
            "title": "Bli en del av lederteamet i Cut'n Go Haugesund",
            "jobtitle": "",
            "description_text": "Frisørsalong søker daglig leder.",
            "employer_name": "Cut'n Go Haugesund As",
            "municipal": "HAUGESUND",
            "county": "ROGALAND",
            "feed_municipal": "HAUGESUND",
            "in_rogaland": 1,
        }
        result = score_profile(profile, row, tek_by_norm={})
        self.assertEqual(result["score_base"], 0.0)
        self.assertEqual(result["score_total"], 0.0)
        self.assertEqual(result["boost_rogaland"], 0.0)
        self.assertIsNone(result["matched_keywords"])
        self.assertIsNone(result["matched_skills"])

    def test_tek_boost_is_relevance_gated_and_small(self) -> None:
        profile = make_profile(keywords=["machine learning"], skills=["python"])
        tek = {"norconsult": "Norconsult Norge AS"}

        relevant = {
            "title": "Data Engineer",
            "jobtitle": "",
            "description_text": "Python pipelines for machine learning.",
            "employer_name": "Norconsult Norge AS",
            "municipal": "Trondheim",
            "county": "Trøndelag",
            "in_rogaland": 0,
        }
        result = score_profile(profile, relevant, tek_by_norm=tek)
        self.assertEqual(result["score_base"], 2.0)
        self.assertEqual(result["boost_tek"], 1.0)
        self.assertEqual(result["score_total"], 3.0)
        self.assertEqual(result["tek_match_name"], "Norconsult Norge AS")

        irrelevant = {
            "title": "Byggeleder",
            "jobtitle": "",
            "description_text": "Prosjektledelse for byggeplass.",
            "employer_name": "Norconsult Norge AS",
            "municipal": "Trondheim",
            "county": "Trøndelag",
            "in_rogaland": 0,
        }
        result = score_profile(profile, irrelevant, tek_by_norm=tek)
        self.assertEqual(result["score_base"], 0.0)
        self.assertEqual(result["boost_tek"], 0.0)
        self.assertEqual(result["score_total"], 0.0)
        self.assertIsNone(result["tek_match_name"])

    def test_academic_postdoc_and_ai_boosts(self) -> None:
        academic = make_profile(
            track="academic",
            keywords=["machine learning"],
            skills=["python"],
        )

        def row(title: str, description: str, employer: str = "University of Oslo") -> dict:
            return {
                "title": title,
                "jobtitle": "",
                "description_text": description,
                "employer_name": employer,
                "municipal": "Oslo",
                "county": "Oslo",
                "in_rogaland": 0,
            }

        postdoc_ai = score_profile(
            academic,
            row("Postdoctoral Research Fellow in Machine Learning", "Python research."),
            tek_by_norm={},
        )
        self.assertEqual(postdoc_ai["score_base"], 2.0)
        # university +2, academic title +1, postdoc +3, AI title +2
        self.assertEqual(postdoc_ai["score_total"], 10.0)

        postdoc_desc_ai = score_profile(
            academic,
            row("Postdoctoral Research Fellow in Fisheries", "Python and machine learning tools."),
            tek_by_norm={},
        )
        self.assertEqual(postdoc_desc_ai["score_total"], 9.5)

        researcher_ai = score_profile(
            academic,
            row("Researcher in Artificial Intelligence", "Python research."),
            tek_by_norm={},
        )
        # base 1 (python) + university 2 + academic title 1 + AI title 2
        self.assertEqual(researcher_ai["score_base"], 1.0)
        self.assertEqual(researcher_ai["score_total"], 6.0)

        industry = make_profile(keywords=["machine learning"], skills=["python"])
        industry_score = score_profile(
            industry,
            row("Postdoctoral Research Fellow in Machine Learning", "Python research."),
            tek_by_norm={},
        )
        self.assertEqual(industry_score["score_total"], 2.0)

    def test_mark_stale_jobs_inactive_marks_missing_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "jobs.sqlite"
            conn = connect(db_path)
            init_schema(conn)
            base = {
                "source": "nav_arbeidsplassen",
                "status": "ACTIVE",
                "title": "Title",
                "fetched_at": "2026-07-08T10:00:00+00:00",
            }
            upsert_job(conn, {"uuid": "seen", **base})
            upsert_job(conn, {"uuid": "stale", **base})
            updated = mark_stale_jobs_inactive(
                conn,
                source="nav_arbeidsplassen",
                fetched_at="2026-07-09T10:00:00+00:00",
                seen_uuids={"seen"},
            )
            rows = {
                row["uuid"]: row["status"]
                for row in conn.execute("SELECT uuid, status FROM job_postings").fetchall()
            }
            self.assertEqual(updated, 1)
            self.assertEqual(rows["seen"], "ACTIVE")
            self.assertEqual(rows["stale"], "INACTIVE")

    def test_effective_if_modified_since_uses_saved_state_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            conn = connect(Path(tmp_dir) / "jobs.sqlite")
            init_schema(conn)
            recent_success = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)
            set_state(conn, "nav_feed:last_success_at", recent_success.isoformat())

            class Args:
                since_days = 3
                use_feed_state = True
                state_overlap_hours = 6

            ims = effective_if_modified_since(conn, Args())
            self.assertEqual(ims, recent_success - timedelta(hours=6))

    def test_http_get_json_retries_transient_errors(self) -> None:
        calls = {"n": 0}

        def fake_urlopen(req, context=None, timeout=None):  # noqa: ANN001
            calls["n"] += 1
            if calls["n"] == 1:
                raise urllib.error.URLError("temporary outage")
            return _FakeResponse({"items": [1]})

        with patch("job_search.http_utils.urllib.request.urlopen", side_effect=fake_urlopen):
            data, headers = http_get_json("https://example.com", max_attempts=2, retry_backoff_s=0)
        self.assertEqual(data, {"items": [1]})
        self.assertEqual(headers["etag"], "abc")
        self.assertEqual(calls["n"], 2)


if __name__ == "__main__":
    unittest.main()
