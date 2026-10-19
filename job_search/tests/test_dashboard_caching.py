"""Caching + search-performance tests for the dashboard data layer."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import pandas as pd

from job_search.job_db import connect, init_schema, upsert_job, upsert_score, utc_now_iso
from job_search.web import services

JOBS = [
    ("job-python", "Python Developer", "Acme", "python azure backend services"),
    ("job-data", "Data Scientist", "Beta", "machine learning python notebooks"),
    ("job-front", "Frontend Engineer", "Gamma", "react typescript user interfaces"),
]


class TestDashboardCaching(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "jobs.sqlite"
        conn = connect(self.db_path)
        init_schema(conn)
        now = utc_now_iso()
        for uuid, title, employer, description in JOBS:
            upsert_job(
                conn,
                {
                    "uuid": uuid,
                    "source": "nav_arbeidsplassen",
                    "title": title,
                    "employer_name": employer,
                    "status": "ACTIVE",
                    "fetched_at": now,
                    "expires": "2099-01-01",
                    "description_text": description,
                },
            )
            upsert_score(
                conn,
                {
                    "uuid": uuid,
                    "source": "nav_arbeidsplassen",
                    "track": "industry",
                    "score_base": 40.0,
                    "boost_rogaland": 0.0,
                    "boost_tek": 0.0,
                    "score_total": 40.0,
                    "scored_at": now,
                    "matched_keywords": "python",
                    "matched_skills": "ml",
                },
            )
        conn.commit()
        conn.close()
        services.clear_explorer_jobs_cache()
        services._CACHE_EXEC_COUNTS.clear()
        self.path_s = str(self.db_path)

    def tearDown(self) -> None:
        services.clear_explorer_jobs_cache()
        services._CACHE_EXEC_COUNTS.clear()
        self.tmp.cleanup()

    def _explorer(self, text_query: str, order_by: str = "score") -> pd.DataFrame:
        df, _ = services.load_explorer_jobs_df(
            path_s=self.path_s,
            track="industry",
            min_score=0.0,
            rogaland_only=False,
            hide_applied=True,
            hide_expired=True,
            query_include_terms=(),
            exclude_tuple=(),
            source_filter="all",
            hide_phd_student=True,
            apply_academic_filter=False,
            dedupe_cross_source=True,
            use_tech_allowlist=True,
            include_tuple=(),
            urgency_days=7,
            text_query=text_query,
            order_by=order_by,
        )
        return df

    def test_base_frame_reused_across_keystrokes(self) -> None:
        for query in ("p", "py", "python"):
            self._explorer(query)
        self.assertEqual(services._cache_exec_count("explorer_base_miss"), 1)
        self.assertEqual(services._cache_exec_count("explorer_base_hit"), 2)
        self.assertEqual(services._cache_exec_count("load_jobs_df"), 1)

    def test_repeated_query_hits_search_cache(self) -> None:
        self._explorer("python")
        self._explorer("python")
        self.assertEqual(services._cache_exec_count("explorer_search_miss"), 1)
        self.assertEqual(services._cache_exec_count("explorer_search_hit"), 1)

    def test_empty_query_returns_cached_base(self) -> None:
        first = self._explorer("")
        second = self._explorer("")
        self.assertEqual(len(first), len(second))
        self.assertEqual(services._cache_exec_count("explorer_base_miss"), 1)
        self.assertEqual(services._cache_exec_count("explorer_base_hit"), 1)

    def test_clear_cache_invalidates_base(self) -> None:
        self._explorer("python")
        services.clear_explorer_jobs_cache()
        self._explorer("python")
        self.assertEqual(services._cache_exec_count("explorer_base_miss"), 2)

    def test_order_by_is_part_of_base_key(self) -> None:
        self._explorer("", order_by="score")
        self._explorer("", order_by="published")
        self.assertEqual(services._cache_exec_count("explorer_base_miss"), 2)

    def test_vectorized_text_search_matches_expected_rows(self) -> None:
        self.assertEqual(
            sorted(self._explorer("python")["uuid"]),
            ["job-data", "job-python"],
        )
        self.assertEqual(sorted(self._explorer("azure")["uuid"]), ["job-python"])
        self.assertEqual(sorted(self._explorer("react")["uuid"]), ["job-front"])
        self.assertEqual(sorted(self._explorer("python notebooks")["uuid"]), ["job-data"])

    def test_text_search_is_case_insensitive_and_handles_nan(self) -> None:
        df = pd.DataFrame(
            [
                {"uuid": "a", "title": "Python Dev", "description_text": None, "employer_name": "Acme"},
                {"uuid": "b", "title": "Java Dev", "description_text": float("nan"), "employer_name": None},
            ]
        )
        out = services.apply_text_search_filter(df, "PYTHON")
        self.assertEqual(list(out["uuid"]), ["a"])

    def test_thin_finn_card_hidden_but_real_description_kept(self) -> None:
        conn = connect(self.db_path)
        now = utc_now_iso()
        for uuid, description in (
            ("thin-finn", "Short marketing teaser."),
            ("full-finn", "y" * 400),
        ):
            upsert_job(
                conn,
                {
                    "uuid": uuid,
                    "source": "finn_no",
                    "title": "Data Engineer",
                    "employer_name": "Northline",
                    "status": "ACTIVE",
                    "fetched_at": now,
                    "expires": "2099-01-01",
                    "description_text": description,
                },
            )
            upsert_score(
                conn,
                {
                    "uuid": uuid,
                    "source": "finn_no",
                    "track": "industry",
                    "score_base": 40.0,
                    "boost_rogaland": 0.0,
                    "boost_tek": 0.0,
                    "score_total": 40.0,
                    "scored_at": now,
                    "matched_keywords": "python",
                    "matched_skills": "ml",
                },
            )
        conn.commit()
        conn.close()
        services.clear_explorer_jobs_cache()
        uuids = set(self._explorer("")["uuid"])
        self.assertNotIn("thin-finn", uuids)
        self.assertIn("full-finn", uuids)

    def test_overview_frames_cached(self) -> None:
        kwargs = dict(
            path_s=self.path_s,
            track="industry",
            source_filter="all",
            hide_phd_student=True,
            dedupe_cross_source=True,
            use_tech_allowlist=True,
            include_tuple=(),
            exclude_tuple=(),
            apply_academic_filter=False,
            query_include_terms=(),
            urgency_days=7,
            min_score=0.0,
        )
        services.load_overview_frames(**kwargs)
        services.load_overview_frames(**kwargs)
        self.assertEqual(services._cache_exec_count("overview_frames_miss"), 1)
        self.assertEqual(services._cache_exec_count("overview_frames_hit"), 1)

    def test_overview_metrics_cached(self) -> None:
        services.load_overview_metrics(self.path_s, "industry", 7)
        services.load_overview_metrics(self.path_s, "academic", 7)
        self.assertEqual(services._cache_exec_count("overview_metrics_miss"), 1)
        self.assertEqual(services._cache_exec_count("overview_metrics_hit"), 1)


if __name__ == "__main__":
    unittest.main()
