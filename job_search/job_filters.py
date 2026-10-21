"""
Job text filters for ingest and dashboard.

1) **Tech allowlist** — show/keep only ads that contain at least one ICT / AI / CS token
   (finite, curated list; EN + NO). This avoids chasing an infinite exclusion list.

2) **Noise blocklist** — optional extra filter to drop obvious non-tech roles.

Matching: case-insensitive `instr`-style substring on title, jobtitle, description, employer.
Short risky tokens like bare \"it\" are avoided; use \"ikt\", \"software\", etc.

Profile relevance (dashboard overview): require CV keyword/skill overlap
(``score_base > 0`` or non-empty matched keywords/skills). TEK-only (+25)
boosts without profile overlap are not Relevant. Geographic points are not scored.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Any, Iterable

# FINN search cards store only a short teaser, not the ad body. Rows below this
# length need a detail-page backfill before the dashboard can show them.
MIN_FINN_DESCRIPTION_CHARS = 280

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
    "softwareutvikler",
    "systemutvikler",
    "webutvikler",
    "applikasjonsutvikler",
    "apputvikler",
    "frontend-utvikler",
    "backend-utvikler",
    "fullstack-utvikler",
    "full stack-utvikler",
    "ikt-utvikler",
    "programmering",
    "programmerer",
    # Avoid bare "utvikler"/"utvikling" — they hit "utvikler deg", "teamutvikling", salon ads.
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
    "forskar",
    "forskingsformidling",
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
    "frisør",
    "frisor",
    "frisørsalong",
    "frisorsalong",
    "frisørfag",
    "frisorfag",
    "frisørkarriere",
    "frisorkarriere",
    "salong",
    "salongen",
    "cut'n go",
    "cut n go",
    "hairdresser",
    "hairstylist",
    "barber",
    "barbershop",
    "kosmetolog",
    "hudpleie",
    "negledesigner",
    "brynstyling",
    "vippe",
    "vippetekniker",
    "fastlege",
    "fastlegestilling",
    "legestilling",
    "allmennlege",
    "legekontor",
    "sykehjemslege",
    "psykolog",
    "psykologspesialist",
    "terapeut",
    "fysioterapeut",
    "jordmor",
    "tannpleier",
    "miljøterapeut",
    "miljoterapeut",
    "bofellesskap",
    "hjemmetjeneste",
    "heimetenesta",
    "lærer",
    "laerer",
    "adjunkt",
    "pedagog",
    "barne- og ungdomsarbeider",
    "salgsmedarbeider",
    "salgskontor",
    "selger",
    "sulten på å tjene",
    "sulten pa a tjene",
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

# Short tokens that are real tech skills but collide with brands / ordinary words
# (Cut'n Go, "go home", …). Require nearby programming / ML context.
_SHORT_TECH_TERMS = frozenset({"ai", "go", "r"})

_SHORT_TERM_CONTEXT_RE = re.compile(
    r"(?:"
    r"golang|go\s*lang|"
    r"programming|programmer|developer|engineer|engineering|"
    r"backend|front[\s-]?end|fullstack|full[\s-]?stack|"
    r"microservice|services?|kubernetes|docker|python|java|rust|typescript|javascript|"
    r"compiler|framework|runtime|sdk|cli|"
    r"kunstig\s+intelligens|machine\s+learning|artificial\s+intelligence|"
    r"deep\s+learning|neural|llm|mlops|software|informatikk|informatik|"
    r"data\s+scien|data\s+engineer|maskinlæring"
    r")",
    re.IGNORECASE,
)

# Window (chars) around a short-term hit that must contain tech context.
_SHORT_TERM_CONTEXT_WINDOW = 48

_GO_PHRASE_RE = re.compile(
    r"(?:"
    r"(?:written|using|built|programming|developed|services?|backend|apis?)\s+in\s+go"
    r"|go\s+(?:developer|engineer|programmer|lang|language|backend|service|services|module|modules|runtime)"
    r")",
    re.IGNORECASE,
)


@lru_cache(maxsize=4096)
def _term_pattern(term: str) -> re.Pattern[str] | None:
    text = term.strip().casefold()
    if not text:
        return None
    escaped = re.escape(text)
    escaped = escaped.replace(r"\ ", r"\s+")
    # Word-ish boundaries: "data" must not match "database" / "databasen".
    pattern = rf"(?<![{_EDGE_CHAR_RE}]){escaped}(?![{_EDGE_CHAR_RE}])"
    return re.compile(pattern, re.IGNORECASE)


def _short_term_has_tech_context(hay: str, term: str, match: re.Match[str]) -> bool:
    """True when a short ambiguous token sits near genuine tech vocabulary."""
    t = term.casefold()
    if t == "go":
        if re.search(r"(?<![0-9a-zæøå])golang(?![0-9a-zæøå])", hay, re.I):
            return True
        if _GO_PHRASE_RE.search(hay):
            return True
    if t == "ai" and re.search(
        r"(?:artificial\s+intelligence|kunstig\s+intelligens|machine\s+learning|mlops|llm)",
        hay,
        re.I,
    ):
        return True
    start = max(0, match.start() - _SHORT_TERM_CONTEXT_WINDOW)
    end = min(len(hay), match.end() + _SHORT_TERM_CONTEXT_WINDOW)
    return bool(_SHORT_TERM_CONTEXT_RE.search(hay[start:end]))


def term_matches(hay: str, term: str) -> bool:
    """
    Strong / contextual term match against a casefolded haystack.

    Uses word-boundary matching so profile term ``data`` does not hit ``database``,
    and short tokens like ``go`` / ``ai`` require nearby tech context (not brand names).
    """
    text = term.strip().casefold()
    if not text:
        return False
    if len(text) <= 2 and text not in _SHORT_TECH_TERMS:
        return False
    # Cheap reject before the boundary regex (most allowlist terms miss on a given ad).
    if " " in text:
        if not all(tok in hay for tok in text.split() if tok):
            return False
    elif text not in hay:
        return False
    pattern = _term_pattern(text)
    if pattern is None:
        return False
    if text not in _SHORT_TECH_TERMS:
        return bool(pattern.search(hay))
    for match in pattern.finditer(hay):
        if _short_term_has_tech_context(hay, text, match):
            return True
    return False


def matching_terms(hay: str, terms: Iterable[str]) -> list[str]:
    return [t for t in terms if term_matches(hay, t)]


@lru_cache(maxsize=4096)
def _noise_term_pattern(term: str) -> re.Pattern[str] | None:
    """
    Noise/blocklist patterns: require a word start, but allow Norwegian compounds
    to continue (frisør→frisørkarrieren, salong→salongen) for terms of length ≥ 6.
    """
    text = term.strip().casefold()
    if not text:
        return None
    escaped = re.escape(text)
    escaped = escaped.replace(r"\ ", r"\s+")
    if len(text) >= 6:
        pattern = rf"(?<![{_EDGE_CHAR_RE}]){escaped}"
    else:
        pattern = rf"(?<![{_EDGE_CHAR_RE}]){escaped}(?![{_EDGE_CHAR_RE}])"
    return re.compile(pattern, re.IGNORECASE)


def noise_term_matches(hay: str, term: str) -> bool:
    text = term.strip().casefold()
    if not text or len(text) < 2:
        return False
    if " " in text:
        if not all(tok in hay for tok in text.split() if tok):
            return False
    elif text not in hay:
        return False
    pattern = _noise_term_pattern(text)
    if pattern is None:
        return False
    return bool(pattern.search(hay))


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
    if any(noise_term_matches(hay, t) for t in terms):
        return True
    return matches_finance_controller(hay)


def has_profile_relevance(row: dict[str, Any] | Any) -> bool:
    """
    True when a scored job has CV keyword/skill overlap.

    TEK-only (+25) rows with ``score_base == 0`` and no matched keywords/skills
    return False so they do not appear under Relevant.

    Academic roles with a university/research title (e.g. Nynorsk ``forskar``) qualify
    even when the posting text is Norwegian-only and does not hit English CV keywords.
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
    if matches_academic_role_display(
        row.get("title") if hasattr(row, "get") else getattr(row, "title", None),
        row.get("jobtitle") if hasattr(row, "get") else getattr(row, "jobtitle", None),
        None,
        row.get("employer_name") if hasattr(row, "get") else getattr(row, "employer_name", None),
    ):
        return True
    return False


