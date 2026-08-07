"""Application artifact registry and deanonymize helpers."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.cv_application_artifacts import (
    detect_supplementary_artifacts,
    is_plain_pdf_markdown,
    normalize_upper_name_variants,
)


class TestApplicationArtifacts(unittest.TestCase):
    def test_detect_postdoc_artifacts(self) -> None:
        job = "Post-doctoral fellow. Attach a research proposal. Application letter describing motivation."
        names = {a.filename for a in detect_supplementary_artifacts(job)}
        self.assertIn("research_proposal.md", names)
        self.assertIn("application_letter.md", names)

    def test_detect_industry_cover_letter(self) -> None:
        job = "Senior ML engineer at a fintech. Send CV and cover letter."
        names = {a.filename for a in detect_supplementary_artifacts(job)}
        self.assertIn("cover_letter.md", names)
        self.assertNotIn("research_proposal.md", names)

    def test_detect_academic_track_defaults_to_application_letter(self) -> None:
        job = "We are a growing technology company looking for developers."
        names = {a.filename for a in detect_supplementary_artifacts(job, track="academic")}
        self.assertIn("application_letter.md", names)
        self.assertNotIn("cover_letter.md", names)

    def test_detect_norwegian_postdoktor_prosjektskisse(self) -> None:
        job = (
            "Postdoktor innen e-helse. Søknaden skal inneholde motivasjonsbrev "
            "og prosjektskisse (maks 5 sider)."
        )
        names = {a.filename for a in detect_supplementary_artifacts(job)}
        self.assertIn("research_proposal.md", names)
        self.assertIn("application_letter.md", names)

    def test_detect_norwegian_soknadstekst_and_referanseprosjekter(self) -> None:
        job = (
            "Vi søker Utvikler – AI. Vi ber deg sende oss: "
            "Søknadstekst med fokus på motivasjon og relevans; CV; "
            "Beskrivelse av referanseprosjekter som demonstrerer relevante kompetanser."
        )
        names = {a.filename for a in detect_supplementary_artifacts(job, track="industry")}
        self.assertIn("cover_letter.md", names)
        self.assertIn("reference_projects.md", names)

    def test_plain_pdf_markers(self) -> None:
        self.assertTrue(is_plain_pdf_markdown(Path("research_proposal.md"), "# Research proposal\n"))
        self.assertTrue(is_plain_pdf_markdown(Path("cover_letter.md"), "Dear team\nSincerely\n"))
        self.assertTrue(is_plain_pdf_markdown(Path("reference_projects_no.md"), "# Referanseprosjekter\n"))
        self.assertFalse(is_plain_pdf_markdown(Path("final_cv.md"), "# Industry CV\n## Name\n"))


    def test_name_title_case_alias(self) -> None:
        mapping = {"MITCH EVANS": "Alex Rivera"}
        expanded = normalize_upper_name_variants(mapping)
        self.assertEqual(expanded["Mitch Evans"], "Alex Rivera")


if __name__ == "__main__":
    unittest.main()
