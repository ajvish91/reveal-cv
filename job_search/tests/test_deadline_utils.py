"""Tests for deadline_utils."""
from __future__ import annotations

import unittest
from datetime import date

from job_search.deadline_utils import (
    apply_soon_badge,
    coerce_expires_value,
    days_until_deadline,
    deadline_display,
    is_apply_soon,
    parse_deadline,
)


class DeadlineUtilsTests(unittest.TestCase):
    def test_parse_iso_date(self) -> None:
        self.assertEqual(parse_deadline("2026-08-15"), date(2026, 8, 15))
        self.assertEqual(parse_deadline("2026-08-15T23:59:59Z"), date(2026, 8, 15))

    def test_parse_norwegian_month_name(self) -> None:
        self.assertEqual(parse_deadline("Søknadsfrist 15. august 2026"), date(2026, 8, 15))

    def test_parse_dotted_date(self) -> None:
        self.assertEqual(parse_deadline("Frist: 15.08.2026"), date(2026, 8, 15))

    def test_days_until_and_apply_soon(self) -> None:
        today = date(2026, 7, 13)
        self.assertEqual(days_until_deadline("2026-07-20", today=today), 7)
        self.assertTrue(is_apply_soon("2026-07-20", within_days=7, today=today))
        self.assertFalse(is_apply_soon("2026-08-01", within_days=7, today=today))
        self.assertEqual(apply_soon_badge("2026-07-13", within_days=7, today=today), "Apply soon (today)")

    def test_unknown_deadline(self) -> None:
        self.assertIsNone(parse_deadline(""))
        self.assertIsNone(days_until_deadline("soon"))
        self.assertEqual(apply_soon_badge("soon"), "")

    def test_place_garbage_deadline(self) -> None:
        self.assertIsNone(coerce_expires_value("Place"))
        self.assertIsNone(coerce_expires_value({"@type": "Place"}))
        self.assertEqual(deadline_display("Place"), "—")
        self.assertEqual(deadline_display('{"@type": "Place", "address": {}}'), "—")
        self.assertEqual(
            deadline_display('{"validThrough": "2026-08-15", "@type": "Place"}'),
            "2026-08-15",
        )


if __name__ == "__main__":
    unittest.main()
