from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from repo_paths import SHARED_DIR
from shared.cv_loader import _load_default_profiles_cached, load_default_profiles
from shared.cv_registry import (
    list_sources,
    save_registry,
    set_active,
    write_user_markdown,
)


class TestCvRegistryLoader(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        demo_src = SHARED_DIR / "cv"
        for name in ("industry.demo.md", "academic.demo.md"):
            (self.root / name).write_text((demo_src / name).read_text(encoding="utf-8"), encoding="utf-8")
        (self.root / "industry.md").write_text(
            "---\ntrack: industry\nkeywords: [local]\n---\n\n# Industry CV\n\n## Name\n\nMITCH EVANS\n",
            encoding="utf-8",
        )
        (self.root / "academic.md").write_text(
            "---\ntrack: academic\nkeywords: [local]\n---\n\n# Academic CV\n\n## Summary\n\nLocal academic.\n",
            encoding="utf-8",
        )
        self.env = patch.dict(os.environ, {"CV_SOURCE_DIR": str(self.root)})
        self.env.start()
        _load_default_profiles_cached.cache_clear()

    def tearDown(self) -> None:
        self.env.stop()
        _load_default_profiles_cached.cache_clear()
        self.tmp.cleanup()

    def test_default_prefers_personal_over_demo(self) -> None:
        profiles = load_default_profiles()
        by_track = {p.track: p for p in profiles}
        self.assertIn("MITCH EVANS", by_track["industry"].body_markdown)
        self.assertTrue(by_track["industry"].source_path.name.endswith("industry.md"))

    def test_activate_user_cv_does_not_overwrite_personal(self) -> None:
        original = (self.root / "industry.md").read_text(encoding="utf-8")
        write_user_markdown(
            "extra",
            "industry",
            "---\ntrack: industry\nkeywords: [extra]\n---\n\n# Industry CV\n\n## Name\n\nRIVER STONE\n",
            self.root,
        )
        set_active("industry", "user:extra", self.root)
        _load_default_profiles_cached.cache_clear()
        profiles = load_default_profiles()
        industry = next(p for p in profiles if p.track == "industry")
        self.assertIn("RIVER STONE", industry.body_markdown)
        self.assertEqual((self.root / "industry.md").read_text(encoding="utf-8"), original)
        ids = [s.source_id for s in list_sources("industry", self.root)]
        self.assertIn("personal", ids)
        self.assertIn("user:extra", ids)
        self.assertIn("demo", ids)

    def test_save_registry_refuses_nothing_on_personal_file(self) -> None:
        save_registry({"active": {"industry": "demo"}}, self.root)
        _load_default_profiles_cached.cache_clear()
        profiles = load_default_profiles()
        industry = next(p for p in profiles if p.track == "industry")
        self.assertTrue(industry.source_path.name.endswith(".demo.md"))
        self.assertTrue((self.root / "industry.md").is_file())


if __name__ == "__main__":
    unittest.main()
