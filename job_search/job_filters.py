"""
Job text filters for ingest and dashboard.

1) **Tech allowlist** — show/keep only ads that contain at least one ICT / AI / CS token
   (finite, curated list; EN + NO). This avoids chasing an infinite exclusion list.

2) **Noise blocklist** — optional extra filter to drop obvious non-tech roles.

Matching: case-insensitive `instr`-style substring on title, jobtitle, description, employer.
Short risky tokens like bare \"it\" are avoided; use \"ikt\", \"software\", etc.

Profile relevance (dashboard overview): require CV keyword/skill overlap
(``score_base > 0`` or non-empty matched keywords/skills). Location-only
(+5) and TEK-only (+25) boosts without profile overlap are not Relevant.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Iterable

# --- Allowlist: at least one hit required when filter is on ------------------------------
# Norwegian + English roles, domains, and common stack terms (substring match).
DEFAULT_TECH_INCLUDE_TERMS: tuple[str, ...] = (
    # Norwegian umbrella & roles
    "ikt",
    "informasjonsteknologi",
    "informasjonssystem",
    "programvare",
    "programutvikling",
    "systemutvikling",
    "programmering",
    "programmerer",
    "utvikler",
    "utvikling",
    "systemarkitekt",
    "IT-arkitekt",
    "løsningsarkitekt",
    "teknolog",
    "dataingeniør",
    "data engineer",
    "systemingeniør",
    "nettverk",
    "nettverks",
    "cyber",
    "sikkerhet IT",
    "informasjonssikkerhet",
    "datasikkerhet",
    "drift IT",
    "systemdrift",
    "applikasjon",
    "integrasjon",
    "digital utvikling",
    "digitalisering",
    "automasjon",
    "automatisering",
    "robot",
    "robotikk",
    "maskinlæring",
    "kunstig intelligens",
    "generative ai",
    "genai",
    "agentic",
    "rag",
    "retrieval augmented",
    "dataanalyt",
    "data scientist",
    "data science",
    "business intelligence",
    "databas",
    "database",
    "sql",
    "big data",
    "datalag",
    "skybasert",
    "sky-",
    "forretningssystem",
    "testing programvare",
    "testutvikler",
    "kvalitetssikring program",
    "devops",
    "forskningsingeniør",
    "forsker teknologi",
    "forskning",
    "forsker",
    "postdoc",
    "postdoktor",
    "postdoctoral",
    "post-doctoral",
    "research fellow",
    "research scientist",
    "vitenskapelig",
    "universitetslektor",
    "førstelektor",
    "første lektor",
    "førsteamanuensis",
    "første amanuensis",
    "associate professor",
    "lektor",
    "lecturer",
    " FoU ",  # spaces reduce false positives
    "fou teknologi",
    # English roles & domains
    "software",
    "developer",
    "programmer",
    "engineer",
    "engineering",
    "architect",
    "fullstack",
    "full-stack",
    "backend",
    "back-end",
    "frontend",
    "front-end",
    "web developer",
    "application developer",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "computational",
    "computer science",
    "informatics",
    "scientific computing",
    "nlp",
    "large language",
    "LLM",
    "prompt engineer",
    "MLOps",
    "data platform",
    "platform engineer",
    "site reliability",
    "sre ",
    "cloud",
    "kubernetes",
    "docker",
    "terraform",
    "ansible",
    "microservice",
    "serverless",
    "API ",
    " REST ",
    "GraphQL",
    "embedded",
    "firmware",
    "hardware engineer",
    "pcb",
    " FPGA ",
    "semiconductor",
    "python",
    "java",
    "typescript",
    "javascript",
    "c++",
    "c#",
    ".net",
    "golang",
    "kotlin",
    "scala",
    "rust",
    "node.js",
    "react ",
    "angular",
    "vue.",
    "django",
    "flask",
    "pytorch",
    "tensor",
    "keras",
    "scikit",
    "hadoop",
    "spark ",
    "kafka",
    "snowflake",
    "databricks",
    "mongodb",
    "postgresql",
    "redis",
    "elasticsearch",
    "linux",
    "unix",
    "network engineer",
    "systems administrator",
    "sysadmin",
    "pentest",
    "penetration test",
    "soc ",
    "threat",
    "vulnerability",
    "compliance techn",
    "IT support",
    "IT-konsulent",
    "IT konsulent",
    "teknisk konsulent",
    "solution consultant",
    "presales",
    "tech lead",
    "technical lead",
    "CTO",
    " CIO ",
    "product owner",  # often IT in NO ads
    "scrum master",
    "agile coach",
    "Jira",
    "confluence",
    "gitlab",
    "github",
    "CI/CD",
    "gitops",
    "SAP ",
    "salesforce",
    "servicenow",
    "dynamics 365",
    "power bi",
    "tableau",
    "looker",
    "RPA",
    "automation",
    "iot",
    "edge computing",
    "blockchain",
    "cryptograph",
    "quantum",  # rare but bounded
)

# Optional blocklist (same as before) — apply *after* allowlist if enabled.
DEFAULT_EXCLUDE_TERMS: tuple[str, ...] = (
    "kokk",
    "kjøkk",
    "kjokken",
    "chef",
    "servitør",
    "servitor",
    "bartender",
    "catering",
    "hotell",
    "restaurant",
    "sykepleier",
    "helsefagarbeider",
    "vernepleier",
    "hjelpepleier",
    "ressurspleier",
    "pleier",
    "nurse",
    "nursing",
    "omsorgsbolig",
    "hjemmehjelp",
    "tilkallingsvikar helse",
    "barnehage",
    "barnevern",
    "familievernkontor",
    "kundeservice",
    "kundebehandler",
    "kunderådgiver",
    "kunderadgiver",
    "call center",
    "callsenter",
    "butikk",
    "butikkmedarbeider",
    "bokhandel",
    "bokhandelansatt",
    "fastlege",
    "fastlegestilling",
    "legestilling",
    "allmennlege",
    "legekontor",
    "sulten på å tjene",
    "sulten pa a tjene",
    "salgsmedarbeider",
    "cashier",
    "customer service",
    "sjåfør",
    "sjofor",
    "lastebil",
    "renhold",
    "rengjøring",
    "rengjoring",
    "vaskehjelp",
    "elektrikerlærling",
    "elektriker",
    "snekker",
    "tømrer",
    "tomrer",
    "murer",
    "lagerarbeider",
    "plukker",
    "truckfører",
    "vekter",
    "vaktmester",
)

# Finance / accounting controller roles — excluded unless clearly IT/ICT controller.
CONTROLLER_KEEP_TERMS: tuple[str, ...] = (
    "it controller",
    "ikt controller",
    "it-controller",
    "ikt-controller",
)


def parse_term_field(text: str) -> list[str]:
    out: list[str] = []
    for part in re.split(r"[,;\n]+", text or ""):
        t = part.strip().casefold()
        if len(t) >= 2:
            out.append(t)
    return out


def _merge_terms_ordered(
    base: Iterable[str],
    custom_text: str,
    extra_cli: Iterable[str] | None = None,
) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for t in list(base) + parse_term_field(custom_text):
        tc = t.strip().casefold()
        if tc and tc not in seen:
            seen.add(tc)
            ordered.append(tc)
    if extra_cli:
        for t in extra_cli:
            tc = t.strip().casefold()
            if len(tc) >= 2 and tc not in seen:
                seen.add(tc)
                ordered.append(tc)
    return tuple(ordered)


def merge_include_terms(
    use_defaults: bool,
    custom_text: str,
    extra_cli: Iterable[str] | None = None,
) -> tuple[str, ...]:
    base = list(DEFAULT_TECH_INCLUDE_TERMS) if use_defaults else []
    return _merge_terms_ordered(base, custom_text, extra_cli)


def merge_exclude_terms(use_defaults: bool, custom_text: str, extra_cli: Iterable[str] | None = None) -> tuple[str, ...]:
    base = list(DEFAULT_EXCLUDE_TERMS) if use_defaults else []
    return _merge_terms_ordered(base, custom_text, extra_cli)


def _filter_text_part(value: object) -> str:
    """Coerce filter fields to str; skip None/NaN/non-strings (pandas empty cells)."""
    return value if isinstance(value, str) else ""


def haystack_for_filter(
    title: object = None,
    jobtitle: object = None,
    description: object = None,
    employer: object = None,
) -> str:
    parts = [
        _filter_text_part(title),
        _filter_text_part(jobtitle),
        _filter_text_part(description),
        _filter_text_part(employer),
    ]
    return " ".join(parts).casefold()


_EDGE_CHAR_RE = r"0-9a-zæøå"


@lru_cache(maxsize=4096)
def _term_pattern(term: str) -> re.Pattern[str] | None:
    text = term.strip().casefold()
    if not text:
        return None
    escaped = re.escape(text)
    escaped = escaped.replace(r"\ ", r"\s+")
    pattern = rf"(?<![{_EDGE_CHAR_RE}]){escaped}(?![{_EDGE_CHAR_RE}])"
    return re.compile(pattern, re.IGNORECASE)


def term_matches(hay: str, term: str) -> bool:
    text = term.strip().casefold()
    if not text:
        return False
    if len(text) <= 2 and text not in ("ai", "go", "r"):
        return False
    pattern = _term_pattern(text)
    if pattern is None:
        return False
    return bool(pattern.search(hay))


def matching_terms(hay: str, terms: Iterable[str]) -> list[str]:
    return [t for t in terms if term_matches(hay, t)]


_SQL_HAY = (
    "LOWER(COALESCE(j.title,'') || ' ' || COALESCE(j.description_text,'') || ' ' || "
    "COALESCE(j.jobtitle,'') || ' ' || COALESCE(j.employer_name,''))"
)


def sql_require_any_include(terms: tuple[str, ...]) -> tuple[str, list[str]]:
    """AND (instr>0 OR ...) — require at least one tech token."""
    if not terms:
        return "", []
    parts = [f"instr({_SQL_HAY}, ?) > 0" for _ in terms]
    sql = " AND (" + " OR ".join(parts) + ")"
    return sql, [t.casefold() for t in terms]


def sql_exclude_fragments(terms: tuple[str, ...]) -> tuple[str, list[str]]:
    if not terms:
        return "", []
    parts = [f"instr({_SQL_HAY}, ?) = 0" for _ in terms]
    sql = " AND " + " AND ".join(parts)
    return sql, [t.casefold() for t in terms]


def matches_any_include_term(hay: str, terms: Iterable[str]) -> bool:
    return any(term_matches(hay, t) for t in terms)


def matches_finance_controller(hay: str) -> bool:
    """True for finance/accounting controller ads; False for IT/ICT controller roles."""
    if not term_matches(hay, "controller"):
        return False
    return not any(term_matches(hay, t) for t in CONTROLLER_KEEP_TERMS)


def matches_exclude_terms(hay: str, terms: Iterable[str]) -> bool:
    if any(term_matches(hay, t) for t in terms):
        return True
    return matches_finance_controller(hay)


def has_profile_relevance(row: dict[str, Any] | Any) -> bool:
    """
    True when a scored job has CV keyword/skill overlap.

    Location-only (+5) and TEK-only (+25) rows with ``score_base == 0`` and no
    matched keywords/skills return False so they do not appear under Relevant.
    """
    base = row.get("score_base") if hasattr(row, "get") else getattr(row, "score_base", 0)
    kw = row.get("matched_keywords") if hasattr(row, "get") else getattr(row, "matched_keywords", None)
    sk = row.get("matched_skills") if hasattr(row, "get") else getattr(row, "matched_skills", None)

    try:
        base_f = float(base) if base is not None else 0.0
    except (TypeError, ValueError):
        base_f = 0.0

    if base_f > 0:
        return True
    if kw is not None and str(kw).strip():
        return True
    if sk is not None and str(sk).strip():
        return True
    return False


def sql_require_profile_relevance() -> str:
    """SQL fragment: require CV keyword/skill overlap (exclude location/TEK-only boosts)."""
    return """
      AND (
          s.score_base > 0
          OR TRIM(COALESCE(s.matched_keywords, '')) != ''
          OR TRIM(COALESCE(s.matched_skills, '')) != ''
      )"""


# --- PhD student openings (seeking candidates to *do* a PhD) ----------------------------
# Filter these out by default; keep postdoc / researcher / "PhD required" roles.
DEFAULT_PHD_STUDENT_EXCLUDE_TERMS: tuple[str, ...] = (
    "phd position",
    "phd fellowship",
    "phd fellow",
    "doktorgradsstipendiat",
    "phd student",
    "doctoral fellowship",
)

PHD_STUDENT_KEEP_TERMS: tuple[str, ...] = (
    "postdoc",
    "postdoktor",
    "postdoctoral",
    "post-doctoral",
    "post doc",
    "researcher",
    "research fellow",
    "research scientist",
    "associate professor",
    "førsteamanuensis",
    "første amanuensis",
    "requires phd",
    "require phd",
    "ph.d. required",
    "phd required",
    "phd is required",
    "doctoral degree required",
    "completed phd",
    "with a phd",
)


def matches_phd_student_opening(haystack: str) -> bool:
    """
    True when the posting is a PhD *student/fellowship* opening (candidate will enroll).

    Postdoc, researcher, and "PhD required" hiring roles return False.
    """
    hay = (haystack or "").casefold()
    if not hay.strip():
        return False
    if any(term_matches(hay, t) for t in PHD_STUDENT_KEEP_TERMS):
        return False
    return any(term_matches(hay, t) for t in DEFAULT_PHD_STUDENT_EXCLUDE_TERMS)


def sql_phd_student_exclude() -> str:
    """SQL fragment: exclude rows whose title/description match PhD-student blocklist."""
    parts: list[str] = []
    for term in DEFAULT_PHD_STUDENT_EXCLUDE_TERMS:
        parts.append(f"instr({_SQL_HAY}, ?) = 0")
    if not parts:
        return ""
    # Keep rows that match any keep-term even if blocklist hits (handled in Python post-filter).
    return " AND " + " AND ".join(parts)


# --- Academic role titles (dashboard academic track) ------------------------------------
# Broad tokens (ingest / legacy SQL). Description hits like bare "forskning" are too noisy
# for dashboard display — use matches_academic_role_display() instead.
ACADEMIC_ROLE_INCLUDE_TERMS: tuple[str, ...] = (
    "postdoc",
    "postdoktor",
    "postdoctoral",
    "post-doctoral",
    "post doc",
    "researcher",
    "research fellow",
    "research scientist",
    "førstelektor",
    "første lektor",
    "førsteamanuensis",
    "første amanuensis",
    "universitetslektor",
    "universitet lektor",
    "associate professor",
    "forsker",
    "vitenskapelig",
    "vitenskapelig stilling",
    "lektor",
    "lecturer",
    "amanuensis",
    "universitet",
    "høyskole",
    "hoyskole",
    "forskning",
    "forskningsstilling",
)

# Title / jobtitle tokens for postdoc, lecturer, and researcher roles (display filter).
ACADEMIC_ROLE_TITLE_TERMS: tuple[str, ...] = (
    "postdoc",
    "postdoktor",
    "postdoctoral",
    "post-doctoral",
    "post doc",
    "researcher",
    "research fellow",
    "research scientist",
    "førstelektor",
    "første lektor",
    "førsteamanuensis",
    "første amanuensis",
    "universitetslektor",
    "universitet lektor",
    "associate professor",
    "vitenskapelig stilling",
    "forskningsstilling",
)

# Weak academic titles that should not appear unless a strong role term is also in the title.
ACADEMIC_WEAK_TITLE_EXCLUDE_TERMS: tuple[str, ...] = (
    "research assistant",
    "research assistants",
    "forskningsassistent",
    "vitenskapelig assistent",
)

# Industry / project-engineering titles excluded unless a strong academic role term is present.
ACADEMIC_ROLE_EXCLUDE_TITLE_TERMS: tuple[str, ...] = (
    "bim coordinator",
    "infrastrukturingeniør",
    "infrastructure engineer",
    "prosjektstilling",
    "prosjektingeniør",
)

# Known university / research employers (substring match on employer_name).
ACADEMIC_RESEARCH_EMPLOYERS: tuple[str, ...] = (
    "universitet",
    "university",
    "høgskole",
    "hoyskole",
    "høyskole",
    "ntnu",
    "uio",
    "oslomet",
    "oslo metropolitan",
    "simula",
    "uit ",
    "nmbu",
    "uis",
    "hvl",
    "mf vitensk",
    "norsk regnesentral",
    "sintef",
    "norwegian school of economics",
    "nhh",
    "bi norwegian",
    "norges miljø",
    "norges miljo",
    "norsk institutt",
    "international research institute",
    "forskningsinstitutt",
)

_SQL_TITLE_EMPLOYER_HAY = (
    "LOWER(COALESCE(j.title,'') || ' ' || COALESCE(j.jobtitle,'') || ' ' || "
    "COALESCE(j.employer_name,''))"
)


def matches_academic_research_employer(employer: str | None) -> bool:
    hay = (employer or "").casefold()
    if not hay.strip():
        return False
    return any(term_matches(hay, term) for term in ACADEMIC_RESEARCH_EMPLOYERS)


def matches_academic_role(hay: str, terms: Iterable[str] | None = None) -> bool:
    """True when title/description/employer matches university or research role vocabulary."""
    use_terms = terms if terms is not None else ACADEMIC_ROLE_INCLUDE_TERMS
    return matches_any_include_term(hay, use_terms)


def matches_academic_role_display(
    title: str | None,
    jobtitle: str | None,
    description: str | None,
    employer: str | None,
) -> bool:
    """
    Stricter dashboard filter: role terms in title/jobtitle, or university employer with
    a role title. Description-only hits (e.g. bare \"forskning\") do not qualify.
    """
    title_only = haystack_for_filter(title, jobtitle, None, None)
    has_role_title = matches_any_include_term(title_only, ACADEMIC_ROLE_TITLE_TERMS)

    blocked = ACADEMIC_WEAK_TITLE_EXCLUDE_TERMS + ACADEMIC_ROLE_EXCLUDE_TITLE_TERMS
    if any(term_matches(title_only, term) for term in blocked):
        if not has_role_title:
            return False

    if has_role_title:
        return True

    if matches_academic_research_employer(employer) and has_role_title:
        return True

    _ = description  # kept for API symmetry; display filter ignores description-only hits
    return False


def sql_require_academic_role(terms: tuple[str, ...] | None = None) -> tuple[str, list[str]]:
    """AND (instr>0 OR ...) — require at least one academic role token."""
    use_terms = terms if terms is not None else ACADEMIC_ROLE_INCLUDE_TERMS
    return sql_require_any_include(use_terms)


def sql_require_academic_role_display() -> tuple[str, list[str]]:
    """SQL pre-filter on title/jobtitle/employer using strict role + university tokens."""
    use_terms = ACADEMIC_ROLE_TITLE_TERMS + ACADEMIC_RESEARCH_EMPLOYERS
    if not use_terms:
        return "", []
    parts = [f"instr({_SQL_TITLE_EMPLOYER_HAY}, ?) > 0" for _ in use_terms]
    sql = " AND (" + " OR ".join(parts) + ")"
    return sql, [t.casefold() for t in use_terms]


def filter_academic_roles_df(df: Any, *, keep_academic_only: bool) -> Any:
    """Drop non-academic rows when keep_academic_only is True (pandas DataFrame)."""
    if not keep_academic_only or df.empty:
        return df
    keep_mask: list[bool] = []
    for _, row in df.iterrows():
        keep_mask.append(
            matches_academic_role_display(
                row.get("title"),
                row.get("jobtitle"),
                row.get("description_text"),
                row.get("employer_name"),
            )
        )
    return df.loc[keep_mask].reset_index(drop=True)
