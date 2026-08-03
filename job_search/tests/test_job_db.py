"""Tests for job_search.job_db helpers."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.job_db import (
    connect,
    delete_application,
    init_schema,
    upsert_application,
    upsert_job,
    utc_now_iso,
)


class TestDeleteApplication(unittest.TestCase):
    def test_delete_application_removes_matching_row(self) -> None:
        now = utc_now_iso()
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.sqlite"
            conn = connect(db_path)
            init_schema(conn)
            upsert_application(
                conn,
                {
                    "uuid": "job-1",
                    "source": "nav_arbeidsplassen",
                    "track": "industry",
                    "status": "drafted",
                    "notes": "CV run: /x/run_one",
                    "updated_at": now,
                },
            )
            upsert_application(
                conn,
                {
                    "uuid": "job-1",
                    "source": "nav_arbeidsplassen",
                    "track": "academic",
                    "status": "interested",
                    "notes": None,
                    "updated_at": now,
                },
            )
            conn.commit()

            delete_application(conn, "job-1", "nav_arbeidsplassen", "industry")
            conn.commit()

            remaining = conn.execute(
                "SELECT track FROM applications ORDER BY track"
            ).fetchall()
            self.assertEqual([row["track"] for row in remaining], ["academic"])

            delete_application(conn, "job-1", "nav_arbeidsplassen", "academic")
            conn.commit()
            count = conn.execute("SELECT COUNT(*) AS n FROM applications").fetchone()
            assert count is not None
            self.assertEqual(int(count["n"]), 0)
            conn.close()

    def test_delete_application_missing_row_is_no_op(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.sqlite"
            conn = connect(db_path)
            init_schema(conn)
            delete_application(conn, "missing", "nav_arbeidsplassen", "industry")
            conn.commit()
            count = conn.execute("SELECT COUNT(*) AS n FROM applications").fetchone()
            assert count is not None
            self.assertEqual(int(count["n"]), 0)
            conn.close()


class TestUpsertJobPreservesDescription(unittest.TestCase):
    def test_empty_reingest_keeps_existing_description_and_detail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.sqlite"
            conn = connect(db_path)
            init_schema(conn)
            upsert_job(
                conn,
                {
                    "uuid": "469335085",
                    "source": "finn_no",
                    "status": "ACTIVE",
                    "title": "AI Engineer",
                    "description_text": "Full posting body about ML systems.",
                    "raw_json": '{"search_card": {}, "detail": {"html": "<p>x</p>"}}',
                    "fetched_at": "2026-07-20T10:00:00+00:00",
                },
            )
            upsert_job(
                conn,
                {
                    "uuid": "469335085",
                    "source": "finn_no",
                    "status": "ACTIVE",
                    "title": "AI Engineer",
                    "description_text": None,
                    "raw_json": '{"search_card": {"finnkode": "469335085"}}',
                    "fetched_at": "2026-07-20T12:00:00+00:00",
                },
            )
            conn.commit()
            row = conn.execute(
                "SELECT description_text, raw_json, fetched_at FROM job_postings WHERE uuid = ?",
                ("469335085",),
            ).fetchone()
            assert row is not None
            self.assertEqual(row["description_text"], "Full posting body about ML systems.")
            self.assertIn('"detail"', row["raw_json"])
            self.assertEqual(row["fetched_at"], "2026-07-20T12:00:00+00:00")
            conn.close()


if __name__ == "__main__":
    unittest.main()
