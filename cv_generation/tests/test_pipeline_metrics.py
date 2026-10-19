"""Tests for pipeline impact metrics collection."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.pipeline_metrics import (
    METRICS_FILENAME,
    PipelineMetricsCollector,
    estimate_energy_kwh,
    estimate_tokens_from_text,
    format_pipeline_metrics_summary,
    load_pipeline_metrics,
    write_pipeline_metrics,
)


class TestPipelineMetrics(unittest.TestCase):
    def test_estimate_tokens_from_text(self) -> None:
        self.assertEqual(estimate_tokens_from_text(""), 0)
        self.assertEqual(estimate_tokens_from_text("abcd"), 1)
        self.assertEqual(estimate_tokens_from_text("a" * 400), 100)

    def test_estimate_energy_kwh_with_tokens(self) -> None:
        est = estimate_energy_kwh(20_000, 5_000)
        self.assertIsNotNone(est["kwh"])
        self.assertIsNotNone(est["co2_kg"])
        self.assertEqual(est["method"], "token_based_v1")
        self.assertIn("disclaimer", est)

    def test_estimate_energy_kwh_without_tokens(self) -> None:
        est = estimate_energy_kwh(0, 0)
        self.assertIsNone(est["kwh"])
        self.assertIsNone(est["co2_kg"])

    def test_collector_records_api_and_char_fallback(self) -> None:
        collector = PipelineMetricsCollector(provider="anthropic", model="claude-test")
        collector.record_stage(
            name="01_jd_parser",
            started_mono=0.0,
            ended_mono=2.5,
            provider="anthropic",
            model="claude-test",
            tokens_input=1000,
            tokens_output=200,
            tokens_source="api",
        )
        collector.record_stage(
            name="02_keyword_ranker",
            started_mono=2.5,
            ended_mono=5.0,
            provider="cursor",
            model="composer-2.5",
            prompt_text="x" * 400,
            response_text="y" * 200,
        )
        metrics = collector.finalize()
        self.assertEqual(len(metrics.stages), 2)
        self.assertEqual(metrics.stages[0].tokens_source, "api")
        self.assertEqual(metrics.stages[1].tokens_source, "estimated_chars")
        self.assertEqual(metrics.totals["tokens_source"], "mixed")
        self.assertGreater(metrics.totals["tokens_total"], 0)

    def test_write_and_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            collector = PipelineMetricsCollector(provider="openai", model="gpt-4o")
            collector.record_stage(
                name="01_jd_parser",
                started_mono=0.0,
                ended_mono=1.0,
                tokens_input=500,
                tokens_output=100,
                tokens_source="api",
            )
            write_pipeline_metrics(run_dir, collector.finalize())
            path = run_dir / METRICS_FILENAME
            self.assertTrue(path.is_file())
            loaded = load_pipeline_metrics(run_dir)
            assert loaded is not None
            self.assertEqual(loaded["version"], 1)
            self.assertEqual(loaded["totals"]["tokens_input"], 500)

    def test_format_pipeline_metrics_summary(self) -> None:
        sample = {
            "duration_sec": 252,
            "totals": {
                "wall_clock_sec": 252,
                "tokens_total": 42_000,
                "tokens_source": "estimated_chars",
            },
            "energy_estimate": {"kwh": 0.021},
        }
        line = format_pipeline_metrics_summary(sample)
        assert line is not None
        self.assertIn("Pipeline:", line)
        self.assertIn("4m", line)
        self.assertIn("42k tokens", line)
        self.assertIn("kWh", line)

    def test_format_summary_none_when_empty(self) -> None:
        self.assertIsNone(format_pipeline_metrics_summary(None))
        self.assertIsNone(format_pipeline_metrics_summary({}))


if __name__ == "__main__":
    unittest.main()
