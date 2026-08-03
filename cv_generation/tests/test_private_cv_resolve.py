"""Resolve run folders for private_cv apply (repo source vs deanonymized output)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.private_cv import PrivateConfig, _prefer_repo_run_source, resolve_run_dir


class TestResolveRunDir(unittest.TestCase):
    def test_deanonymized_output_redirects_to_repo_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            priv = root / "private"
            runs = repo / "cv_generation" / "cv_runs" / "demo_run"
            deanon = priv / "deanonymized" / "demo_run"
            runs.mkdir(parents=True)
            deanon.mkdir(parents=True)
            (runs / "final_cv.md").write_text("# CV\n", encoding="utf-8")
            (runs / "cover_letter_no.md").write_text("no\n", encoding="utf-8")
            (deanon / "final_cv.md").write_text("# Deanon CV\n", encoding="utf-8")

            cfg = PrivateConfig(
                repo_root=repo,
                cv_package_dir=repo / "cv_generation",
                private_dir=priv,
                mapping_file=priv / "cv_identity_mapping.json",
                output_dir=deanon.parent,
                profile_photo=priv / "profile_photo.jpg",
            )
            resolved, run_id = _prefer_repo_run_source(cfg, deanon, "demo_run")
            self.assertEqual(run_id, "demo_run")
            self.assertEqual(resolved, runs)
            self.assertTrue((resolved / "cover_letter_no.md").is_file())

    def test_resolve_run_id_uses_repo_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            priv = root / "private"
            runs = repo / "cv_generation" / "cv_runs" / "demo_run"
            runs.mkdir(parents=True)
            (runs / "final_cv.md").write_text("# CV\n", encoding="utf-8")

            cfg = PrivateConfig(
                repo_root=repo,
                cv_package_dir=repo / "cv_generation",
                private_dir=priv,
                mapping_file=priv / "cv_identity_mapping.json",
                output_dir=priv / "deanonymized",
                profile_photo=priv / "profile_photo.jpg",
            )
            resolved, run_id = resolve_run_dir(cfg, "demo_run")
            self.assertEqual(resolved, runs)
            self.assertEqual(run_id, "demo_run")


if __name__ == "__main__":
    unittest.main()
