"""Tests for profile relevance filtering and expanded noise blocklist."""
from __future__ import annotations

import unittest

import pandas as pd

from job_search.dashboard import apply_dashboard_filters
from job_search.job_filters import (
    DEFAULT_EXCLUDE_TERMS,
    DEFAULT_TECH_INCLUDE_TERMS,
    haystack_for_filter,
    has_profile_relevance,
    matches_exclude_terms,
    matches_any_include_term,
    matches_finance_controller,
)


class ProfileRelevanceTests(unittest.TestCase):
    def test_location_only_score_is_not_relevant(self) -> None:
        row = {
            "score_base": 0.0,
            "score_total": 5.0,
            "boost_rogaland": 5.0,
            "boost_tek": 0.0,
            "matched_keywords": None,
            "matched_skills": None,
        }
        self.assertFalse(has_profile_relevance(row))

    def test_keyword_match_is_relevant(self) -> None:
        row = {
            "score_base": 0.0,
            "score_total": 5.0,
            "matched_keywords": "python",
            "matched_skills": None,
        }
        self.assertTrue(has_profile_relevance(row))

    def test_tek_boost_without_keywords_is_not_relevant(self) -> None:
        row = {
            "score_base": 0.0,
            "score_total": 25.0,
            "boost_rogaland": 0.0,
            "boost_tek": 25.0,
            "matched_keywords": None,
            "matched_skills": None,
        }
        self.assertFalse(has_profile_relevance(row))

    def test_tek_boost_with_keyword_overlap_is_relevant(self) -> None:
        row = {
            "score_base": 10.0,
            "score_total": 35.0,
            "boost_rogaland": 0.0,
            "boost_tek": 25.0,
            "matched_keywords": "python",
            "matched_skills": None,
        }
        self.assertTrue(has_profile_relevance(row))

    def test_apply_dashboard_filters_drops_location_only(self) -> None:
        df = pd.DataFrame(
            [
                {
                    "title": "Software engineer",
                    "jobtitle": "",
                    "description_text": "Python and machine learning",
                    "employer_name": "Tech AS",
                    "score_total": 40.0,
                    "score_base": 25.0,
                    "matched_keywords": "python",
                    "matched_skills": None,
                    "in_rogaland": True,
                    "location_matched": True,
                },
                {
                    "title": "Butikkmedarbeider",
                    "jobtitle": "",
                    "description_text": "Vi digitaliserer butikken vår",
                    "employer_name": "Bokhandel",
                    "score_total": 5.0,
                    "score_base": 0.0,
                    "matched_keywords": None,
                    "matched_skills": None,
                    "in_rogaland": True,
                    "location_matched": True,
                },
            ]
        )
        filtered = apply_dashboard_filters(
            df,
            use_tech_allowlist=True,
            include_terms=DEFAULT_TECH_INCLUDE_TERMS,
            exclude_terms=DEFAULT_EXCLUDE_TERMS,
            hide_phd_student=True,
            rogaland_only=True,
            require_profile_match=True,
        )
        titles = filtered["title"].tolist()
        self.assertIn("Software engineer", titles)
        self.assertNotIn("Butikkmedarbeider", titles)


class NoiseBlocklistTests(unittest.TestCase):
    def test_butikkmedarbeider_excluded(self) -> None:
        hay = haystack_for_filter("Butikkmedarbeider", None, "Vi søker deg til bokhandel", "Ark")
        self.assertTrue(matches_exclude_terms(hay, DEFAULT_EXCLUDE_TERMS))

    def test_fastlege_excluded(self) -> None:
        hay = haystack_for_filter("Fastlegestilling", None, "Allmennlege søkes", "Legekontor")
        self.assertTrue(matches_exclude_terms(hay, DEFAULT_EXCLUDE_TERMS))

    def test_marketing_spam_excluded(self) -> None:
        hay = haystack_for_filter("Er du sulten på å tjene penger?", None, "Salg og markedsføring", "Firma")
        self.assertTrue(matches_exclude_terms(hay, DEFAULT_EXCLUDE_TERMS))

    def test_finance_controller_excluded(self) -> None:
        hay = haystack_for_filter("Controller", None, "Økonomi og regnskap", "Industri AS")
        self.assertTrue(matches_finance_controller(hay))
        self.assertTrue(matches_exclude_terms(hay, DEFAULT_EXCLUDE_TERMS))

    def test_it_controller_kept(self) -> None:
        hay = haystack_for_filter("IT controller", None, "IKT og systemforvaltning", "Kommune")
        self.assertFalse(matches_finance_controller(hay))
        self.assertFalse(matches_exclude_terms(hay, DEFAULT_EXCLUDE_TERMS))

    def test_it_enhetsleder_digitalisering_kept(self) -> None:
        hay = haystack_for_filter(
            "IT enhetsleder digitalisering",
            None,
            "Lede digital utvikling og integrasjon",
            "Kommune",
        )
        self.assertTrue(matches_any_include_term(hay, DEFAULT_TECH_INCLUDE_TERMS))
        self.assertFalse(matches_exclude_terms(hay, DEFAULT_EXCLUDE_TERMS))


if __name__ == "__main__":
    unittest.main()
