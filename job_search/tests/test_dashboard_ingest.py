"""Tests for dashboard ingest-cycle helpers (no Streamlit runtime)."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.dashboard import build_ingest_cycle_command, parse_ingest_cycle_output


class TestBuildIngestCycleCommand(unittest.TestCase):
    def test_default_daily_cycle(self) -> None:
        cmd = build_ingest_cycle_command(python_exe="/usr/bin/python3")
        self.assertEqual(cmd[0], "/usr/bin/python3")
        self.assertTrue(str(cmd[1]).endswith("scripts/run_job_search_cycle.py"))
        self.assertNotIn("--skip-ingest", cmd)
        self.assertNotIn("--skip-nav-ingest", cmd)
        self.assertNotIn("--skip-finn-ingest", cmd)

    def test_db_path_forwarded(self) -> None:
        cmd = build_ingest_cycle_command(db_path="/tmp/jobs.sqlite", python_exe="py")
        self.assertEqual(cmd[:4], ["py", str(REPO / "scripts" / "run_job_search_cycle.py"), "--db", "/tmp/jobs.sqlite"])

    def test_skip_nav_only(self) -> None:
        cmd = build_ingest_cycle_command(skip_nav=True, python_exe="py")
        self.assertIn("--skip-nav-ingest", cmd)
        self.assertNotIn("--skip-finn-ingest", cmd)
        self.assertNotIn("--skip-ingest", cmd)

    def test_skip_finn_only(self) -> None:
        cmd = build_ingest_cycle_command(skip_finn=True, python_exe="py")
        self.assertIn("--skip-finn-ingest", cmd)
        self.assertNotIn("--skip-nav-ingest", cmd)

    def test_skip_both_runs_score_only(self) -> None:
        cmd = build_ingest_cycle_command(skip_nav=True, skip_finn=True, python_exe="py")
        self.assertIn("--skip-ingest", cmd)
        self.assertNotIn("--skip-nav-ingest", cmd)
        self.assertNotIn("--skip-finn-ingest", cmd)

    def test_academic_queries_only(self) -> None:
        cmd = build_ingest_cycle_command(academic_queries_only=True, python_exe="py")
        self.assertEqual(
            cmd[-2:],
            ["--finn-ingest-arg=--search-track", "--finn-ingest-arg=academic"],
        )

    def test_academic_queries_only_argparse_accepts(self) -> None:
        import argparse

        cmd = build_ingest_cycle_command(academic_queries_only=True, python_exe="py")
        parser = argparse.ArgumentParser()
        parser.add_argument("--db", default="")
        parser.add_argument("--skip-ingest", action="store_true")
        parser.add_argument("--skip-nav-ingest", action="store_true")
        parser.add_argument("--skip-finn-ingest", action="store_true")
        parser.add_argument("--finn-ingest-arg", action="append", default=[], metavar="ARG")
        args = parser.parse_args(cmd[2:])
        self.assertEqual(args.finn_ingest_arg, ["--search-track", "academic"])


class TestParseIngestCycleOutput(unittest.TestCase):
    def test_parses_step_json_blocks(self) -> None:
        nav_summary = {"stored_rows": 12, "if_modified_since": "2026-01-01T00:00:00+00:00"}
        finn_summary = {"stored_rows": 8, "queries": ["postdoc"]}
        score_summary = {"score_rows": 40, "jobs": 20}
        stdout = "\n".join(
            [
                "[job-search] ingest-nav: py -m job_search.ingest_nav_jobs",
                json.dumps(nav_summary, indent=2),
                "[job-search] ingest-finn: py -m job_search.ingest_finn_jobs",
                json.dumps(finn_summary, indent=2),
                "[job-search] score: py -m job_search.score_jobs",
                json.dumps(score_summary, indent=2),
            ]
        )
        parsed = parse_ingest_cycle_output(stdout)
        steps = parsed["steps"]
        self.assertEqual(steps["ingest-nav"]["stored_rows"], 12)
        self.assertEqual(steps["ingest-finn"]["stored_rows"], 8)
        self.assertEqual(steps["score"]["score_rows"], 40)


if __name__ == "__main__":
    unittest.main()
