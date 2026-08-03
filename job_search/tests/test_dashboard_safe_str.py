"""Tests for NaN-safe string helpers used by the Streamlit dashboard."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.dashboard import _safe_str, format_location, format_job_export_text


class SafeStrTests(unittest.TestCase):
    def test_safe_str_none_and_nan(self) -> None:
        self.assertEqual(_safe_str(None), "")
        self.assertEqual(_safe_str(float("nan")), "")
        self.assertEqual(_safe_str(math.nan), "")
        self.assertEqual(_safe_str(pd.NA), "")

    def test_safe_str_strips_text(self) -> None:
        self.assertEqual(_safe_str("  Stavanger  "), "Stavanger")
        self.assertEqual(_safe_str(42), "42")

    def test_format_location_tolerates_nan_fields(self) -> None:
        loc = format_location(
            {
                "location_label": float("nan"),
                "municipal": math.nan,
                "county": None,
            }
        )
        self.assertEqual(loc, "")

    def test_format_location_municipal_county(self) -> None:
        self.assertEqual(
            format_location({"municipal": "Stavanger", "county": "Rogaland"}),
            "Stavanger, Rogaland",
        )
        self.assertEqual(
            format_location({"location_label": " Oslo ", "municipal": float("nan")}),
            "Oslo",
        )

    def test_format_job_export_text_tolerates_nan(self) -> None:
        text = format_job_export_text(
            {
                "title": "ML Engineer",
                "employer_name": float("nan"),
                "source": "nav_arbeidsplassen",
                "uuid": "abc",
                "location_label": math.nan,
                "municipal": None,
                "county": None,
                "description_text": float("nan"),
            }
        )
        self.assertIn("Role: ML Engineer", text)
        self.assertNotIn("nan", text.casefold())


if __name__ == "__main__":
    unittest.main()