_SQL_TITLE_JOBTITLE_HAY = (
    "LOWER(COALESCE(j.title,'') || ' ' || COALESCE(j.jobtitle,''))"
)


def sql_require_profile_relevance() -> tuple[str, list[str]]:
    """SQL fragment: CV overlap or strict academic role title (exclude TEK-only boosts)."""
    title_parts = [
        f"instr({_SQL_TITLE_JOBTITLE_HAY}, ?) > 0" for _ in ACADEMIC_ROLE_TITLE_TERMS
    ]
    title_or = " OR ".join(title_parts) if title_parts else "0"
    sql = f"""
      AND (
          s.score_base > 0
          OR TRIM(COALESCE(s.matched_keywords, '')) != ''
          OR TRIM(COALESCE(s.matched_skills, '')) != ''
          OR ({title_or})
      )"""
    return sql, [t.casefold() for t in ACADEMIC_ROLE_TITLE_TERMS]


# --- PhD student openings (seeking candidates to *do* a PhD) ----------------------------
# Filter these out by default; keep postdoc / researcher / "PhD required" roles.
# Norwegian "stipendiat" is the standard PhD fellowship title; a postdoc is "postdoktor".
DEFAULT_PHD_STUDENT_EXCLUDE_TERMS: tuple[str, ...] = (
    "phd position",
    "phd fellowship",
    "phd fellow",
    "phd research fellow",
    "phd research fellowship",
    "phd candidate",
    "phd student",
    "phd scholarship",
    "doctoral fellowship",
    "doctoral candidate",
    "doktorgradsstipend",
    "stipendiat",
)

