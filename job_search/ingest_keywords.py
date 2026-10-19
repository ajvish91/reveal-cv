"""Merge CV profile keywords/skills with optional application-history boosts for ingest."""
from __future__ import annotations

from typing import Iterable

from shared.cv_loader import JobProfile, load_default_profiles
from job_search.role_search_config import (
    DEFAULT_INGEST_KEYWORD_BOOSTS,
    merge_unique_terms,
    profiles_use_demo_templates,
)

# Alone, these profile/boost tokens keep too much unrelated work (biology postdocs,
# "company philosophy", generic "innovation" fluff). Strong ingest keep requires at
# least one term outside this set.
WEAK_ALONE_INGEST_TERMS: frozenset[str] = frozenset(
    {
        "research",
        "innovation",
        "philosophy",
        "consulting",
        "forskning",
        "forsker",
        "researcher",
        "vitenskapelig",
    }
)


def profile_terms_from_loaded(
    profiles: Iterable[JobProfile],
    *,
    include_skills: bool,
) -> list[str]:
    """Ordered unique keywords (+ optional skills) from loaded CV profiles."""
    cv_terms: list[str] = []
    for pr in profiles:
        cv_terms.extend(pr.keywords)
        if include_skills:
            cv_terms.extend(pr.skills)
    return merge_unique_terms(cv_terms, [], [])


def collect_ingest_keywords(
    extra: list[str],
    *,
    include_skills: bool,
    include_application_boosts: bool | None = None,
    drop_weak_alone: bool = True,
) -> list[str]:
    """
    Keywords used by NAV/FINN ingest for --keyword-filter matching and --list-keywords.

    Sources (in order):
      1. CV profile keywords (+ skills when include_skills)
      2. DEFAULT_INGEST_KEYWORD_BOOSTS only when include_application_boosts is True
         (default: **on for demo CV templates only**; off for real profiles so the
         CV alone gates keep/drop)
      3. CLI --keyword extras

    When ``drop_weak_alone`` is True (default), strip tokens in
    ``WEAK_ALONE_INGEST_TERMS`` so bare ``research`` / ``innovation`` cannot keep an ad.
    """
    profiles = load_default_profiles()
    cv_terms = profile_terms_from_loaded(profiles, include_skills=include_skills)

    if include_application_boosts is None:
        # Demo CVs are sparse; real profiles should gate ingest by themselves.
        include_application_boosts = profiles_use_demo_templates(profiles)

    boost_terms = list(DEFAULT_INGEST_KEYWORD_BOOSTS) if include_application_boosts else []
    merged = merge_unique_terms(cv_terms, boost_terms, extra)
    if not drop_weak_alone:
        return merged
    return [t for t in merged if t.casefold() not in WEAK_ALONE_INGEST_TERMS]


def using_demo_cv_keywords() -> bool:
    """Expose demo detection for tests and diagnostics."""
    return profiles_use_demo_templates(load_default_profiles())
