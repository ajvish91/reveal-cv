"""Guardrails: industry and academic CV workflows stay separated."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.cv_assemble import assemble_final_cv_markdown, select_tailored_skills
from cv_generation.cv_pdf_renderer import (
    markdown_inline_to_reportlab,
    parse_cv_markdown,
    parse_experience_heading,
    _is_academic_cv,
    _is_industry_cv,
)
from cv_generation.cv_private import (
    ANON_GOOGLE_SCHOLAR_URL,
    ANON_ORCID_URL,
    social_url_replacements_from_raw,
)
from cv_generation.cv_tracks import cv_track_from_title, is_academic_title, is_industry_title

INDUSTRY_MD = REPO / "shared" / "cv" / "industry.demo.md"
INDUSTRY_SOURCE_MD = REPO / "shared" / "cv" / "industry.md"
ACADEMIC_MD = REPO / "shared" / "cv" / "academic.demo.md"


class TestCvTrackSeparation(unittest.TestCase):
    def test_track_detection_from_title(self) -> None:
        self.assertEqual(cv_track_from_title("Industry CV"), "industry")
        self.assertEqual(cv_track_from_title("Academic CV"), "academic")
        self.assertTrue(is_industry_title("Industry CV"))
        self.assertTrue(is_academic_title("Academic CV"))

    def test_source_contact_separation(self) -> None:
        industry = INDUSTRY_MD.read_text(encoding="utf-8")
        academic = ACADEMIC_MD.read_text(encoding="utf-8")
        self.assertNotIn("Google Scholar", industry)
        self.assertNotIn("ORCID", industry)
        self.assertIn("Google Scholar", academic)
        self.assertIn("ORCID", academic)

    def test_parsed_cv_track_flags(self) -> None:
        industry_cv = parse_cv_markdown(INDUSTRY_MD.read_text(encoding="utf-8"))
        academic_cv = parse_cv_markdown(ACADEMIC_MD.read_text(encoding="utf-8"))
        self.assertTrue(_is_industry_cv(industry_cv))
        self.assertFalse(_is_academic_cv(industry_cv))
        self.assertTrue(_is_academic_cv(academic_cv))
        self.assertFalse(_is_industry_cv(academic_cv))

    def test_scholar_orcid_replacements_optional_for_industry(self) -> None:
        """Industry deanonymize works with only GitHub/LinkedIn metadata."""
        raw = {
            "_github_url": "https://github.com/realuser",
            "_linkedin_url": "https://www.linkedin.com/in/realuser",
        }
        pairs = social_url_replacements_from_raw(raw)
        self.assertNotIn(ANON_GOOGLE_SCHOLAR_URL, pairs)
        self.assertNotIn(ANON_ORCID_URL, pairs)
        self.assertIn("https://github.com/cv-placeholder", pairs)


class TestTailoredSkills(unittest.TestCase):
    def test_select_tailored_skills_caps_at_four(self) -> None:
        source = ["Python", "Java", "LaTeX", "Unity", "Docker", "MySQL"]
        picked = select_tailored_skills(source, ["docker", "python"])
        self.assertEqual(len(picked), 4)
        self.assertEqual(picked[0], "Python")
        self.assertIn("Docker", picked)

    def test_select_tailored_skills_keeps_short_lists(self) -> None:
        source = ["Python", "PyTorch"]
        self.assertEqual(select_tailored_skills(source), source)


class TestMarkdownInlineEmphasis(unittest.TestCase):
    def test_plain_text_is_escaped(self) -> None:
        self.assertEqual(markdown_inline_to_reportlab("a & b"), "a &amp; b")

    def test_bold_and_italic(self) -> None:
        self.assertEqual(
            markdown_inline_to_reportlab("Built **Python data pipelines** with *batch* work."),
            "Built <b>Python data pipelines</b> with <i>batch</i> work.",
        )

    def test_parsed_bullets_preserve_markers(self) -> None:
        md = "# Industry CV\n\n## Experience\n\n### Example Corp\nRole title\n2020\n\n- Did **data quality** work.\n"
        cv = parse_cv_markdown(md)
        self.assertEqual(cv.experience[0].company, "Example Corp")
        self.assertEqual(cv.experience[0].role, "Role title")
        self.assertEqual(cv.experience[0].bullets[0], "Did **data quality** work.")

    def test_experience_heading_company_first_for_mixed_markdown(self) -> None:
        self.assertEqual(
            parse_experience_heading("Postdoctoral Researcher", "University of Boston"),
            ("University of Boston", "Postdoctoral Researcher"),
        )
        self.assertEqual(
            parse_experience_heading("NXT Research Center", "Research Engineer"),
            ("NXT Research Center", "Research Engineer"),
        )

    def test_industry_source_experience_company_before_role(self) -> None:
        cv = parse_cv_markdown(INDUSTRY_SOURCE_MD.read_text(encoding="utf-8"))
        boston = next(item for item in cv.experience if "Boston" in item.company)
        self.assertEqual(boston.company, "University of Boston")
        self.assertEqual(boston.role, "Postdoctoral Researcher, ForwardMedia Research Centre")
        nxt = next(item for item in cv.experience if "NXT" in item.company)
        self.assertEqual(nxt.company, "NXT Research Center")
        self.assertEqual(nxt.role, "Research Engineer")

    def test_academic_assembly_omits_role_designation(self) -> None:
        source = ACADEMIC_MD.read_text(encoding="utf-8")
        md, _ = assemble_final_cv_markdown(
            source,
            {"tailored_summary": "", "experience_roles": []},
            job_role_title="Research Fellow in AI",
        )
        self.assertNotIn("## Role", md)
        self.assertIn("## Summary", md)

    def test_industry_assembly_includes_role_designation(self) -> None:
        source = INDUSTRY_MD.read_text(encoding="utf-8")
        md, _ = assemble_final_cv_markdown(
            source,
            {"tailored_summary": "", "experience_roles": []},
            job_role_title="ML Engineer",
        )
        self.assertIn("## Role", md)
        self.assertIn("ML ENGINEER", md)


if __name__ == "__main__":
    unittest.main()
