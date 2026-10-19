"""
Curated search and ingest keywords derived from cv_runs application history.

Supplements CV front-matter keywords when demo templates are in use, and fills gaps
for roles the candidate actually applies to (agentic AI, RAG, platform engineering,
academic postdoc/research scientist, etc.).

See JOB_SEARCH.md → “Keyword filtering”.
"""
from __future__ import annotations

from shared.cv_loader import JobProfile, load_default_profiles

# Ingest keyword matching (--keyword-filter): merged after CV keywords/skills.
# Sourced from 24 industry + academic applications in cv_generation/cv_runs/.
DEFAULT_INGEST_KEYWORD_BOOSTS: tuple[str, ...] = (
    # Agentic / GenAI (Equinor, Storebrand, Statnett, Six Robotics, …)
    "agentic ai",
    "agentic",
    "generative ai",
    "genai",
    "rag",
    "retrieval augmented",
    "llm",
    "large language model",
    "prompt engineering",
    "responsible ai",
    # Platform / data (Twoday, Attensi, AW Academy, Metier, …)
    "data engineer",
    "data platform",
    "platform engineer",
    "AI platform",
    "business intelligence",
    "data scientist",
    "databricks",
    "snowflake",
    # Software / solutions (Falkor, agentic commerce, Fujitsu, …)
    "software engineer",
    "solutions architect",
    "AI engineer",
    "ML engineer",
    "machine learning engineer",
    "mlops",
    # Enablement / innovation (Six Robotics, Tieto Banktech, …)
    "AI enablement",
    "innovation lead",
    # Academic / research (UiO, Simula, NTNU, HVL, OsloMet, …)
    "postdoc",
    "postdoktor",
    "postdoctoral",
    "post-doctoral",
    "research fellow",
    "research scientist",
    "researcher",
    "forskning",
    "forsker",
    "vitenskapelig",
    "associate professor",
    "universitetslektor",
    "førstelektor",
    "første lektor",
    "førsteamanuensis",
    "første amanuensis",
    "information theory",
)

# FINN.no search queries — industry lanes from the same application set.
DEFAULT_FINN_SEARCH_QUERIES: tuple[str, ...] = (
    # Data
    "data engineer",
    "data scientist",
    "data platform",
    "business intelligence",
    "dataingeniør",
    # AI / ML
    "AI engineer",
    "ML engineer",
    "machine learning",
    "generative AI",
    "agentic AI",
    "RAG",
    "LLM",
    "maskinlæring",
    # Software / platform
    "software engineer",
    "platform engineer",
    "AI platform engineer",
    "solutions architect",
    "tech lead",
    "AI enablement",
)

# FINN.no academic / university search queries (merged with industry set by default).
DEFAULT_ACADEMIC_FINN_SEARCH_QUERIES: tuple[str, ...] = (
    "postdoktor",
    "postdoc",
    "postdoctoral",
    "researcher",
    "research fellow",
    "research scientist",
    "forskning",
    "forsker",
    "førstelektor",
    "førsteamanuensis",
    "universitetslektor",
    "associate professor",
    "vitenskapelig",
    "lektor",
)


def all_default_finn_search_queries() -> tuple[str, ...]:
    """Industry + academic FINN queries (deduped, stable order)."""
    return tuple(merge_unique_terms(list(DEFAULT_FINN_SEARCH_QUERIES), list(DEFAULT_ACADEMIC_FINN_SEARCH_QUERIES)))


def finn_search_queries_for_track(track: str) -> tuple[str, ...]:
    """FINN queries for ``industry``, ``academic``, or ``both`` (default ingest)."""
    if track == "industry":
        return DEFAULT_FINN_SEARCH_QUERIES
    if track == "academic":
        return DEFAULT_ACADEMIC_FINN_SEARCH_QUERIES
    return all_default_finn_search_queries()


def profiles_use_demo_templates(profiles: list[JobProfile] | None = None) -> bool:
    """True when every loaded profile comes from *.demo.md (repo CI / demo mode)."""
    prs = profiles if profiles is not None else load_default_profiles()
    if not prs:
        return True
    return all(p.source_path.name.endswith(".demo.md") for p in prs)


def merge_unique_terms(*groups: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for group in groups:
        for term in group:
            t = term.strip()
            if t:
                seen.setdefault(t, None)
    return list(seen.keys())
