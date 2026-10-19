"""Tests for noisy-jobs audit helpers."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from job_search.audit_noisy_jobs import audit_active_jobs, mark_blocklist_inactive
from job_search.job_db import connect, init_schema, upsert_job, upsert_score


class AuditNoisyJobsTests(unittest.TestCase):
    def _seed(self, conn) -> None:
        upsert_job(
            conn,
            {
                "uuid": "noise-1",
                "source": "finn_no",
                "status": "ACTIVE",
                "title": "Butikkmedarbeider",
                "employer_name": "REMA 1000",
                "description_text": "Vi søker butikkmedarbeider til kasse.",
                "fetched_at": "2026-08-26T10:00:00+00:00",
                "keyword_hits": None,
                "in_rogaland": 1,
            },
        )
        upsert_job(
            conn,
            {
                "uuid": "weak-1",
                "source": "finn_no",
                "status": "ACTIVE",
                "title": "Associate Professor in Fish Biology",
                "employer_name": "UiT",
                "description_text": "Forskning og undervisning i biologi.",
                "fetched_at": "2026-08-26T10:00:00+00:00",
                "keyword_hits": "forskning, research",
                "in_rogaland": 0,
            },
        )
        upsert_job(
            conn,
            {
                "uuid": "good-1",
                "source": "finn_no",
                "status": "ACTIVE",
                "title": "ML Engineer",
                "employer_name": "Tech AS",
                "description_text": "Python machine learning and LLM fine-tuning.",
                "fetched_at": "2026-08-26T10:00:00+00:00",
                "keyword_hits": "machine learning, Python",
                "in_rogaland": 1,
            },
        )
        for uuid, base in (("noise-1", 0.0), ("weak-1", 0.0), ("good-1", 3.0)):
            upsert_score(
                conn,
                {
                    "uuid": uuid,
                    "source": "finn_no",
                    "track": "industry",
                    "scored_at": "2026-08-26T10:00:00+00:00",
                    "score_base": base,
                    "boost_rogaland": 0.0,
                    "boost_tek": 0.0,
                    "score_total": base,
                    "matched_keywords": "machine learning" if base > 0 else None,
                    "matched_skills": "Python" if base > 0 else None,
                    "tek_match_name": None,
                },
            )
        conn.commit()

    def test_audit_flags_blocklist_and_zero_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "jobs.sqlite")
            init_schema(conn)
            self._seed(conn)
            summary = audit_active_jobs(conn, track="industry", print_limit=10)
            self.assertEqual(summary["active"], 3)
            self.assertGreaterEqual(summary["blocklist_active"], 1)
            self.assertGreaterEqual(summary["zero_score"], 2)
            titles = {row["title"] for row in summary["samples"]["blocklist"]}
            self.assertIn("Butikkmedarbeider", titles)

    def test_mark_blocklist_inactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "jobs.sqlite")
            init_schema(conn)
            self._seed(conn)
            n = mark_blocklist_inactive(conn)
            self.assertGreaterEqual(n, 1)
            status = conn.execute(
                "SELECT status FROM job_postings WHERE uuid = ?",
                ("noise-1",),
            ).fetchone()["status"]
            self.assertEqual(status, "INACTIVE")
            still = conn.execute(
                "SELECT status FROM job_postings WHERE uuid = ?",
                ("good-1",),
            ).fetchone()["status"]
            self.assertEqual(still, "ACTIVE")


if __name__ == "__main__":
    unittest.main()
