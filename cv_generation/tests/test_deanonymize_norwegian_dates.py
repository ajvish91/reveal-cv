"""Norwegian CV deanonymize: English date keys expand to localized forms."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.deanonymize_cvs import (
    apply_replacements,
    expand_mapping_norwegian_dates,
    norwegian_date_variants,
)


TWODAY_NO = REPO / "cv_generation/cv_runs/20260630T115312Z_Twoday_senior-data-engineer-data-scientist/final_cv_no.md"


class TestNorwegianDateDeanonymize(unittest.TestCase):
    def test_variants_match_agent_cv_month_style(self) -> None:
        self.assertIn("mar. 2026 – nå", norwegian_date_variants("Mar 2026 - Present"))
        self.assertIn("sep. 2025 – mar. 2026", norwegian_date_variants("Sep 2025 - Mar 2026"))
        self.assertIn("15. mars 1992", norwegian_date_variants("15 Mar 1992"))
        self.assertIn("jul. 2020 – jul. 2021", norwegian_date_variants("Jul 2020 - Jul 2021"))

    def test_english_date_keys_replace_in_norwegian_cv(self) -> None:
        if not TWODAY_NO.is_file():
            self.skipTest("Twoday run not present")
        text = TWODAY_NO.read_text(encoding="utf-8")
        mapping = expand_mapping_norwegian_dates(
            {
                "15 Mar 1992": "15 Mar 1990",
                "Mar 2026 - Present": "Jan 2025 - Present",
                "Sep 2025 - Mar 2026": "Jun 2024 - Dec 2024",
                "Aug 2022 - Aug 2025": "Aug 2020 - Aug 2023",
                "2022 - 2025": "2020 - 2023",
            }
        )
        out, counts = apply_replacements(text, mapping)
        self.assertIn("15. mars 1990", out)
        self.assertIn("jan. 2025 – nå", out)
        self.assertNotIn("15. mars 1992", out)
        self.assertNotIn("sep. 2025 – mar. 2026", out)
        self.assertTrue(counts)


if __name__ == "__main__":
    unittest.main()
