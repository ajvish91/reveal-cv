from __future__ import annotations

import unittest
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from repo_paths import SHARED_DIR
from shared.cv_form import (
    assemble_markdown,
    blank_identity,
    mapping_from_form,
    parse_identity_and_track,
    paired,
    strip_real_values,
)


class TestCvForm(unittest.TestCase):
    def test_round_trip_industry_fields(self) -> None:
        identity = {
            "name": paired("ALEX RIVERA", "Jane Doe"),
            "date_of_birth": paired("01 Jan 1990", "02 Feb 1991"),
            "email": paired("demo.candidate@example.com", "jane@example.com"),
            "phone": paired("+00-000-000-0000", "+47-000-00-000"),
            "location": paired("Example City, Example Country", "Stavanger, Norway"),
            "work_permit": paired("Example work authorization status", "Permanent residence"),
            "github_url": paired("https://github.com/cv-placeholder", "https://github.com/jane"),
            "linkedin_url": paired("https://linkedin.com/in/cv-placeholder", "https://linkedin.com/in/jane"),
            "scholar_url": paired(),
            "orcid_url": paired(),
            "languages": [{"name": paired("English", "English"), "level": paired("Fluent", "Fluent")}],
            "hobbies": [paired("Reading", "Reading")],
            "locations_preferred": [paired("Example Region", "Rogaland")],
            "seniority_years": 8,
        }
        track = {
            "profile": "Software engineer with eight years in machine learning.",
            "skills": ["Python", "PyTorch"],
            "keywords": ["machine learning", "python"],
            "experience": [
                {
                    "title": "ML Engineer",
                    "employer": paired("Northline Labs", "Real Labs"),
                    "dates": paired("Jan 2022 - Aug 2024", "Mar 2022 - Sep 2024"),
                    "bullets": ["Built document classification pipelines."],
                }
            ],
            "education": [
                {
                    "degree": "Ph.D.",
                    "school": paired("Example Institute of Technology", "Real University"),
                    "years": paired("2020 - 2023", "2019 - 2023"),
                    "field": "Information Technology",
                    "thesis": paired("Example thesis on trustworthy automation", "Real thesis title"),
                }
            ],
            "publications": ["Example Publication One (Example Conference 2022)."],
        }
        markdown = assemble_markdown(identity, track, "industry")
        self.assertIn("ALEX RIVERA", markdown)
        self.assertNotIn("Jane Doe", markdown)
        self.assertNotIn("Real Labs", markdown)
        self.assertIn("Northline Labs", markdown)
        parsed_id, parsed_track = parse_identity_and_track(markdown, "industry")
        self.assertEqual(parsed_id["name"]["fake"], "ALEX RIVERA")
        self.assertEqual(parsed_id["name"]["real"], "")
        self.assertEqual(parsed_track["experience"][0]["employer"]["fake"], "Northline Labs")
        self.assertEqual(parsed_track["education"][0]["school"]["fake"], "Example Institute of Technology")
        mapping = mapping_from_form(identity, track, None)
        self.assertEqual(mapping["ALEX RIVERA"], "Jane Doe")
        self.assertEqual(mapping["Northline Labs"], "Real Labs")
        self.assertEqual(mapping["_github_url"], "https://github.com/jane")
        self.assertNotIn("Jane Doe", strip_real_values(identity)["name"])

    def test_mapping_from_form_includes_work_permit_aliases(self) -> None:
        identity = blank_identity()
        identity["work_permit"] = paired(
            "Example work authorization status",
            "Permanent residence",
        )
        mapping = mapping_from_form(identity, None, None)
        self.assertEqual(mapping["Example work authorization status"], "Permanent residence")
        self.assertEqual(mapping["Valid Norwegian work permit"], "Permanent residence")
        self.assertEqual(mapping["Gyldig norsk arbeidstillatelse"], "Permanent residence")

    def test_parse_committed_demo_industry(self) -> None:
        raw = (SHARED_DIR / "cv" / "industry.demo.md").read_text(encoding="utf-8")
        identity, track = parse_identity_and_track(raw, "industry")
        self.assertEqual(identity["name"]["fake"], "ALEX RIVERA")
        self.assertGreaterEqual(len(track["experience"]), 3)
        self.assertTrue(any("Northline Labs" in (r["employer"]["fake"]) for r in track["experience"]))

    def test_parse_committed_demo_academic(self) -> None:
        raw = (SHARED_DIR / "cv" / "academic.demo.md").read_text(encoding="utf-8")
        identity, track = parse_identity_and_track(raw, "academic")
        self.assertIn("demo.candidate@example.com", identity["email"]["fake"])
        self.assertTrue(track["education"])
        self.assertIn("Example Institute of Technology", track["education"][0]["school"]["fake"])
        rebuilt = assemble_markdown(identity, track, "academic")
        self.assertIn("Academic CV", rebuilt)
        self.assertIn("Example University Lab", rebuilt)


if __name__ == "__main__":
    unittest.main()
