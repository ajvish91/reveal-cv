from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from job_search.job_db import connect, init_schema, upsert_job, utc_now_iso
from job_search.job_dedup import (
    dedup_key,
    dedupe_jobs_df,
    mark_cross_source_duplicates_inactive,
    normalize_text,
)


class JobDedupTests(unittest.TestCase):
    def test_normalize_text_strips_punctuation_and_whitespace(self) -> None:
        self.assertEqual(
            normalize_text("  Acme AS — Senior Developer!!  "),
            "acme as senior developer",
        )

    def test_dedup_key_uses_employer_and_title(self) -> None:
        self.assertEqual(
            dedup_key("Acme AS", "Senior Developer"),
            dedup_key("acme as", "senior developer"),
        )

    def test_dedup_key_strips_employer_legal_suffix(self) -> None:
        self.assertEqual(
            dedup_key("Sopra Steria AS", "Data Engineer"),
            dedup_key("Sopra Steria", "Data Engineer"),
        )
        self.assertEqual(
            dedup_key("Capgemini Norge AS", "Consultant"),
            dedup_key("Capgemini", "Consultant"),
        )

    def test_dedupe_prefers_higher_score(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "uuid": "f1",
                    "source": "finn_no",
                    "title": "Data Engineer",
                    "employer_name": "Example AS",
                    "score_total": 40.0,
                    "score_base": 30.0,
                    "link": "https://finn.no/job/ad/1",
                    "application_url": "https://finn.no/job/ad/1",
                },
                {
                    "uuid": "n1",
                    "source": "nav_arbeidsplassen",
                    "title": "Data Engineer",
                    "employer_name": "Example AS",
                    "score_total": 25.0,
                    "score_base": 20.0,
                    "link": "https://arbeidsplassen.nav.no/stillinger/stilling/n1",
                    "application_url": "https://arbeidsplassen.nav.no/apply/n1",
                },
            ]
        )
        out = dedupe_jobs_df(df)
        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["uuid"], "f1")
        self.assertEqual(out.iloc[0]["sources"], "nav_arbeidsplassen, finn_no")
        self.assertIn("nav_arbeidsplassen", out.iloc[0]["duplicate_note"])

    def test_dedupe_prefers_nav_apply_url_when_scores_tie(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "uuid": "f1",
                    "source": "finn_no",
                    "title": "ML Engineer",
                    "employer_name": "North AS",
                    "score_total": 30.0,
                    "score_base": 30.0,
                    "link": "https://finn.no/job/ad/9",
                    "application_url": "https://finn.no/job/ad/9",
                },
                {
                    "uuid": "n1",
                    "source": "nav_arbeidsplassen",
                    "title": "ML Engineer",
                    "employer_name": "North AS",
                    "score_total": 30.0,
                    "score_base": 30.0,
                    "link": "https://arbeidsplassen.nav.no/stillinger/stilling/n1",
                    "application_url": "https://arbeidsplassen.nav.no/apply/n1",
                },
            ]
        )
        out = dedupe_jobs_df(df)
        self.assertEqual(len(out), 1)
        self.assertEqual(out.iloc[0]["uuid"], "n1")
        self.assertEqual(out.iloc[0]["application_url"], "https://arbeidsplassen.nav.no/apply/n1")


class CrossSourceDedupTests(unittest.TestCase):
    def _row(self, uuid: str, source: str, employer: str, title: str) -> dict:
        return {
            "uuid": uuid,
            "source": source,
            "status": "ACTIVE",
            "title": title,
            "employer_name": employer,
            "fetched_at": utc_now_iso(),
            "description_text": "x" * 400,
        }

    def _statuses(self, conn) -> dict[tuple[str, str], str]:
        return {
            (r["uuid"], r["source"]): r["status"]
            for r in conn.execute("SELECT uuid, source, status FROM job_postings").fetchall()
        }

    def test_cross_source_duplicate_marks_lower_priority_inactive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "jobs.sqlite")
            init_schema(conn)
            upsert_job(conn, self._row("f1", "finn_no", "Example AS", "Data Engineer"))
            upsert_job(conn, self._row("n1", "nav_arbeidsplassen", "Example AS", "Data Engineer"))
            conn.commit()
            marked = mark_cross_source_duplicates_inactive(conn)
            conn.commit()
            self.assertEqual(marked, 1)
            statuses = self._statuses(conn)
            self.assertEqual(statuses[("n1", "nav_arbeidsplassen")], "ACTIVE")
            self.assertEqual(statuses[("f1", "finn_no")], "INACTIVE")
            conn.close()

    def test_same_source_multiples_are_left_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "jobs.sqlite")
            init_schema(conn)
            upsert_job(conn, self._row("a", "finn_no", "Example AS", "Data Engineer"))
            upsert_job(conn, self._row("b", "finn_no", "Example AS", "Data Engineer"))
            conn.commit()
            marked = mark_cross_source_duplicates_inactive(conn)
            self.assertEqual(marked, 0)
            statuses = self._statuses(conn)
            self.assertEqual(statuses[("a", "finn_no")], "ACTIVE")
            self.assertEqual(statuses[("b", "finn_no")], "ACTIVE")
            conn.close()


if __name__ == "__main__":
    unittest.main()
