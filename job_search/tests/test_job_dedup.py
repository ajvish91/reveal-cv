from __future__ import annotations

import unittest

import pandas as pd

from job_search.job_dedup import dedup_key, dedupe_jobs_df, normalize_text


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


if __name__ == "__main__":
    unittest.main()
