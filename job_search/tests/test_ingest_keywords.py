from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from shared.cv_loader import JobProfile
from job_search.ingest_keywords import collect_ingest_keywords, using_demo_cv_keywords
from job_search.job_filters import matches_any_include_term, term_matches, haystack_for_filter
from job_search.role_search_config import (
    DEFAULT_FINN_SEARCH_QUERIES,
    DEFAULT_INGEST_KEYWORD_BOOSTS,
    profiles_use_demo_templates,
)


def _demo_profile(track: str = "industry") -> JobProfile:
    return JobProfile(
        track=track,
        source_path=Path(f"shared/cv/{track}.demo.md"),
        front_matter={
            "keywords": ["machine learning", "python"],
            "skills": ["PyTorch", "Docker"],
        },
        body_markdown="",
    )


def _real_profile(track: str = "industry") -> JobProfile:
    return JobProfile(
        track=track,
        source_path=Path(f"shared/cv/{track}.md"),
        front_matter={
            "keywords": ["agentic ai", "rag"],
            "skills": ["Python"],
        },
        body_markdown="",
    )


class IngestKeywordTests(unittest.TestCase):
    def test_demo_profiles_detected(self) -> None:
        self.assertTrue(profiles_use_demo_templates([_demo_profile(), _demo_profile("academic")]))
        self.assertFalse(profiles_use_demo_templates([_real_profile(), _demo_profile("academic")]))

    @patch("job_search.ingest_keywords.load_default_profiles", return_value=[_demo_profile()])
    def test_collect_merges_cv_skills_and_application_boosts(self, _mock: object) -> None:
        keywords = collect_ingest_keywords([], include_skills=True)
        self.assertIn("machine learning", keywords)
        self.assertIn("PyTorch", keywords)
        self.assertIn("agentic ai", keywords)
        self.assertIn("postdoctoral", keywords)
        self.assertIn("platform engineer", keywords)

    @patch("job_search.ingest_keywords.load_default_profiles", return_value=[_demo_profile()])
    def test_collect_without_skills_omits_skill_terms(self, _mock: object) -> None:
        keywords = collect_ingest_keywords([], include_skills=False)
        self.assertIn("machine learning", keywords)
        self.assertNotIn("PyTorch", keywords)
        self.assertIn("rag", keywords)

    @patch("job_search.ingest_keywords.load_default_profiles", return_value=[_real_profile()])
    def test_real_cv_dedupes_overlapping_boosts(self, _mock: object) -> None:
        keywords = collect_ingest_keywords([], include_skills=True)
        self.assertEqual(keywords.count("agentic ai"), 1)
        self.assertEqual(keywords.count("rag"), 1)

    def test_application_boosts_cover_applied_role_lanes(self) -> None:
        joined = " ".join(DEFAULT_INGEST_KEYWORD_BOOSTS).casefold()
        for term in (
            "agentic ai",
            "rag",
            "platform engineer",
            "postdoktor",
            "postdoctoral",
            "research scientist",
            "forskning",
        ):
            self.assertIn(term.casefold(), joined)

    def test_finn_queries_cover_application_lanes(self) -> None:
        joined = " ".join(DEFAULT_FINN_SEARCH_QUERIES).casefold()
        for term in (
            "data engineer",
            "AI engineer",
            "software engineer",
            "agentic AI",
            "RAG",
            "platform engineer",
            "AI platform engineer",
        ):
            self.assertIn(term.casefold(), joined)

    def test_finn_academic_queries_merged_by_default(self) -> None:
        from job_search.role_search_config import all_default_finn_search_queries

        merged = all_default_finn_search_queries()
        self.assertIn("postdoktor", merged)
        self.assertIn("postdoc", merged)
        self.assertIn("førstelektor", merged)
        self.assertIn("data engineer", merged)

    def test_tech_allowlist_covers_agentic_and_academic_roles(self) -> None:
        hay_agentic = "agentic ai and generative ai solutions architect for enterprise rag systems"
        hay_academic = (
            "postdoc and postdoctoral research fellow and research scientist "
            "in forskning and information theory"
        )
        agentic_terms = ("agentic", "rag", "generative ai")
        academic_terms = ("postdoc", "postdoctoral", "research fellow", "research scientist", "forskning")
        hay_postdoktor = haystack_for_filter("Postdoktor i biologi", None, "", "UiO")
        self.assertTrue(term_matches(hay_postdoktor, "postdoktor"))
        self.assertFalse(term_matches(hay_postdoktor, "postdoc"))
        for term in agentic_terms:
            self.assertTrue(term_matches(hay_agentic, term), term)
        for term in academic_terms:
            self.assertTrue(term_matches(hay_academic, term), term)
        self.assertTrue(matches_any_include_term(hay_agentic, agentic_terms))
        self.assertTrue(matches_any_include_term(hay_academic, academic_terms))
        self.assertTrue(matches_any_include_term(hay_postdoktor, ("postdoktor",)))

    @patch("job_search.ingest_keywords.load_default_profiles", return_value=[_demo_profile()])
    def test_using_demo_cv_keywords_helper(self, _mock: object) -> None:
        self.assertTrue(using_demo_cv_keywords())


if __name__ == "__main__":
    unittest.main()
