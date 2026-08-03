"""Tests for optional apply tailoring instructions."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.apply_prompts import (
    APPLY_PROMPTS_FILENAME,
    apply_language_markdown_section,
    apply_prompts_markdown_section,
    merge_apply_prompts,
    normalize_apply_language,
    read_apply_prompts,
    resolve_apply_language,
    write_apply_prompts,
)

JOB_FILE = REPO / "cv_generation" / "jobs" / "demo_northline_ml_engineer.txt"


class TestApplyPrompts(unittest.TestCase):
    def test_merge_skips_empty_parts(self) -> None:
        self.assertEqual(merge_apply_prompts("", "  emphasize RAG  ", None), "emphasize RAG")
        self.assertEqual(
            merge_apply_prompts("default note", "per-job note"),
            "default note\n\nper-job note",
        )

    def test_write_and_read_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            path = write_apply_prompts(run_dir, "mention Rogaland relocation")
            self.assertIsNotNone(path)
            assert path is not None
            self.assertEqual(path.name, APPLY_PROMPTS_FILENAME)
            self.assertEqual(read_apply_prompts(run_dir), "mention Rogaland relocation")

    def test_write_empty_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            self.assertIsNone(write_apply_prompts(run_dir, "   "))

    def test_markdown_section_empty_when_blank(self) -> None:
        self.assertEqual(apply_prompts_markdown_section(""), "")

    def test_normalize_apply_language_defaults_to_en(self) -> None:
        self.assertEqual(normalize_apply_language(None), "en")
        self.assertEqual(normalize_apply_language("bogus"), "en")

    def test_resolve_apply_language_inherit_or_override(self) -> None:
        self.assertEqual(resolve_apply_language("en", "inherit"), "en")
        self.assertEqual(resolve_apply_language("en", "no"), "no")
        self.assertEqual(resolve_apply_language("no", "inherit"), "no")
        self.assertEqual(resolve_apply_language("no", "en"), "en")

    def test_apply_language_markdown_section_notes_norwegian(self) -> None:
        section = apply_language_markdown_section("no")
        self.assertIn("Norwegian (Bokmål)", section)
        self.assertIn("final_cv_no.md", section)

    def test_run_cv_tailoring_writes_apply_prompts_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            cmd = [
                sys.executable,
                "-m",
                "cv_generation.run_cv_tailoring",
                "--job-file",
                str(JOB_FILE),
                "--company",
                "Northline Labs",
                "--role",
                "ML Engineer",
                "--run-dir",
                str(run_dir),
                "--force",
                "--apply-prompts",
                "emphasize Python pipelines",
            ]
            subprocess.run(cmd, cwd=REPO, check=True, capture_output=True, text=True)
            self.assertEqual(read_apply_prompts(run_dir), "emphasize Python pipelines")
            task = (run_dir / "04_bullet_tailor_task.json").read_text(encoding="utf-8")
            self.assertIn("emphasize Python pipelines", task)
            artifacts = (run_dir / "application_artifacts.md").read_text(encoding="utf-8")
            self.assertIn("User tailoring instructions", artifacts)

    def test_run_cv_tailoring_stores_output_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "cv_generation.run_cv_tailoring",
                    "--job-file",
                    str(JOB_FILE),
                    "--company",
                    "Northline Labs",
                    "--role",
                    "ML Engineer",
                    "--run-dir",
                    str(run_dir),
                    "--force",
                    "--output-language",
                    "no",
                ],
                cwd=REPO,
                check=True,
                capture_output=True,
                text=True,
            )
            task = (run_dir / "01_jd_parser_task.json").read_text(encoding="utf-8")
            self.assertIn('"output_language": "no"', task)
            artifacts = (run_dir / "application_artifacts.md").read_text(encoding="utf-8")
            self.assertIn("Application language", artifacts)
            self.assertIn("Norwegian (Bokmål)", artifacts)


if __name__ == "__main__":
    unittest.main()
