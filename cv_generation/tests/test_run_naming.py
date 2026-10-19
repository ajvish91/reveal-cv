"""Tests for run folder naming and deanonymize output enrichment."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.private_cv import PrivateConfig, resolve_deanon_output_dir, resolve_run_dir
from cv_generation.run_naming import (
    enrich_run_folder_name,
    find_repo_run_by_timestamp,
    folder_includes_company,
    parse_run_folder_basename,
    resolve_company_for_folder,
    run_folder_name,
)
from cv_generation.run_cv_tailoring import main as run_cv_tailoring_main


FIXTURES = Path(__file__).resolve().parent / "fixtures"


class TestRunNaming(unittest.TestCase):
    def test_run_folder_name_includes_company(self) -> None:
        name = run_folder_name("20260601T122139Z", "Senior AI Platform Engineer", "Storebrand")
        self.assertEqual(name, "20260601T122139Z_Storebrand_senior-ai-platform-engineer")

    def test_parse_legacy_folder_without_company(self) -> None:
        ts, company, role = parse_run_folder_basename("20260528T113852Z_ml-ai-engineer")
        self.assertEqual(ts, "20260528T113852Z")
        self.assertIsNone(company)
        self.assertEqual(role, "ml-ai-engineer")
        self.assertFalse(folder_includes_company("20260528T113852Z_ml-ai-engineer"))

    def test_parse_folder_with_company(self) -> None:
        ts, company, role = parse_run_folder_basename(
            "20260713T095418Z_Falkor_software-ai-engineer"
        )
        self.assertEqual(ts, "20260713T095418Z")
        self.assertEqual(company, "Falkor")
        self.assertEqual(role, "software-ai-engineer")
        self.assertTrue(folder_includes_company("20260713T095418Z_Falkor_software-ai-engineer"))

    def test_enrich_legacy_run_from_parser_json(self) -> None:
        run_dir = FIXTURES / "legacy_run_no_company"
        enriched = enrich_run_folder_name("20260528T113852Z_ml-ai-engineer", run_dir)
        self.assertEqual(
            enriched,
            "20260528T113852Z_PianoSoftwareNorway_ml-ai-engineer",
        )

    def test_enrich_preserves_existing_company_segment(self) -> None:
        run_dir = FIXTURES / "legacy_run_no_company"
        existing = "20260713T095418Z_Falkor_software-ai-engineer"
        self.assertEqual(enrich_run_folder_name(existing, run_dir), existing)

    def test_resolve_company_from_job_posting(self) -> None:
        text = "Role: ML Engineer\nCompany: Piano Software Norway\n"
        self.assertEqual(
            resolve_company_for_folder(company_arg="", job_text=text),
            "Piano Software Norway",
        )
        self.assertEqual(
            resolve_company_for_folder(company_arg="Acme", job_text=text),
            "Acme",
        )

    def test_find_repo_run_by_timestamp_from_enriched_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runs_root = Path(tmp)
            legacy = runs_root / "20260528T113852Z_ml-ai-engineer"
            legacy.mkdir()
            (legacy / "final_cv.md").write_text("# CV\n", encoding="utf-8")
            found = find_repo_run_by_timestamp(
                runs_root,
                "20260528T113852Z_PianoSoftwareNorway_ml-ai-engineer",
            )
            self.assertEqual(found, legacy)


class TestRunCvTailoringFolderName(unittest.TestCase):
    def test_run_cv_tailoring_derives_company_from_job_posting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job = root / "job.txt"
            job.write_text(
                "Role: ML/AI Engineer\nCompany: Piano Software Norway\n\nAbout the role:\n",
                encoding="utf-8",
            )
            runs = root / "cv_runs"
            runs.mkdir()
            module = sys.modules["cv_generation.run_cv_tailoring"]
            original_runs = module.RUNS_DIR
            module.RUNS_DIR = runs
            try:
                argv = sys.argv
                sys.argv = [
                    "run_cv_tailoring",
                    "--job-file",
                    str(job),
                    "--role",
                    "ML/AI Engineer",
                ]
                try:
                    code = run_cv_tailoring_main()
                finally:
                    sys.argv = argv
                self.assertEqual(code, 0)
                created = next(p for p in runs.iterdir() if p.is_dir())
                self.assertTrue(folder_includes_company(created.name))
                self.assertIn("PianoSoftwareNorway", created.name)
            finally:
                module.RUNS_DIR = original_runs


class TestPrivateCvDeanonOutput(unittest.TestCase):
    def test_resolve_deanon_output_dir_enriches_legacy_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            priv = root / "private"
            run_dir = repo / "cv_generation" / "cv_runs" / "20260528T113852Z_ml-ai-engineer"
            run_dir.mkdir(parents=True)
            (run_dir / "final_cv.md").write_text("# CV\n", encoding="utf-8")
            fixture = FIXTURES / "legacy_run_no_company" / "01_jd_parser_output.json"
            (run_dir / "01_jd_parser_output.json").write_text(
                fixture.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (run_dir / "job_posting.txt").write_text(
                "Company: Piano Software Norway\nRole: ML/AI Engineer\n",
                encoding="utf-8",
            )

            cfg = PrivateConfig(
                repo_root=repo,
                cv_package_dir=repo / "cv_generation",
                private_dir=priv,
                mapping_file=priv / "cv_identity_mapping.json",
                output_dir=priv / "deanonymized",
                profile_photo=priv / "profile_photo.jpg",
            )
            out = resolve_deanon_output_dir(
                cfg,
                run_dir,
                "20260528T113852Z_ml-ai-engineer",
                announce=False,
            )
            self.assertEqual(
                out.name,
                "20260528T113852Z_PianoSoftwareNorway_ml-ai-engineer",
            )

    def test_resolve_run_dir_finds_legacy_run_from_enriched_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "repo"
            priv = root / "private"
            legacy = repo / "cv_generation" / "cv_runs" / "20260528T113852Z_ml-ai-engineer"
            legacy.mkdir(parents=True)
            (legacy / "final_cv.md").write_text("# CV\n", encoding="utf-8")

            cfg = PrivateConfig(
                repo_root=repo,
                cv_package_dir=repo / "cv_generation",
                private_dir=priv,
                mapping_file=priv / "cv_identity_mapping.json",
                output_dir=priv / "deanonymized",
                profile_photo=priv / "profile_photo.jpg",
            )
            resolved, run_id = resolve_run_dir(
                cfg,
                "20260528T113852Z_PianoSoftwareNorway_ml-ai-engineer",
            )
            self.assertEqual(resolved, legacy)
            self.assertEqual(run_id, "20260528T113852Z_ml-ai-engineer")


if __name__ == "__main__":
    unittest.main()
