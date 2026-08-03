"""Tests for dashboard Apply language resolution (no Streamlit import)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.apply_prompts import normalize_apply_language, resolve_apply_language
from job_search.dashboard import (
    ApplyPipelineOptions,
    apply_dialog_language_key,
    apply_pipeline_options_from_mapping,
    apply_pipeline_options_to_mapping,
)


class TestDashboardApplyLanguage(unittest.TestCase):
    def test_sidebar_default_is_english(self) -> None:
        self.assertEqual(normalize_apply_language(None), "en")

    def test_popover_inherits_sidebar(self) -> None:
        self.assertEqual(resolve_apply_language("no", "inherit"), "no")
        self.assertEqual(resolve_apply_language("en", "inherit"), "en")

    def test_popover_overrides_sidebar(self) -> None:
        self.assertEqual(resolve_apply_language("en", "no"), "no")
        self.assertEqual(resolve_apply_language("no", "en"), "en")

    def test_apply_dialog_language_key(self) -> None:
        self.assertEqual(apply_dialog_language_key("job_42"), "job_42_dialog_language")

    def test_pipeline_options_round_trip_preserves_norwegian(self) -> None:
        opts = ApplyPipelineOptions(language="no", generate_cover_letter=True)
        payload = apply_pipeline_options_to_mapping(opts)
        self.assertEqual(payload["language"], "no")
        restored = apply_pipeline_options_from_mapping(payload)
        self.assertEqual(restored.language, "no")

    def test_pipeline_options_top_level_language_overrides_dict(self) -> None:
        payload = apply_pipeline_options_to_mapping(ApplyPipelineOptions(language="en"))
        restored = apply_pipeline_options_from_mapping(payload, language="no")
        self.assertEqual(restored.language, "no")

    def test_pipeline_options_from_none_defaults_to_english(self) -> None:
        restored = apply_pipeline_options_from_mapping(None)
        self.assertEqual(restored.language, "en")

    def test_pipeline_options_from_dataclass_with_language_override(self) -> None:
        opts = ApplyPipelineOptions(language="en")
        restored = apply_pipeline_options_from_mapping(opts, language="no")
        self.assertEqual(restored.language, "no")


if __name__ == "__main__":
    unittest.main()