PHD_STUDENT_KEEP_TERMS: tuple[str, ...] = (
    "postdoc",
    "postdoktor",
    "postdoctoral",
    "post-doctoral",
    "post doc",
)

# Title-first regex handles punctuation and Norwegian compounds/inflections:
# "Ph.D Research Fellow", "Ph.d.-stipendiat", "doktorgradsstipendiater",
# "stipendiatstilling". A preceding letter blocks "postdoctoral research fellow".
_PHD_STUDENT_TITLE_RE = re.compile(
    r"(?<![0-9a-zæøå])("
    r"ph\.?\s?d\.?[\s-]+(?:research\s+)?"
    r"(?:fellow(?:ship)?|candidate|position|student|scholarship)"
    r"|doctoral\s+(?:research\s+)?(?:fellow(?:ship)?|candidate)"
    r"|doktorgradsstipend\w*"
    r"|stipendiat\w*"
    r")(?![0-9a-zæøå])",
    re.IGNORECASE,
)

# Description fallback: only unambiguous phrases. Bare "phd candidate" /
# "stipendiat" is omitted because postdoc ads mention supervising PhD candidates.
_PHD_STUDENT_DESCRIPTION_RE = re.compile(
    r"(?<![0-9a-zæøå])"
    r"(?:ph\.?\s?d\.?[\s-]+(?:position|fellowship|student)|doctoral\s+fellowship|"
    r"doktorgradsstipend\w*)"
    r"(?![0-9a-zæøå])",
    re.IGNORECASE,
)

def matches_phd_student_opening(haystack: str, title_haystack: str | None = None) -> bool:
    """
    True when the posting is a PhD *student/fellowship* opening (candidate will enroll).

    Postdoc, researcher, and "PhD required" hiring roles return False. The title is
    checked first so a postdoc ad that mentions "PhD candidates" in its description
    is not hidden.
    """
    hay = (haystack or "").casefold()
    title = (title_haystack if title_haystack is not None else haystack or "").casefold()
    if not hay.strip() and not title.strip():
        return False
    if any(term_matches(title, t) for t in PHD_STUDENT_KEEP_TERMS):
        return False
    if _PHD_STUDENT_TITLE_RE.search(title):
        return True
    return bool(_PHD_STUDENT_DESCRIPTION_RE.search(hay))


