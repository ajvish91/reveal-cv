"""Tests for automated cover letter generation."""
from __future__ import annotations

import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.agent_providers import AgentRunResult
from cv_generation.cover_letter_generator import (
    COVER_LETTER_FILENAME,
    build_cover_letter_prompt,
    is_cover_letter_required,
    maybe_generate_cover_letter,
    resolve_track,
)
from cv_generation.pipeline_metrics import PipelineMetricsCollector

INTILITY_RUN = (
    REPO
    / "cv_generation"
    / "cv_runs"
    / "20260714T113347Z_Intility_developer-software-engineer"
)


class TestCoverLetterGenerator(unittest.TestCase):
    def setUp(self) -> None:
        if not INTILITY_RUN.is_dir():
            self.skipTest("Intility fixture run not present")

    def _copy_fixture(self, tmp: Path) -> Path:
        run_dir = tmp / INTILITY_RUN.name
        shutil.copytree(INTILITY_RUN, run_dir)
        cover = run_dir / COVER_LETTER_FILENAME
        if cover.is_file():
            cover.unlink()
        cover_pdf = run_dir / "cover_letter.pdf"
        if cover_pdf.is_file():
            cover_pdf.unlink()
        return run_dir

    def test_intility_fixture_requires_cover_letter(self) -> None:
        track = resolve_track(INTILITY_RUN)
        self.assertEqual(track, "industry")
        self.assertTrue(is_cover_letter_required(INTILITY_RUN, track=track))

    def test_build_prompt_includes_voice_and_cv(self) -> None:
        final_cv = (INTILITY_RUN / "final_cv.md").read_text(encoding="utf-8")
        prompt = build_cover_letter_prompt(
            role_title="Developer / Software Engineer",
            company="Intility",
            job_posting=(INTILITY_RUN / "job_posting.txt").read_text(encoding="utf-8"),
            final_cv_markdown=final_cv,
            user_apply_prompts="Cater it to software engineering",
        )
        payload = json.loads(prompt)
        self.assertIn("voice_rules", payload)
        self.assertIn("final_cv_markdown", payload)
        self.assertEqual(payload["user_apply_prompts"], "Cater it to software engineering")
        self.assertIn("markdown only", payload["instruction"])

    def test_build_prompt_norwegian_includes_localization_hint(self) -> None:
        final_cv = (INTILITY_RUN / "final_cv.md").read_text(encoding="utf-8")
        prompt = build_cover_letter_prompt(
            role_title="Developer / Software Engineer",
            company="Intility",
            job_posting=(INTILITY_RUN / "job_posting.txt").read_text(encoding="utf-8"),
            final_cv_markdown=final_cv,
            output_language="no",
        )
        payload = json.loads(prompt)
        self.assertEqual(payload["output_language"], "no")
        self.assertIn("localization_note", payload)
        self.assertIn("250", payload["localization_note"])
        self.assertIn("350", payload["localization_note"])
        self.assertIn("personality", payload["localization_note"].lower())
        self.assertIn("Norwegian B1", payload["instruction"])

    def test_dry_run_prints_prompt_without_writing_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._copy_fixture(Path(tmp))
            result = maybe_generate_cover_letter(
                run_dir,
                provider_name="cursor",
                model="composer-2.5",
                dry_run=True,
            )
            self.assertFalse(result.generated)
            self.assertEqual(result.skipped_reason, "dry-run")
            self.assertFalse((run_dir / COVER_LETTER_FILENAME).is_file())

    def test_mock_provider_writes_cover_letter(self) -> None:
        import tempfile

        sample_letter = (
            "MITCH EVANS\n\n**Re: Developer / Software Engineer**\n\n"
            "Dear Hiring Team,\n\nBody paragraph one.\n\nBody paragraph two.\n\n"
            "Body paragraph three.\n\nBody paragraph four.\n\n"
            "Thank you for considering my application.\n\nSincerely,\n\nMITCH EVANS\n"
        )

        def fake_run_markdown(prompt: str, *, model: str, cwd=None) -> AgentRunResult:
            return AgentRunResult(text=sample_letter, provider="cursor", model=model)

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._copy_fixture(Path(tmp))
            collector = PipelineMetricsCollector(provider="cursor", model="composer-2.5")
            with patch(
                "cv_generation.cover_letter_generator.get_provider"
            ) as mock_get_provider:
                mock_provider = mock_get_provider.return_value
                mock_provider.run_markdown.side_effect = fake_run_markdown
                result = maybe_generate_cover_letter(
                    run_dir,
                    provider_name="cursor",
                    model="composer-2.5",
                    metrics=collector,
                )
            self.assertTrue(result.generated)
            written = (run_dir / COVER_LETTER_FILENAME).read_text(encoding="utf-8")
            self.assertIn("MITCH EVANS", written)
            self.assertIn("Dear Hiring Team", written)
            metrics = collector.finalize()
            stage_names = [stage.name for stage in metrics.stages]
            self.assertIn("07_cover_letter", stage_names)

    def test_mock_provider_routes_norwegian_to_cover_letter_no(self) -> None:
        import tempfile

        sample_letter = (
            "MITCH EVANS\n\n**Ang: Utvikler**\n\n"
            "Jeg søker stillingen fordi arbeidet passer.\n\n"
            "Med vennlig hilsen,\n\nMITCH EVANS\n"
        )

        def fake_run_markdown(prompt: str, *, model: str, cwd=None) -> AgentRunResult:
            return AgentRunResult(text=sample_letter, provider="cursor", model=model)

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._copy_fixture(Path(tmp))
            with patch(
                "cv_generation.cover_letter_generator.get_provider"
            ) as mock_get_provider:
                mock_provider = mock_get_provider.return_value
                mock_provider.run_markdown.side_effect = fake_run_markdown
                result = maybe_generate_cover_letter(
                    run_dir,
                    provider_name="cursor",
                    model="composer-2.5",
                    no_pdf=True,
                )
            self.assertTrue(result.generated)
            self.assertTrue(result.wrote_norwegian_direct)
            self.assertFalse((run_dir / COVER_LETTER_FILENAME).is_file())
            self.assertTrue((run_dir / "cover_letter_no.md").is_file())
            self.assertIn("Jeg søker", (run_dir / "cover_letter_no.md").read_text())

    def test_build_prompt_english_requires_english_even_for_norwegian_jd(self) -> None:
        final_cv = (INTILITY_RUN / "final_cv.md").read_text(encoding="utf-8")
        prompt = build_cover_letter_prompt(
            role_title="KI-ingeniør",
            company="Forsvaret",
            job_posting="Norsk stillingsannonse med mange ord.",
            final_cv_markdown=final_cv,
            output_language="en",
        )
        payload = json.loads(prompt)
        self.assertIn("entirely in English", payload["instruction"])

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._copy_fixture(Path(tmp))
            existing = run_dir / COVER_LETTER_FILENAME
            existing.write_text("# Existing letter\n", encoding="utf-8")
            result = maybe_generate_cover_letter(
                run_dir,
                provider_name="cursor",
                model="composer-2.5",
            )
            self.assertFalse(result.generated)
            self.assertEqual(result.skipped_reason, "already exists")
            self.assertEqual(existing.read_text(encoding="utf-8"), "# Existing letter\n")

    def test_skips_for_academic_track(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self._copy_fixture(Path(tmp))
            track_path = run_dir / "03_track_selector_output.json"
            track_data = json.loads(track_path.read_text(encoding="utf-8"))
            track_data["selected_track"] = "academic"
            track_path.write_text(json.dumps(track_data, indent=2) + "\n", encoding="utf-8")
            self.assertFalse(is_cover_letter_required(run_dir, track="academic"))
            result = maybe_generate_cover_letter(
                run_dir,
                provider_name="cursor",
                model="composer-2.5",
            )
            self.assertFalse(result.generated)
            self.assertIn("academic", result.skipped_reason or "")


if __name__ == "__main__":
    unittest.main()
