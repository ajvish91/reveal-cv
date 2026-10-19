"""Tests for PhD student opening filter."""
from __future__ import annotations

import math
import unittest

from job_search.job_filters import haystack_for_filter, matches_phd_student_opening


class PhdStudentFilterTests(unittest.TestCase):
    def test_haystack_tolerates_nan_and_non_strings(self) -> None:
        """pandas empty cells are float NaN; must not break ' '.join."""
        hay = haystack_for_filter(
            "PhD position in ML",
            float("nan"),
            None,
            math.nan,
        )
        self.assertIn("phd position in ml", hay)
        self.assertNotIn("nan", hay)
        self.assertTrue(matches_phd_student_opening(hay))

    def test_blocks_phd_student_ads(self) -> None:
        cases = [
            "PhD position in machine learning",
            "PhD fellowship in AI",
            "PhD fellow within NLP",
            "doktorgradsstipendiat i informatikk",
            "PhD student in robotics",
            "doctoral fellowship in computer science",
            "PhD Research Fellow in Underwater Quantum Communication",
            "Ph.D Research Fellow Management: AI-based business model innovation",
            "Phd Research Fellow in Medicinal Chemistry",
            "PhD Candidate in Empirical Software Engineering",
            "Ph.D.-scholarship in numerical optimisation",
            "Ph.d.-stipendiat i algoritmar",
            "Stipendiat innen sykepleie og ergoterapi",
            "Stipendiatstilling i rettsvitenskap",
            "Doktorgradsstipendiater ved Det medisinske fakultet",
            "PhD research fellow/Researcher",
        ]
        for title in cases:
            hay = haystack_for_filter(title, None, None, "University of Example")
            self.assertTrue(matches_phd_student_opening(hay), msg=title)
            self.assertTrue(matches_phd_student_opening(hay, title.casefold()), msg=title)

    def test_keeps_postdoc_and_researcher(self) -> None:
        cases = [
            "Postdoctoral researcher in ML",
            "Postdoc fellowship in AI",
            "Postdoctoral Research Fellow at the Department of Biomedicine",
            "Postdoctoral research fellowship in children, youth and digital media",
            "Postdoktor innen Software Engineering",
            "Research fellow in information theory",
            "Associate professor in computer science",
            "Research scientist — PhD required",
            "Software engineer (requires PhD)",
        ]
        for title in cases:
            hay = haystack_for_filter(title, None, None, "Simula")
            self.assertFalse(matches_phd_student_opening(hay), msg=title)
            self.assertFalse(matches_phd_student_opening(hay, title.casefold()), msg=title)

    def test_postdoctoral_fellowship_not_blocked(self) -> None:
        hay = haystack_for_filter("Postdoctoral fellowship in privacy-preserving ML", None, None, "UiO")
        self.assertFalse(matches_phd_student_opening(hay))

    def test_postdoc_description_mentioning_phd_candidates_is_kept(self) -> None:
        title = "Postdoktor"
        description = "The postdoc will supervise PhD candidates and teach."
        hay = haystack_for_filter(title, None, description, "Universitetet i Oslo")
        self.assertFalse(matches_phd_student_opening(hay, title.casefold()))


if __name__ == "__main__":
    unittest.main()
