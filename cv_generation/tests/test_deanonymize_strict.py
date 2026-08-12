"""--strict must fail only on leftover placeholders, not unused mapping keys."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.cv_application_artifacts import normalize_upper_name_variants
from cv_generation.deanonymize_cvs import apply_replacements


class TestStrictUnusedKeys(unittest.TestCase):
    def test_title_case_alias_is_unmatched_when_cv_uses_all_caps(self) -> None:
        mapping = normalize_upper_name_variants({"ALEX RIVERA": "Jane Doe", "Northline Labs": "Acme"})
        text = "# ALEX RIVERA\nNorthline Labs\n"
        _, counts = apply_replacements(text, mapping)
        unmatched = set(mapping) - set(counts)
        self.assertIn("Alex Rivera", unmatched)

    def test_strict_passes_with_unused_alias_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping_path = root / "mapping.json"
            mapping_path.write_text(
                json.dumps(
                    {
                        "ALEX RIVERA": "Jane Doe",
                        "Northline Labs": "Acme Corp",
                        # Academic-only key absent from this industry CV
                        "Example Publication One": "Real Paper (2022).",
                    }
                ),
                encoding="utf-8",
            )
            run = root / "run"
            run.mkdir()
            (run / "final_cv.md").write_text(
                "# ALEX RIVERA\nWorked at Northline Labs\n",
                encoding="utf-8",
            )
            out = root / "out"
            cmd = [
                sys.executable,
                "-m",
                "cv_generation.deanonymize_cvs",
                "--mapping",
                str(mapping_path),
                "--input-dir",
                str(run),
                "--glob",
                "final_cv.md",
                "--output-dir",
                str(out),
                "--strict",
            ]
            proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
            self.assertEqual(
                proc.returncode,
                0,
                msg=f"stdout={proc.stdout}\nstderr={proc.stderr}",
            )
            written = (out / "final_cv.md").read_text(encoding="utf-8")
            self.assertIn("Jane Doe", written)
            self.assertNotIn("ALEX RIVERA", written)
            self.assertIn("informational", proc.stderr.lower())

    def test_strict_fails_when_placeholder_remains(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping_path = root / "mapping.json"
            # Name is filled; employer value is still a template → leftover in output.
            mapping_path.write_text(
                json.dumps(
                    {
                        "ALEX RIVERA": "Jane Doe",
                        "Northline Labs": "REPLACE_WITH_EMPLOYER_1",
                    }
                ),
                encoding="utf-8",
            )
            run = root / "run"
            run.mkdir()
            (run / "final_cv.md").write_text(
                "# ALEX RIVERA\nStill has Northline Labs\n",
                encoding="utf-8",
            )
            out = root / "out"
            cmd = [
                sys.executable,
                "-m",
                "cv_generation.deanonymize_cvs",
                "--mapping",
                str(mapping_path),
                "--input-dir",
                str(run),
                "--glob",
                "final_cv.md",
                "--output-dir",
                str(out),
                "--strict",
            ]
            proc = subprocess.run(cmd, cwd=str(REPO), capture_output=True, text=True)
            self.assertEqual(proc.returncode, 4, msg=f"stderr={proc.stderr}")
            self.assertIn("incomplete", proc.stderr.lower())


if __name__ == "__main__":
    unittest.main()
