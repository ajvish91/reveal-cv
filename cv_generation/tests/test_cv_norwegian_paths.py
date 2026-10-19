"""Norwegian localization must write *_no.md and never replace English sources."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.agent_providers import AgentRunResult
from cv_generation.cv_norwegian import (
    looks_like_norwegian_cover_letter,
    looks_like_norwegian_cv,
    localize_run,
)


class TestNorwegianPathGuards(unittest.TestCase):
    def test_looks_like_norwegian_cv(self) -> None:
        self.assertTrue(looks_like_norwegian_cv("# Bransje-CV\n\n## Navn\n\nMITCH\n"))
        self.assertFalse(looks_like_norwegian_cv("# Industry CV\n\n## Name\n\nMITCH\n"))
        self.assertFalse(looks_like_norwegian_cv("# Industry CV\n\n## Profile\n\nText\n"))

    def test_looks_like_norwegian_cover_letter(self) -> None:
        self.assertTrue(
            looks_like_norwegian_cover_letter(
                "MITCH\n\n**Ang: Rolle**\n\nJeg søker stillingen fordi arbeidet passer.\n"
            )
        )
        self.assertFalse(
            looks_like_norwegian_cover_letter(
                "MITCH\n\n**Re: Role**\n\nI am applying because the work fits.\n"
            )
        )

    def test_localize_writes_final_cv_no_and_restores_english_source(self) -> None:
        english = "# Industry CV\n\n## Name\n\nMITCH EVANS\n\n## Profile\n\nHello.\n"
        norwegian = "# Bransje-CV\n\n## Navn\n\nMITCH EVANS\n\n## Profil\n\nHei.\n"

        def fake_run(prompt: str, *, model: str, cwd=None) -> AgentRunResult:
            # Simulate a local agent that wrongly overwrites final_cv.md.
            run_dir = Path(cwd) if cwd else Path.cwd()
            # cwd may be repo root; find the temp run via prompt content is hard —
            # write via the open file we know from the test closure.
            src.write_text(norwegian, encoding="utf-8")
            return AgentRunResult(text=norwegian, provider="cursor", model=model)

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            src = run_dir / "final_cv.md"
            src.write_text(english, encoding="utf-8")
            with patch("cv_generation.cv_norwegian.get_provider") as mock_get:
                mock_get.return_value.run.side_effect = fake_run
                code = localize_run(
                    run_dir,
                    artifacts=("cv",),
                    provider="cursor",
                    model="composer-2.5",
                    no_pdf=True,
                )
            self.assertEqual(code, 0)
            self.assertEqual(src.read_text(encoding="utf-8"), english)
            self.assertTrue((run_dir / "final_cv_no.md").is_file())
            self.assertTrue(looks_like_norwegian_cv((run_dir / "final_cv_no.md").read_text()))

    def test_localize_moves_norwegian_cover_letter_to_no_suffix(self) -> None:
        norwegian_letter = (
            "MITCH EVANS\n\n**Ang: Rolle**\n\n"
            "Jeg søker stillingen fordi arbeidet passer godt.\n\n"
            "Med vennlig hilsen,\n\nMITCH EVANS\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            (run_dir / "cover_letter.md").write_text(norwegian_letter, encoding="utf-8")
            code = localize_run(
                run_dir,
                artifacts=("cover-letter",),
                provider="cursor",
                model="composer-2.5",
                no_pdf=True,
            )
            self.assertEqual(code, 0)
            self.assertFalse((run_dir / "cover_letter.md").is_file())
            no_path = run_dir / "cover_letter_no.md"
            self.assertTrue(no_path.is_file())
            self.assertIn("Jeg søker", no_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
