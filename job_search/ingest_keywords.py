"""Merge CV profile keywords/skills with curated application-history boosts for ingest."""
from __future__ import annotations

from shared.cv_loader import load_default_profiles
from job_search.role_search_config import (
    DEFAULT_INGEST_KEYWORD_BOOSTS,
    merge_unique_terms,
    profiles_use_demo_templates,
)


def collect_ingest_keywords(
    extra: list[str],
    *,
    include_skills: bool,
    include_application_boosts: bool | None = None,
) -> list[str]:
    """
    Keywords used by NAV/FINN ingest for --keyword-filter matching and --list-keywords.

    Sources (in order):
      1. CV profile keywords (+ skills when include_skills)
      2. DEFAULT_INGEST_KEYWORD_BOOSTS when include_application_boosts is True
         (default: always on; boosts are curated from cv_runs application history)
      3. CLI --keyword extras
    """
    cv_terms: list[str] = []
    profiles = load_default_profiles()
    for pr in profiles:
        cv_terms.extend(pr.keywords)
        if include_skills:
            cv_terms.extend(pr.skills)

    if include_application_boosts is None:
        # Always merge boosts: demo CVs are sparse; real CVs dedupe overlapping terms.
        include_application_boosts = True

    boost_terms = list(DEFAULT_INGEST_KEYWORD_BOOSTS) if include_application_boosts else []
    return merge_unique_terms(cv_terms, boost_terms, extra)


def using_demo_cv_keywords() -> bool:
    """Expose demo detection for tests and diagnostics."""
    return profiles_use_demo_templates(load_default_profiles())
