"""Tests for institution cross-checks in CV assembly."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.cv_assemble import (
    assemble_final_cv_markdown,
    validate_institution_consistency,
)


SWAPPED_ACADEMIC_SNIPPET = """# Academic CV

## Education

### Ph.D.
University of Arkansas
2022 - 2025
Information and Communication Technology

### M.Sc., Computing
Texas University
2018 - 2019
Computer Science

## Teaching and supervision

- Assistant professor (guest): AI, ethics, and society — University of Arkansas (master's level).

## Research experience

### Texas University
Ph.D. Student in AI
Aug 2022 - Aug 2025

- Built reinforcement-learning systems with ethical constraints.
"""

CONSISTENT_ACADEMIC_SNIPPET = """# Academic CV

## Education

### Ph.D.
Texas University
2022 - 2025
Information and Communication Technology

### M.Sc., Computing
University of Arkansas
2018 - 2019
Computer Science

## Teaching and supervision

- Assistant professor (guest): AI, ethics, and society — Texas University (master's level).

## Research experience

### Texas University
Ph.D. Student in AI
Aug 2022 - Aug 2025

- Built reinforcement-learning systems with ethical constraints.
"""


class TestInstitutionValidation(unittest.TestCase):
    def test_detects_phd_education_experience_mismatch_in_source(self) -> None:
        warnings = validate_institution_consistency(SWAPPED_ACADEMIC_SNIPPET)
        self.assertTrue(any("Ph.D. Education institution" in w for w in warnings))

    def test_consistent_source_has_no_warnings(self) -> None:
        warnings = validate_institution_consistency(CONSISTENT_ACADEMIC_SNIPPET)
        self.assertEqual(warnings, [])

    def test_detects_bullet_tailor_employer_relabel(self) -> None:
        bullet_tailor_output = {
            "tailored_summary": "",
            "experience_roles": [
                {
                    "role_key": "ph.d. student in ai|university of arkansas|aug 2022 - aug 2025",
                    "role": "Ph.D. Student in AI",
                    "company": "University of Arkansas",
                    "duration": "Aug 2022 - Aug 2025",
                    "bullets": ["Built reinforcement-learning systems."],
                }
            ],
            "removed_claims": [],
        }
        warnings = validate_institution_consistency(
            CONSISTENT_ACADEMIC_SNIPPET,
            bullet_tailor_output=bullet_tailor_output,
        )
        self.assertTrue(any("relabeled employer" in w for w in warnings))

    def test_assemble_emits_no_institution_warnings_for_consistent_source(self) -> None:
        bullet_tailor_output = {
            "tailored_summary": "",
            "experience_roles": [
                {
                    "role_key": "ph.d. student in ai|texas university|aug 2022 - aug 2025",
                    "role": "Ph.D. Student in AI",
                    "company": "Texas University",
                    "duration": "Aug 2022 - Aug 2025",
                    "bullets": ["Built reinforcement-learning systems with ethical constraints."],
                }
            ],
            "removed_claims": [],
        }
        _, warnings = assemble_final_cv_markdown(
            CONSISTENT_ACADEMIC_SNIPPET,
            bullet_tailor_output,
            apply_tailored_experience=True,
        )
        institution_warnings = [w for w in warnings if "institution" in w.lower() or "employer" in w.lower()]
        self.assertEqual(institution_warnings, [])


if __name__ == "__main__":
    unittest.main()
