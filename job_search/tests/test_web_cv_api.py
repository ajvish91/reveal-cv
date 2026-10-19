"""API tests for the CVs page (fake markdown in-repo, mapping outside)."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from repo_paths import REPO_ROOT, SHARED_DIR
from shared.cv_loader import _load_default_profiles_cached


class TestWebCvApi(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.cv_dir = Path(self.tmp.name) / "cv"
        self.cv_dir.mkdir()
        self.private_dir = Path(self.tmp.name) / "private-cv"
        self.private_dir.mkdir()
        for name in ("industry.demo.md", "academic.demo.md"):
            shutil.copy(SHARED_DIR / "cv" / name, self.cv_dir / name)
        (self.cv_dir / "industry.md").write_text(
            "---\ntrack: industry\nkeywords: [kept]\n---\n\n# Industry CV\n\n## Name\n\nMITCH EVANS\n",
            encoding="utf-8",
        )
        self.env = patch.dict(
            os.environ,
            {
                "CV_SOURCE_DIR": str(self.cv_dir),
                "CV_PRIVATE_DIR": str(self.private_dir),
                "JOBS_DB": str(Path(self.tmp.name) / "jobs.sqlite"),
            },
        )
        self.env.start()
        _load_default_profiles_cached.cache_clear()
        from fastapi.testclient import TestClient

        from job_search.web.app import app

        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.env.stop()
        _load_default_profiles_cached.cache_clear()
        self.tmp.cleanup()

    def test_cv_page_and_sources(self) -> None:
        page = self.client.get("/cv")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Fill both columns", page.text)
        self.assertIn("mapping JSON", page.text)
        data = self.client.get("/api/cv/sources").json()
        ids = [s["id"] for s in data["tracks"]["industry"]["sources"]]
        self.assertIn("demo", ids)
        self.assertIn("personal", ids)

    def test_save_user_cv_strips_real_and_leaves_personal(self) -> None:
        original = (self.cv_dir / "industry.md").read_text(encoding="utf-8")
        res = self.client.post(
            "/api/cv",
            json={
                "slug": "extra-cv",
                "identity": {
                    "name": {"fake": "RIVER STONE", "real": "Secret Name"},
                    "email": {"fake": "river@example.com", "real": "secret@example.com"},
                    "github_url": {"fake": "https://github.com/cv-placeholder", "real": "https://github.com/secret"},
                },
                "industry": {
                    "profile": "Fake profile text.",
                    "skills": ["Python"],
                    "keywords": ["python"],
                    "experience": [
                        {
                            "title": "Engineer",
                            "employer": {"fake": "Northline Labs", "real": "Secret Corp"},
                            "dates": {"fake": "2022 - 2024", "real": "2020 - 2024"},
                            "bullets": ["Did fake work."],
                        }
                    ],
                    "education": [],
                    "publications": [],
                },
                "academic": {
                    "profile": "Academic summary.",
                    "skills": ["Python"],
                    "keywords": ["research"],
                    "experience": [],
                    "education": [],
                    "publications": [],
                    "teaching": "",
                },
                "activate": {"industry": True, "academic": False},
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        payload = res.json()
        self.assertEqual(payload["source_id"], "user:extra-cv")
        written = (self.cv_dir / "user" / "extra-cv-industry.md").read_text(encoding="utf-8")
        self.assertIn("RIVER STONE", written)
        self.assertNotIn("Secret Name", written)
        self.assertNotIn("Secret Corp", written)
        self.assertNotIn("secret@example.com", written)
        self.assertEqual((self.cv_dir / "industry.md").read_text(encoding="utf-8"), original)
        doc = self.client.get("/api/cv/document?source_id=user:extra-cv").json()
        self.assertEqual(doc["identity"]["name"]["fake"], "RIVER STONE")
        self.assertNotIn("real", doc["identity"]["name"])
        self.assertNotIn("Secret Name", str(doc))

    def test_refuses_demo_write(self) -> None:
        res = self.client.post(
            "/api/cv",
            json={
                "source_id": "demo",
                "identity": {"name": {"fake": "X"}},
                "industry": {"profile": "nope", "experience": [], "education": []},
            },
        )
        self.assertEqual(res.status_code, 400)
        demo = (self.cv_dir / "industry.demo.md").read_text(encoding="utf-8")
        self.assertIn("ALEX RIVERA", demo)

    def test_activate_and_blank(self) -> None:
        self.client.post(
            "/api/cv",
            json={
                "slug": "second",
                "identity": {"name": {"fake": "CASEY LAKE"}},
                "industry": {"profile": "p", "experience": [], "education": [], "keywords": ["x"]},
            },
        )
        res = self.client.post("/api/cv/activate", json={"track": "industry", "source_id": "user:second"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["active"]["industry"], "user:second")
        blank = self.client.get("/api/cv/blank").json()
        self.assertEqual(blank["kind"], "new")
        self.assertIn("cv-placeholder", blank["identity"]["github_url"]["fake"])

    def test_save_mapping_outside_repo(self) -> None:
        res = self.client.post(
            "/api/cv/save-mapping",
            json={"mapping": {"RIVER STONE": "Secret Name", "_github_url": "https://github.com/secret"}},
        )
        self.assertEqual(res.status_code, 200, res.text)
        saved = Path(res.json()["path"])
        self.assertTrue(saved.is_file())
        self.assertNotIn(str(REPO_ROOT.resolve()), str(saved.resolve()))
        text = saved.read_text(encoding="utf-8")
        self.assertIn("Secret Name", text)

    def test_save_mapping_rejects_repo_path(self) -> None:
        from cv_generation.private_cv import PrivateConfig
        from job_search.web import cv_sources

        cfg = PrivateConfig(
            repo_root=REPO_ROOT,
            cv_package_dir=REPO_ROOT / "cv_generation",
            private_dir=REPO_ROOT,
            mapping_file=REPO_ROOT / "cv_identity_mapping.json",
            output_dir=REPO_ROOT / "out",
            profile_photo=REPO_ROOT / "photo.jpg",
        )
        with patch.object(cv_sources, "mapping_path_outside_repo", side_effect=ValueError("inside")):
            with patch("cv_generation.private_cv.load_config", return_value=cfg):
                res = self.client.post("/api/cv/save-mapping", json={"mapping": {"A": "B"}})
        self.assertEqual(res.status_code, 400)
        self.assertFalse((REPO_ROOT / "cv_identity_mapping.json").exists())


if __name__ == "__main__":
    unittest.main()
