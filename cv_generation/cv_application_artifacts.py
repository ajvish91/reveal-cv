"""
Supplementary application markdown files beyond final_cv.md.

Used by private_cv apply (deanonymize + PDF), render_cv_pdf (plain layout),
run_cv_tailoring (scaffold notes), and agent docs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Primary CV — deanonymized with --strict in private_cv apply.
CV_MARKDOWN = "final_cv.md"

# Norwegian localized pairs (English canonical for mapping keys).
LOCALIZED_ARTIFACT_PAIRS: tuple[tuple[str, str], ...] = (
    ("final_cv.md", "final_cv_no.md"),
    ("cover_letter.md", "cover_letter_no.md"),
    ("reference_projects.md", "reference_projects_no.md"),
)


@dataclass(frozen=True)
class SupplementaryArtifact:
    filename: str
    label: str
    plain_pdf: bool = True
    """Render as one-column plain PDF, not styled CV layout."""

    @property
    def stem(self) -> str:
        return Path(self.filename).stem


SUPPLEMENTARY_ARTIFACTS: tuple[SupplementaryArtifact, ...] = (
    SupplementaryArtifact("cover_letter.md", "cover letter"),
    SupplementaryArtifact("application_letter.md", "application letter"),
    SupplementaryArtifact("research_proposal.md", "research proposal"),
    SupplementaryArtifact("reference_projects.md", "reference projects"),
)

SUPPLEMENTARY_FILENAMES: tuple[str, ...] = tuple(a.filename for a in SUPPLEMENTARY_ARTIFACTS)

_PLAIN_NAME_MARKERS = (
    "cover_letter",
    "cover-letter",
    "application_letter",
    "application-letter",
    "research_proposal",
    "research-proposal",
    "reference_projects",
    "reference-projects",
    "referanseprosjekter",
)


def supplementary_artifact_filenames() -> tuple[str, ...]:
    return SUPPLEMENTARY_FILENAMES


def supplementary_artifact_for(filename: str) -> SupplementaryArtifact | None:
    for artifact in SUPPLEMENTARY_ARTIFACTS:
        if artifact.filename == filename:
            return artifact
    return None


def is_plain_pdf_markdown(markdown_path: Path, text: str | None = None) -> bool:
    """True when markdown should render as plain one-column PDF (not styled CV)."""
    name = markdown_path.name.lower()
    if any(marker in name for marker in _PLAIN_NAME_MARKERS):
        return True
    body = text if text is not None else markdown_path.read_text(encoding="utf-8")
    lowered = body.lower()
    if "dear " in lowered and "sincerely" in lowered:
        return True
    if name.startswith("research_proposal") or name.startswith("application_letter"):
        return True
    return False


def normalize_upper_name_variants(mapping: dict[str, str]) -> dict[str, str]:
    """
    Add title-case aliases for fully-uppercase personal-name keys.

    Example: ``MITCH EVANS`` → also map ``Mitch Evans`` to the same value.
    """
    expanded = dict(mapping)
    for key, value in mapping.items():
        if not key.isupper():
            continue
        if not all(part.isalpha() or part.isspace() for part in key):
            continue
        words = key.split()
        if len(words) < 2:
            continue
        title = " ".join(word.capitalize() for word in words)
        if title not in expanded:
            expanded[title] = value
    return expanded


_COVER_LETTER_RE = re.compile(
    r"cover\s+letter|søknadstekst|soknadstekst",
    re.IGNORECASE,
)
_RESEARCH_PROPOSAL_RE = re.compile(
    r"research\s+proposal|project\s+description|statement\s+of\s+purpose|"
    r"prosjektskisse|prosjektbeskrivelse",
    re.IGNORECASE,
)
_APPLICATION_LETTER_RE = re.compile(
    r"application\s+letter|letter\s+of\s+(?:motivation|application)|"
    r"qualifications\s+and\s+motivation|motivation\s+letter|"
    r"motivasjonsbrev|søknadsbrev|soknadsbrev",
    re.IGNORECASE,
)
_REFERENCE_PROJECTS_RE = re.compile(
    r"reference\s+projects|referanseprosjekt|beskrivelse\s+av\s+referanse",
    re.IGNORECASE,
)
_ACADEMIC_ROLE_RE = re.compile(
    r"post[- ]?doc|postdoktor|postdoctoral|research\s+fellow|"
    r"researcher\s+in|ph\.?d\.?\s+position",
    re.IGNORECASE,
)
_LETTER_FILENAMES = frozenset({"cover_letter.md", "application_letter.md"})


def detect_supplementary_artifacts(
    job_text: str,
    *,
    track: str | None = None,
) -> list[SupplementaryArtifact]:
    """Heuristic: which supplementary files the posting likely needs."""
    needed: list[SupplementaryArtifact] = []
    by_name = {a.filename: a for a in SUPPLEMENTARY_ARTIFACTS}
    normalized_track = (track or "").strip().lower()

    if _RESEARCH_PROPOSAL_RE.search(job_text):
        needed.append(by_name["research_proposal.md"])
    if _COVER_LETTER_RE.search(job_text):
        needed.append(by_name["cover_letter.md"])
    elif _APPLICATION_LETTER_RE.search(job_text):
        needed.append(by_name["application_letter.md"])
    elif _ACADEMIC_ROLE_RE.search(job_text) and by_name["research_proposal.md"] not in needed:
        # Academic postdoc/researcher calls often want a motivation letter even if not named.
        needed.append(by_name["application_letter.md"])
    if _REFERENCE_PROJECTS_RE.search(job_text):
        needed.append(by_name["reference_projects.md"])

    has_letter = any(a.filename in _LETTER_FILENAMES for a in needed)
    if not has_letter:
        if normalized_track == "academic" or (
            normalized_track != "industry" and _ACADEMIC_ROLE_RE.search(job_text)
        ):
            needed.append(by_name["application_letter.md"])
        elif normalized_track == "industry" or not _ACADEMIC_ROLE_RE.search(job_text):
            needed.append(by_name["cover_letter.md"])


    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[SupplementaryArtifact] = []
    for artifact in needed:
        if artifact.filename in seen:
            continue
        seen.add(artifact.filename)
        out.append(artifact)
    return out


def application_artifacts_markdown(job_text: str, *, role_title: str = "") -> str:
    """Scaffold note written into each new cv_runs/<id>/ folder."""
    detected = detect_supplementary_artifacts(job_text)
    lines = [
        "# Application artifacts",
        "",
        "After `final_cv.md` is assembled, create any supplementary markdown files "
        "required by the posting. `private_cv apply <run>` deanonymizes and renders "
        "PDFs for every file below when it exists in this folder.",
        "",
        "| File | Purpose |",
        "|------|---------|",
        f"| `{CV_MARKDOWN}` | Tailored CV (always) |",
    ]
    for artifact in SUPPLEMENTARY_ARTIFACTS:
        marker = " **← likely for this posting**" if artifact in detected else ""
        lines.append(f"| `{artifact.filename}` | {artifact.label}{marker} |")
    lines.extend(
        [
            "",
            "## Placeholders",
            "",
            "Reuse anonymized tokens from the CV source (`MITCH EVANS`, `master_cv@gmail.com`, "
            "`Prague, Czech Republic`, institution placeholders, etc.). For the applicant name, "
            "use **`MITCH EVANS`** (all caps) in headers and signatures so deanonymize mapping keys match.",
            "",
            "## Generation",
            "",
            "- **Industry:** `cover_letter.md` — motivation/fit letter (`cv_style.py` → `COVER_LETTER_VOICE`); "
            "auto-generated by `run_agent_pipeline` when flagged above.",
            "- **Academic:** `application_letter.md` — qualifications, motivation, link to attached proposal.",
            "- **Research postdoc/researcher:** `research_proposal.md` — project plan when the call requires it.",
            "",
            "Do not invent employers, dates, or experience absent from the source CV.",
            "",
        ]
    )
    if role_title:
        lines.insert(4, f"**Role:** {role_title}")
        lines.insert(5, "")
    if detected:
        names = ", ".join(f"`{a.filename}`" for a in detected)
        lines.append(f"**Detected for this posting:** {names}")
        lines.append("")
    return "\n".join(lines)
