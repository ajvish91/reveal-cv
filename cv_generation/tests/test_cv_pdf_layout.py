"""PDF layout: sidebar continuation pages and profile length limits."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.cv_assemble import assemble_final_cv_markdown
from cv_generation.cv_pdf_renderer import parse_cv_markdown, render_styled_cv_pdf
from cv_generation.cv_style import (
    PROFILE_MAX_CHARS_PER_PARAGRAPH,
    PROFILE_MAX_PARAGRAPHS,
    PROFILE_MAX_TOTAL_CHARS,
    normalize_profile_paragraphs,
    normalize_summary_bullets,
)

INDUSTRY_MD = REPO / "shared" / "cv" / "industry.md"


def _sidebar_tail_counts(pdf_path: Path) -> list[tuple[int, int]]:
    from pypdf import PdfReader

    counts: list[tuple[int, int]] = []
    for page in PdfReader(str(pdf_path)).pages:
        text = page.extract_text() or ""
        counts.append((text.count("LANGUAGES"), text.count("HOBBIES")))
    return counts


class TestProfileLengthLimits(unittest.TestCase):
    def test_normalize_profile_paragraphs_caps_count_and_chars(self) -> None:
        paras = ["a" * 500, "b" * 500, "c" * 100]
        limited, warnings = normalize_profile_paragraphs(paras)
        self.assertLessEqual(len(limited), PROFILE_MAX_PARAGRAPHS)
        self.assertLessEqual(sum(len(p) for p in limited), PROFILE_MAX_TOTAL_CHARS)
        for para in limited:
            self.assertLessEqual(len(para), PROFILE_MAX_CHARS_PER_PARAGRAPH)
        self.assertTrue(warnings)

    def test_normalize_summary_bullets_caps_length(self) -> None:
        bullets = ["- " + ("x" * 300)]
        limited, warnings = normalize_summary_bullets(bullets)
        self.assertEqual(len(limited), 1)
        self.assertLess(len(limited[0]), 300)
        self.assertTrue(warnings)

    def test_assemble_trims_long_source_profile(self) -> None:
        source = INDUSTRY_MD.read_text(encoding="utf-8")
        md, warnings = assemble_final_cv_markdown(
            source,
            {"tailored_summary": "", "experience_roles": []},
        )
        cv = parse_cv_markdown(md)
        total = sum(len(p) for p in cv.profile_paragraphs)
        self.assertLessEqual(len(cv.profile_paragraphs), PROFILE_MAX_PARAGRAPHS)
        self.assertLessEqual(total, PROFILE_MAX_TOTAL_CHARS)
        self.assertTrue(any("Profile" in w for w in warnings))


class TestCvPdfMultiPageLayout(unittest.TestCase):
    def test_tail_sections_only_on_first_continuation_page(self) -> None:
        """Languages/hobbies must not repeat on page 3+ when main content spans 3 pages."""
        source = INDUSTRY_MD.read_text(encoding="utf-8")
        extra_roles = []
        for index in range(8):
            extra_roles.append(
                f"""
### Extra Corp {index}
Senior ML Engineer
202{index % 10} - 202{index % 10 + 1}

- Built **LLM pipelines** for document processing with evaluation hooks, observability, and privacy controls across production systems.
- Delivered scalable backend services with CI/CD, monitoring, and cross-functional collaboration on data quality and model deployment.
- Improved retrieval-oriented workflows and content understanding pipelines for enterprise integrations and catalog search.
"""
            )
        long_cv = source.replace("## Education", "\n".join(extra_roles) + "\n## Education")
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "cv.md"
            pdf_path = Path(tmp) / "cv.pdf"
            md_path.write_text(long_cv, encoding="utf-8")
            render_styled_cv_pdf(md_path, pdf_path)
            tail_counts = _sidebar_tail_counts(pdf_path)
            self.assertGreaterEqual(len(tail_counts), 3)
            self.assertEqual(tail_counts[1], (1, 1), "page 2 should show languages and hobbies")
            for page_index, counts in enumerate(tail_counts[2:], start=3):
                self.assertEqual(
                    counts,
                    (0, 0),
                    f"page {page_index} must not repeat sidebar tail sections",
                )

    def test_industry_source_fits_two_pages_after_profile_trim(self) -> None:
        source = INDUSTRY_MD.read_text(encoding="utf-8")
        md, _ = assemble_final_cv_markdown(
            source,
            {"tailored_summary": "", "experience_roles": []},
        )
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "cv.md"
            pdf_path = Path(tmp) / "cv.pdf"
            md_path.write_text(md, encoding="utf-8")
            render_styled_cv_pdf(md_path, pdf_path)
            from pypdf import PdfReader

            self.assertEqual(len(PdfReader(str(pdf_path)).pages), 2)


if __name__ == "__main__":
    unittest.main()
