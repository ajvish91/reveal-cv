"""Tests for dashboard periodic refresh helpers (no Streamlit runtime)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.dashboard_refresh import (
    AUTO_REFRESH_MINUTE_OPTIONS,
    format_auto_refresh_label,
    refresh_interval_seconds,
    should_periodic_refresh,
)


class TestRefreshIntervalSeconds(unittest.TestCase):
    def test_off_returns_none(self) -> None:
        self.assertIsNone(refresh_interval_seconds(0))
        self.assertIsNone(refresh_interval_seconds(-1))

    def test_positive_minutes_to_seconds(self) -> None:
        self.assertEqual(refresh_interval_seconds(2), 120)
        self.assertEqual(refresh_interval_seconds(5), 300)
        self.assertEqual(refresh_interval_seconds(10), 600)


class TestFormatAutoRefreshLabel(unittest.TestCase):
    def test_off_and_interval_labels(self) -> None:
        self.assertEqual(format_auto_refresh_label(0), "Off")
        self.assertEqual(format_auto_refresh_label(5), "Every 5 min")


class TestShouldPeriodicRefresh(unittest.TestCase):
    def test_disabled_interval_never_refreshes(self) -> None:
        self.assertFalse(
            should_periodic_refresh(
                interval_minutes=0,
                last_refresh_monotonic=0.0,
                now_monotonic=10_000.0,
            )
        )

    def test_not_due_before_interval(self) -> None:
        self.assertFalse(
            should_periodic_refresh(
                interval_minutes=5,
                last_refresh_monotonic=100.0,
                now_monotonic=399.0,
            )
        )

    def test_due_at_interval_boundary(self) -> None:
        self.assertTrue(
            should_periodic_refresh(
                interval_minutes=2,
                last_refresh_monotonic=50.0,
                now_monotonic=170.0,
            )
        )

    def test_due_after_interval(self) -> None:
        self.assertTrue(
            should_periodic_refresh(
                interval_minutes=10,
                last_refresh_monotonic=0.0,
                now_monotonic=601.0,
            )
        )


class TestAutoRefreshOptions(unittest.TestCase):
    def test_default_off_with_standard_intervals(self) -> None:
        self.assertEqual(AUTO_REFRESH_MINUTE_OPTIONS[0], 0)
        self.assertEqual(AUTO_REFRESH_MINUTE_OPTIONS, (0, 2, 5, 10))


if __name__ == "__main__":
    unittest.main()
