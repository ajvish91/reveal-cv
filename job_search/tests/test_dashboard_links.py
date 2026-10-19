"""Tests for the public ad/listing URL used by the dashboard drawer."""
from __future__ import annotations

import unittest

from job_search.web.services import best_job_url, job_row_payload


class JobUrlTests(unittest.TestCase):
    def test_jobbnorge_prefers_listing_over_login_apply_url(self) -> None:
        row = {
            "source": "jobbnorge",
            "link": "https://www.jobbnorge.no/ledige-stillinger/stilling/307541",
            "application_url": "https://jobseeker.jobbnorge.no/client/apply/307541",
        }
        self.assertEqual(best_job_url(row), row["link"])

    def test_nav_prefers_listing_over_external_ats_apply_url(self) -> None:
        row = {
            "source": "nav_arbeidsplassen",
            "link": "https://arbeidsplassen.nav.no/stillinger/stilling/abc",
            "application_url": "https://jobseeker.jobbnorge.no/apply/308405",
        }
        self.assertEqual(best_job_url(row), row["link"])

    def test_falls_back_to_application_url_when_link_missing(self) -> None:
        row = {
            "source": "nav_arbeidsplassen",
            "link": "",
            "application_url": "https://example.no/apply/1",
        }
        self.assertEqual(best_job_url(row), "https://example.no/apply/1")

    def test_finn_uses_same_ad_url(self) -> None:
        row = {
            "source": "finn_no",
            "title": "Data Engineer",
            "link": "https://www.finn.no/job/ad/465089104",
            "application_url": "https://www.finn.no/job/ad/465089104",
        }
        self.assertEqual(best_job_url(row), row["link"])
        self.assertEqual(job_row_payload(row)["job_url"], row["link"])
