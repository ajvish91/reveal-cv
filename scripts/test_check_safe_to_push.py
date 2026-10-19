"""Regression tests for the public-repo push scanner."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from repo_paths import REPO_ROOT

_SCANNER = REPO_ROOT / "scripts" / "check_safe_to_push.py"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("check_safe_to_push", _SCANNER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestCheckSafeToPush(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_scanner()

    def test_scanner_source_has_no_personal_identity(self) -> None:
        text = _SCANNER.read_text(encoding="utf-8")
        # Real identifiers belong in .privacy_patterns.local, not in published code.
        forbidden = (
            "Jane" + "Doe",
            "example" + ".edu",
            "/Users/" + "someuser",
            r"\bJD" + r"\b",
        )
        for fragment in forbidden:
            self.assertNotIn(fragment, text)

    def test_jobs_and_docs_are_not_prefix_skipped(self) -> None:
        prefixes = self.mod.SKIP_REL_PREFIXES
        self.assertNotIn("cv_generation/jobs/", prefixes)
        self.assertNotIn("docs/", prefixes)

    def test_tracked_demo_posting_is_scanned(self) -> None:
        demo = REPO_ROOT / "cv_generation" / "jobs" / "demo_northline_ml_engineer.txt"
        self.assertTrue(demo.is_file())
        self.assertTrue(self.mod.should_scan(demo))

    def test_gitignored_real_cv_is_not_scanned(self) -> None:
        academic = REPO_ROOT / "shared" / "cv" / "academic.md"
        self.assertFalse(self.mod.should_scan(academic))

    def test_select_files_uses_git_tracked_list(self) -> None:
        selected = {p.resolve() for p in self.mod.select_files(["cv_generation"])}
        demo = (REPO_ROOT / "cv_generation" / "jobs" / "demo_northline_ml_engineer.txt").resolve()
        self.assertIn(demo, selected)
        jobs_dir = REPO_ROOT / "cv_generation" / "jobs"
        if jobs_dir.is_dir():
            for extra in jobs_dir.glob("*"):
                if extra.name != "demo_northline_ml_engineer.txt" and extra.is_file():
                    self.assertNotIn(extra.resolve(), selected)

    def test_home_dir_path_flags_real_usernames_not_placeholders(self) -> None:
        pat = dict(self.mod.SENSITIVE_PATTERNS)["home_dir_path"]
        self.assertIsNotNone(pat.search("/Users/" + "someuser/secret"))
        self.assertIsNone(pat.search("/Users/you/private/cv/cv"))
        self.assertIsNone(pat.search("/Users/me/Job Applications"))
        self.assertIsNone(pat.search("/Users/<your-username>/x"))

    def test_local_patterns_file_is_optional(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"
            self.mod.LOCAL_PATTERN_FILE = missing
            self.assertEqual(self.mod.load_local_patterns(), [])


if __name__ == "__main__":
    unittest.main()
