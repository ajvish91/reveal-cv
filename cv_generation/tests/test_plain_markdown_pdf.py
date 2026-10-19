"""Plain markdown PDF rendering for proposals and letters."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.plain_markdown_pdf import build_plain_markdown_story, render_plain_markdown_pdf


class TestPlainMarkdownPdf(unittest.TestCase):
    def test_heading_and_inline_bold(self) -> None:
        lines = [
            "# Research proposal",
            "",
            "**Applicant:** MITCH EVANS",
            "## Summary",
            "Text with **mixed-methods** design.",
        ]
        story = build_plain_markdown_story(lines)
        self.assertGreater(len(story), 0)

    def test_renders_pdf_without_literal_markers(self) -> None:
        md = (
            "# Research proposal\n\n"
            "**Applicant:** MITCH EVANS\n\n"
            "## Title\n\n"
            "Example title\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            md_path = Path(tmp) / "research_proposal.md"
            pdf_path = Path(tmp) / "research_proposal.pdf"
            md_path.write_text(md, encoding="utf-8")
            render_plain_markdown_pdf(md_path, pdf_path)
            self.assertTrue(pdf_path.is_file())
            self.assertGreater(pdf_path.stat().st_size, 500)


if __name__ == "__main__":
    unittest.main()
