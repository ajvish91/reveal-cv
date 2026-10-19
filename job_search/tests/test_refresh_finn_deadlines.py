from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from job_search.finn_deadlines import expires_and_status_from_finn_detail
from job_search.finn_job_client import FINN_EXPIRED_SENTINEL
from job_search.job_db import connect, init_schema, upsert_job, utc_now_iso
from job_search.refresh_finn_deadlines import mark_known_expired_inactive, refresh_missing_finn_deadlines


class FinnDeadlineRefreshTests(unittest.TestCase):
    def test_expires_and_status_from_expired_badge(self) -> None:
        expires, status = expires_and_status_from_finn_detail({"listingExpired": True})
        self.assertEqual(expires, FINN_EXPIRED_SENTINEL)
        self.assertEqual(status, "INACTIVE")

    def test_expires_snarest_text_with_expired_badge_uses_sentinel(self) -> None:
        expires, status = expires_and_status_from_finn_detail(
            {"validThrough": "Snarest", "listingExpired": True}
        )
        self.assertEqual(expires, FINN_EXPIRED_SENTINEL)
        self.assertEqual(status, "INACTIVE")

    def test_expires_and_status_from_future_deadline(self) -> None:
        expires, status = expires_and_status_from_finn_detail({"validThrough": "2099-01-01"})
        self.assertEqual(expires, "2099-01-01")
        self.assertEqual(status, "ACTIVE")

    def test_mark_known_expired_inactive(self) -> None:
        now = utc_now_iso()
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "jobs.sqlite")
            init_schema(conn)
            for uuid, expires in (("past", "2020-01-01"), ("future", "2099-01-01"), ("blank", None)):
                upsert_job(
                    conn,
                    {
                        "uuid": uuid,
                        "source": "finn_no",
                        "status": "ACTIVE",
                        "title": uuid,
                        "expires": expires,
                        "fetched_at": now,
                    },
                )
            conn.commit()
            n = mark_known_expired_inactive(conn)
            rows = {
                row["uuid"]: row["status"]
                for row in conn.execute("SELECT uuid, status FROM job_postings").fetchall()
            }
            self.assertEqual(n, 1)
            self.assertEqual(rows["past"], "INACTIVE")
            self.assertEqual(rows["future"], "ACTIVE")
            self.assertEqual(rows["blank"], "ACTIVE")

    def test_refresh_missing_finn_deadlines_updates_row(self) -> None:
        now = utc_now_iso()
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "jobs.sqlite")
            init_schema(conn)
            upsert_job(
                conn,
                {
                    "uuid": "471127093",
                    "source": "finn_no",
                    "status": "ACTIVE",
                    "title": "AI Lead",
                    "expires": None,
                    "fetched_at": now,
                },
            )
            conn.commit()

            class FakeClient:
                def fetch_deadline_only(self, finnkode: str, **kwargs):
                    return {
                        "validThrough": None,
                        "listingExpired": True,
                    }

            summary = refresh_missing_finn_deadlines(conn, FakeClient(), limit=10)
            row = conn.execute(
                "SELECT expires, status FROM job_postings WHERE uuid = ?",
                ("471127093",),
            ).fetchone()
            self.assertEqual(summary["refreshed"], 1)
            self.assertEqual(summary["inactivated"], 1)
            assert row is not None
            self.assertEqual(row["expires"], FINN_EXPIRED_SENTINEL)
            self.assertEqual(row["status"], "INACTIVE")


if __name__ == "__main__":
    unittest.main()