def sql_phd_student_exclude() -> tuple[str, list[str]]:
    """SQL pre-filter on title/jobtitle only, with conservative PhD-enrollment terms.

    Description text is deliberately excluded here: a postdoc ad that says
    "supervise PhD candidates" must not be filtered before the Python matcher
    can inspect the title.
    """
    terms = (
        "phd position",
        "phd fellowship",
        "phd fellow",
        "phd research fellow",
        "phd candidate",
        "phd student",
        "phd scholarship",
        "doktorgradsstipend",
        "stipendiat",
    )
    if not terms:
        return "", []
    parts = [f"instr({_SQL_TITLE_JOBTITLE_HAY}, ?) = 0" for _ in terms]
    return " AND " + " AND ".join(parts), [t.casefold() for t in terms]


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
    "forskar",
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
    "forskingsformidling",
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
    "forsker",
    "forskar",
    "vitenskapelig stilling",
    "forskningsstilling",
    "forskingsformidling",
)

# Postdoc titles are ranked above other academic roles in the academic track.
ACADEMIC_POSTDOC_TITLE_TERMS: tuple[str, ...] = (
    "postdoc",
    "postdoktor",
    "postdoctoral",
    "post-doctoral",
    "post doc",
)

_ACADEMIC_POSTDOC_RE = re.compile(
    r"(?<![0-9a-zæøå])(?:postdoc\w*|postdoktor\w*|post-doc\w*|post\s+doc\w*)"
    r"(?![0-9a-zæøå])",
    re.IGNORECASE,
)

# AI/KI topic terms (English + Norwegian) for academic ranking. Short tokens
# ``ai``/``ki`` are matched as standalone words; longer phrases catch variants.
ACADEMIC_AI_TERMS: tuple[str, ...] = (
    "artificial intelligence",
    "kunstig intelligens",
    "machine learning",
    "maskinlæring",
    "deep learning",
    "dyp læring",
    "djup læring",
    "reinforcement learning",
    "forsterkende læring",
    "neural network",
    "nevralt nettverk",
    "nevrale nettverk",
    "large language model",
    "llm",
    "språkmodell",
    "natural language processing",
    "nlp",
    "språkteknologi",
    "computer vision",
    "datasyn",
    "generative ai",
    "generativ ai",
    "agentic ai",
    "agentisk ai",
)

_ACADEMIC_AI_RE = re.compile(
    r"(?<![0-9a-zæøå])(?:"
    r"ai|ki"
    r"|artificial\s+intelligence|kunstig\s+intelligens"
    r"|machine\s+learning|maskinlæring"
    r"|deep\s+learning|d[yj]p\s+læring"
    r"|reinforcement\s+learning|forsterkende\s+læring"
    r"|neural\s+networks?|nevralt\s+nettverk|nevrale\s+nettverk"
    r"|large\s+language\s+models?|llms?|språkmodell(?:er)?"
    r"|natural\s+language\s+processing|nlp|språkteknologi"
    r"|computer\s+vision|datasyn"
    r"|generative\s+ai|generativ\s+ai|generativ\s+kunstig\s+intelligens"
    r"|agentic\s+ai|agentisk\s+ai"
    r")(?![0-9a-zæøå])",
    re.IGNORECASE,
)


def matches_academic_postdoc(title_haystack: str) -> bool:
    """True when a postdoc title (English or Norwegian) is present."""
    return bool(_ACADEMIC_POSTDOC_RE.search((title_haystack or "").casefold()))


def matches_academic_ai_topic(haystack: str) -> bool:
    """True when English/Norwegian AI/KI vocabulary is present."""
    return bool(_ACADEMIC_AI_RE.search((haystack or "").casefold()))


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
    "universitetet",
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
