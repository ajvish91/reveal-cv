"""Tests for job quick actions (pin, skip, mark applied)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from job_search.job_db import connect, init_schema, upsert_job
from job_search.web.services import STATUS_OPTIONS, apply_job_quick_action


class JobQuickActionTests(unittest.TestCase):
    def _conn(self, tmp: str):
        conn = connect(Path(tmp) / "jobs.sqlite")
        init_schema(conn)
        upsert_job(
            conn,
            {
                "uuid": "job-1",
                "source": "finn_no",
                "status": "ACTIVE",
                "title": "ML Engineer",
                "employer_name": "Tech AS",
                "fetched_at": "2026-08-26T12:00:00+00:00",
            },
        )
        conn.commit()
        return conn

    def test_pin_and_mark_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = self._conn(tmp)
            out = apply_job_quick_action(
                conn, uuid="job-1", source="finn_no", track="industry", action="pin"
            )
            self.assertTrue(out["application"]["pinned"])
            out2 = apply_job_quick_action(
                conn, uuid="job-1", source="finn_no", track="industry", action="mark_applied"
            )
            self.assertEqual(out2["application"]["status"], "applied")
            self.assertTrue(out2["application"]["pinned"])
            self.assertTrue(out2["application"]["applied_at"])

    def test_skip_unpins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = self._conn(tmp)
            apply_job_quick_action(conn, uuid="job-1", source="finn_no", track="industry", action="pin")
            out = apply_job_quick_action(
                conn, uuid="job-1", source="finn_no", track="industry", action="skip"
            )
            self.assertEqual(out["application"]["status"], "skipped")
            self.assertEqual(out["application"]["pinned"], 0)
            self.assertIn("skipped", STATUS_OPTIONS)

    def test_clear_removes_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = self._conn(tmp)
            apply_job_quick_action(
                conn, uuid="job-1", source="finn_no", track="industry", action="interested"
            )
            out = apply_job_quick_action(
                conn, uuid="job-1", source="finn_no", track="industry", action="clear"
            )
            self.assertTrue(out["cleared"])
            row = conn.execute(
                "SELECT 1 FROM applications WHERE uuid = ? AND source = ? AND track = ?",
                ("job-1", "finn_no", "industry"),
            ).fetchone()
            self.assertIsNone(row)


    def test_mark_expired_inactivates_posting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = self._conn(tmp)
            out = apply_job_quick_action(
                conn, uuid="job-1", source="finn_no", track="industry", action="mark_expired"
            )
            self.assertEqual(out["action"], "mark_expired")
            self.assertEqual(out["posting"]["status"], "INACTIVE")
            row = conn.execute(
                "SELECT status, expires FROM job_postings WHERE uuid = ?",
                ("job-1",),
            ).fetchone()
            self.assertEqual(row["status"], "INACTIVE")
            self.assertEqual(row["expires"], "1970-01-01")
            # Does not create an applications row.
            app = conn.execute(
                "SELECT 1 FROM applications WHERE uuid = ?",
                ("job-1",),
            ).fetchone()
            self.assertIsNone(app)


if __name__ == "__main__":
    unittest.main()
