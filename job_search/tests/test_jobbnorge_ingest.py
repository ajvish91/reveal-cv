from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.ingest_jobbnorge_jobs import card_passes_filters, run_ingest
from job_search.job_db import connect, init_schema


class JobbnorgeIngestTests(unittest.TestCase):
    def test_card_passes_nynorsk_forskar_ui_b(self) -> None:
        """Job 307720: Nynorsk title must pass default --require-tech and academic display."""
        card = {
            "id": 307720,
            "title": "Forskar (mellombels) i KI-forskingsformidling ved AI LEARN",
            "employer": "Universitetet i Bergen",
            "summary": (
                "UiB skal vere blant Europas fremste universitet, internasjonalt "
                "kjent for høg kvalitet i forsking og utdanning."
            ),
            "location": "Bergen",
            "deadline": "23.09.2026",
        }
        from job_search.job_filters import merge_include_terms

        require = merge_include_terms(True, "", [])
        ok, _hits, _in_r, _loc, _label = card_passes_filters(
            card,
            keywords=["machine learning", "research"],
            keyword_filter=True,
            rogaland_only=False,
            require_terms=require,
            exclude_terms=(),
            preferred_locations=["Rogaland"],
            search_track_terms=(),
        )
        self.assertTrue(ok, "default ICT allowlist should accept Nynorsk forskar")

        from job_search.job_filters import matches_academic_role_display

        self.assertTrue(
            matches_academic_role_display(
                card["title"],
                None,
                card["summary"],
                card["employer"],
            )
        )

    def test_card_passes_academic_postdoc(self) -> None:
        card = {
            "id": 307898,
            "title": "Postdoctoral Fellow in Machine Learning and Digital Health Services",
            "employer": "NTNU - Norwegian University of Science and Technology",
            "summary": "We offer a 3-year postdoctoral position in machine learning.",
            "location": "Trondheim",
            "deadline": "05.10.2026",
        }
        ok, hits, in_r, _loc, _label = card_passes_filters(
            card,
            keywords=["machine learning", "research", "postdoc"],
            keyword_filter=True,
            rogaland_only=False,
            require_terms=("postdoc", "machine learning"),
            exclude_terms=(),
            preferred_locations=["Rogaland"],
            search_track_terms=("postdoctoral", "machine learning"),
        )
        self.assertTrue(ok)
        self.assertTrue(hits)
        self.assertFalse(in_r)

    @patch("job_search.ingest_jobbnorge_jobs.JobbnorgeClient")
    @patch("job_search.ingest_jobbnorge_jobs.load_default_profiles")
    @patch("job_search.ingest_jobbnorge_jobs.collect_ingest_keywords")
    def test_run_ingest_stores_matching_row(
        self,
        mock_keywords,
        mock_profiles,
        mock_client_cls,
    ) -> None:
        mock_profiles.return_value = []
        mock_keywords.return_value = ["machine learning", "research", "postdoc"]
        mock_client_cls.return_value.fetch_job_catalog.return_value = [
            {
                "id": 307898,
                "title": "Postdoctoral Fellow in Machine Learning",
                "employer": "NTNU",
                "summary": "Postdoctoral research in machine learning for health.",
                "location": "Trondheim",
                "deadline": "05.10.2026",
            },
            {
                "id": 999,
                "title": "Nattevakt",
                "employer": "Kommune",
                "summary": "Turnus nattevakt helse.",
                "location": "Oslo",
                "deadline": "01.01.2027",
            },
        ]
        mock_client_cls.return_value.fetch_pdf_text.return_value = "Deadline: 10/5/2026\nML postdoc."

        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "jobs.sqlite"
            import argparse

            args = argparse.Namespace(
                db=str(db),
                keyword=[],
                keyword_source="keywords-and-skills",
                keyword_filter=True,
                application_boosts=None,
                rogaland_only=False,
                require_tech=True,
                require_tech_no_defaults=False,
                include_tech=[],
                exclude_noise=True,
                exclude_noise_no_defaults=False,
                exclude=[],
                search_track="both",
                max_details=5,
                sleep_s=0,
                search_only=False,
                mark_stale=True,
                use_ingest_state=False,
            )
            code = run_ingest(args)
            self.assertEqual(code, 0)
            conn = connect(db)
            init_schema(conn)
            rows = conn.execute(
                "SELECT uuid, source, title FROM job_postings WHERE source = 'jobbnorge'"
            ).fetchall()
            conn.close()
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["uuid"], "307898")


if __name__ == "__main__":
    unittest.main()
