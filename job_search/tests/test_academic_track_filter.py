"""Tests for academic role filtering on the dashboard and ingest queries."""
from __future__ import annotations

import unittest

import pandas as pd

from job_search.dashboard import apply_dashboard_filters, effective_academic_roles_only
from job_search.finn_search_queries import all_default_finn_search_queries
from job_search.job_filters import (
    ACADEMIC_ROLE_INCLUDE_TERMS,
    ACADEMIC_ROLE_TITLE_TERMS,
    haystack_for_filter,
    matches_academic_role,
    matches_academic_role_display,
    matches_any_include_term,
)
from job_search.role_search_config import (
    DEFAULT_ACADEMIC_FINN_SEARCH_QUERIES,
    DEFAULT_FINN_SEARCH_QUERIES,
    finn_search_queries_for_track,
)


class AcademicRoleFilterTests(unittest.TestCase):
    def test_matches_university_postdoc(self) -> None:
        self.assertTrue(
            matches_academic_role_display(
                "Postdoctoral Research Fellow in AI",
                None,
                "We seek a postdoc for machine learning research",
                "University of Oslo",
            )
        )

    def test_matches_norwegian_lecturer_titles(self) -> None:
        for title in (
            "Førstelektor i informatikk",
            "Førsteamanuensis i data science",
            "Universitetslektor i kunstig intelligens",
        ):
            self.assertTrue(
                matches_academic_role_display(title, None, "Undervisning og forskning", "Høyskolen"),
                title,
            )

    def test_industry_data_engineer_not_academic(self) -> None:
        self.assertFalse(
            matches_academic_role_display(
                "Senior Data Engineer",
                None,
                "Build data pipelines on Azure for Capgemini clients",
                "Capgemini",
            )
        )

    def test_bim_coordinator_not_academic_display(self) -> None:
        self.assertFalse(
            matches_academic_role_display(
                "BIM Coordinator",
                None,
                "Software engineering and cloud projects at Hitachi Energy",
                "Hitachi Energy Norway AS",
            )
        )

    def test_forsvar_infrastructure_engineer_not_academic(self) -> None:
        self.assertFalse(
            matches_academic_role_display(
                "Data- og infrastrukturingeniør (prosjektstilling)",
                None,
                "Forskning og utvikling i Forsvaret",
                "Forsvaret",
            )
        )

    def test_research_assistant_not_academic_display(self) -> None:
        self.assertFalse(
            matches_academic_role_display(
                "Research Assistants",
                None,
                "Assist faculty with research projects",
                "University of Bergen",
            )
        )

    def test_description_forskning_alone_not_academic_display(self) -> None:
        hay = haystack_for_filter(
            "IT Engineer",
            None,
            "Du vil jobbe med forskning og utvikling",
            "Private company",
        )
        self.assertTrue(matches_academic_role(hay))
        self.assertFalse(
            matches_academic_role_display(
                "IT Engineer",
                None,
                "Du vil jobbe med forskning og utvikling",
                "Private company",
            )
        )

    def test_apply_dashboard_filters_academic_only(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "title": "Postdoctoral fellow in NLP",
                    "jobtitle": "",
                    "description_text": "Research at Simula",
                    "employer_name": "Simula",
                    "score_total": 55.0,
                    "score_base": 40.0,
                    "matched_keywords": "nlp",
                    "matched_skills": None,
                    "in_rogaland": False,
                    "location_matched": False,
                },
                {
                    "title": "Principal Architect",
                    "jobtitle": "",
                    "description_text": "Enterprise AI and data platform",
                    "employer_name": "Norconsult",
                    "score_total": 60.0,
                    "score_base": 45.0,
                    "matched_keywords": "ai",
                    "matched_skills": None,
                    "in_rogaland": False,
                    "location_matched": False,
                },
                {
                    "title": "BIM Coordinator",
                    "jobtitle": "",
                    "description_text": "Software engineering projects",
                    "employer_name": "Hitachi Energy",
                    "score_total": 70.0,
                    "score_base": 50.0,
                    "matched_keywords": "software",
                    "matched_skills": None,
                    "in_rogaland": False,
                    "location_matched": False,
                },
            ]
        )
        filtered = apply_dashboard_filters(
            df,
            use_tech_allowlist=False,
            include_terms=(),
            exclude_terms=(),
            hide_phd_student=True,
            academic_roles_only=True,
        )
        titles = filtered["title"].tolist()
        self.assertIn("Postdoctoral fellow in NLP", titles)
        self.assertNotIn("Principal Architect", titles)
        self.assertNotIn("BIM Coordinator", titles)

    def test_effective_academic_roles_only_on_academic_track(self) -> None:
        self.assertTrue(
            effective_academic_roles_only(track="academic", academic_roles_only=False)
        )
        self.assertFalse(
            effective_academic_roles_only(track="industry", academic_roles_only=False)
        )

    def test_academic_terms_list_covers_posting_titles(self) -> None:
        joined = " ".join(ACADEMIC_ROLE_TITLE_TERMS).casefold()
        for term in (
            "postdoc",
            "postdoktor",
            "førstelektor",
            "førsteamanuensis",
            "universitetslektor",
            "researcher",
        ):
            self.assertIn(term.casefold(), joined)

    def test_broad_include_terms_still_cover_legacy_sql(self) -> None:
        joined = " ".join(ACADEMIC_ROLE_INCLUDE_TERMS).casefold()
        self.assertIn("forskning", joined)


class AcademicFinnQueryTests(unittest.TestCase):
    def test_academic_queries_present(self) -> None:
        joined = " ".join(DEFAULT_ACADEMIC_FINN_SEARCH_QUERIES).casefold()
        for term in ("postdoktor", "postdoc", "førstelektor", "forskning", "researcher"):
            self.assertIn(term.casefold(), joined)

    def test_postdoktor_title_matches_academic_and_tech_filters(self) -> None:
        from job_search.job_filters import DEFAULT_TECH_INCLUDE_TERMS, term_matches

        hay = haystack_for_filter("Postdoktor i informatikk", None, "", "NTNU")
        self.assertTrue(matches_academic_role_display("Postdoktor i informatikk", None, "", "NTNU"))
        self.assertTrue(matches_any_include_term(hay, DEFAULT_TECH_INCLUDE_TERMS))
        self.assertTrue(term_matches(hay, "postdoktor"))
        self.assertFalse(term_matches(hay, "postdoc"))

    def test_postdoktor_in_academic_finn_queries(self) -> None:
        self.assertIn("postdoktor", DEFAULT_ACADEMIC_FINN_SEARCH_QUERIES)

    def test_both_track_merges_industry_and_academic(self) -> None:
        both = finn_search_queries_for_track("both")
        self.assertIn("data engineer", both)
        self.assertIn("postdoc", both)
        self.assertEqual(len(both), len(all_default_finn_search_queries()))

    def test_industry_track_omits_academic_only_queries(self) -> None:
        industry = finn_search_queries_for_track("industry")
        self.assertIn("software engineer", industry)
        self.assertNotIn("førstelektor", industry)

    def test_industry_defaults_unchanged(self) -> None:
        self.assertIn("software engineer", DEFAULT_FINN_SEARCH_QUERIES)


if __name__ == "__main__":
    unittest.main()
