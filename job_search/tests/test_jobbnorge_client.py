from __future__ import annotations

import unittest
from pathlib import Path

from job_search.jobbnorge_client import (
    deadline_from_pdf_text,
    listing_url,
    normalize_api_deadline,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class JobbnorgeClientTests(unittest.TestCase):
    def test_normalize_api_deadline_dotted(self) -> None:
        self.assertEqual(normalize_api_deadline("25.09.2026"), "2026-09-25")

    def test_normalize_api_deadline_open(self) -> None:
        self.assertIsNone(normalize_api_deadline("Løpende"))

    def test_deadline_from_pdf_text(self) -> None:
        self.assertEqual(deadline_from_pdf_text("Deadline: 10/5/2026\nOther"), "2026-10-05")

    def test_listing_url(self) -> None:
        self.assertEqual(
            listing_url(307898),
            "https://www.jobbnorge.no/ledige-stillinger/stilling/307898",
        )

    def test_pdf_fixture_extracts_text(self) -> None:
        pdf_path = FIXTURES / "jobbnorge_307898.pdf"
        if not pdf_path.is_file():
            self.skipTest("fixture PDF missing")
        from pypdf import PdfReader

        text = "".join(p.extract_text() or "" for p in PdfReader(str(pdf_path)).pages)
        self.assertIn("307898", text)
        self.assertIn("Machine Learning", text)
        self.assertEqual(deadline_from_pdf_text(text), "2026-10-05")


if __name__ == "__main__":
    unittest.main()
