#!/usr/bin/env python3
"""
CV PDF renderer — dual-column layout (sidebar + main) with automatic pagination.

Supports both tracks: ``# Industry CV`` (corporate) and ``# Academic CV`` (research).
Track-specific sidebar rules live in ``_sidebar_page1_from_cv``; shared contact/icons
and main-column flow apply to both.

Main-column content (profile, experience, education, publications) flows through
a single frame so ReportLab paginates when bullets or profile text change length.
No fixed page-1 role count or per-role bullet cap.

Set LAYOUT_ONLY = True to render placeholders while tuning layout geometry.
"""
from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape

from cv_generation.cv_private import resolve_profile_photo_path
from cv_generation.cv_tracks import is_academic_title

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    FrameBreak,
    Image as RLImage,
    KeepTogether,
    NextPageTemplate,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Layout tuning
# ---------------------------------------------------------------------------
LAYOUT_ONLY = False

PAGE_W, PAGE_H = A4
SIDEBAR_W = 68 * mm * 0.9
SIDEBAR_BG = colors.HexColor("#1F2A3B")
SIDEBAR_PAD_X = 16
SIDEBAR_PAD_RIGHT = 12
SIDEBAR_PAD_TOP = 14
PHOTO_SIZE = 32 * mm
PAD_MAIN_X = 18
MAIN_PAD_TOP = 32
MAIN_PAD_RIGHT = 14
MAIN_HEADER_GAP = 8
MAIN_AFTER_TITLE_GAP = 22
MAIN_COL_W = PAGE_W - SIDEBAR_W - PAD_MAIN_X - MAIN_PAD_RIGHT
EXP_ENTRY_SPACING = 10
EXP_AFTER_BULLETS = 2
MAIN_BULLET_LEFT_INDENT = 14
MAIN_BULLET_BULLET_INDENT = 0
MAIN_BULLET_SPACE_AFTER = 5
MAIN_BULLET_LEADING = 15
PUBLICATION_FONT_SIZE = 10
PUBLICATION_LEADING = 12
PUBLICATION_SPACE_AFTER = 3
SIDEBAR_SECTION_GAP = 14
SIDEBAR_LANG_HOBBY_GAP = 22
SIDEBAR_TITLE_AFTER_GAP = 12
SIDEBAR_TITLE_TO_BULLETS_GAP = 18
SIDEBAR_BULLET_AFTER_GAP = 10
SIDEBAR_CONTACT_TITLE_AFTER_GAP = 16
SIDEBAR_CONTACT_ITEM_PAD = 8
SIDEBAR_CONTACT_SECTION_PAD = 14
SIDEBAR_SKILLS_TITLE_TO_BULLETS_GAP = 10
SIDEBAR_SKILLS_BULLET_AFTER_GAP = 5
SIDEBAR_SPREAD_MAX_GAP = 40
PROFILE_BEFORE_EXP_GAP = 10
PROFILE_FONT_SIZE = 11.5
PROFILE_LEADING = 16
PROFILE_PARA_SPACE_AFTER = 6
ACADEMIC_NAME_TO_FIRST_SECTION_GAP = PROFILE_LEADING * 3  # ~3 lines after name (academic only)

FULL_NAME = "ALEX RIVERA"
ROLE_TITLE = ""
DATE_OF_BIRTH_DEFAULT = "01 Jan 1990"  # demo / placeholder only

CONTACT_KEY_MAP = {
    "github": "github",
    "linkedin": "linkedin",
    "google scholar": "google_scholar",
    "scholar": "google_scholar",
    "orcid": "orcid",
    "email": "email",
    "e-post": "email",
    "epost": "email",
    "phone": "phone",
    "telefon": "phone",
    "location": "location",
    "sted": "location",
}

WORK_PERMIT_CONTACT_KEYS = frozenset({"work permit", "arbeidstillatelse"})


@dataclass
class ExperienceItem:
    role: str
    company: str
    duration: str
    bullets: list[str] = field(default_factory=list)


_ORG_MARKERS = (
    "university",
    "consulting",
    "services",
    " center",
    "center ",
    " group",
    "group ",
    "institute",
    " inc",
    " ltd",
    "corporation",
    " analytics",
    " cloud ",
    " commerce",
    " labs",
    "/",
)
_ROLE_SUFFIXES = (
    " researcher",
    " engineer",
    " developer",
    " assistant",
    " student",
    " manager",
    " scientist",
    " fellow",
    " professor",
    " activities",
)
_ROLE_PREFIXES = (
    "postdoctoral",
    "ph.d.",
    "backend ",
    "research ",
    "software ",
    "integration ",
    "assistant ",
    "professional ",
    "ml ",
)


def _looks_like_organization(text: str) -> bool:
    t = text.lower().strip()
    return any(marker in t for marker in _ORG_MARKERS)


def _looks_like_job_title(text: str) -> bool:
    t = text.lower().strip()
    if any(t.startswith(prefix) for prefix in _ROLE_PREFIXES):
        return True
    return any(t.endswith(suffix) for suffix in _ROLE_SUFFIXES)


def parse_experience_heading(heading: str, subtitle: str) -> tuple[str, str]:
    """Return (company, role) from a ### heading and the following line."""
    heading = heading.strip()
    subtitle = subtitle.strip()
    if not subtitle:
        return heading, ""

    h_org = _looks_like_organization(heading)
    h_role = _looks_like_job_title(heading)
    s_org = _looks_like_organization(subtitle)
    s_role = _looks_like_job_title(subtitle)

    if h_role and s_org:
        return subtitle, heading
    if h_org and s_role:
        return heading, subtitle
    if h_org and not h_role:
        return heading, subtitle
    if h_role and not h_org:
        return subtitle, heading
    return heading, subtitle


@dataclass
class EducationItem:
    degree: str
    institute: str
    duration: str
    field: str = ""
    thesis: str = ""


@dataclass
class CvContent:
    title: str = "Industry CV"
    full_name: str = ""
    role_title: str = ROLE_TITLE
    profile: str = ""
    profile_paragraphs: list[str] = field(default_factory=list)
    date_of_birth: str = ""
    contact: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    experience: list[ExperienceItem] = field(default_factory=list)
    education: list[EducationItem] = field(default_factory=list)
    publications: list[str] = field(default_factory=list)
    summary_bullets: list[str] = field(default_factory=list)
    research_publications: list[str] = field(default_factory=list)
    teaching: list[str] = field(default_factory=list)
    hobbies: list[str] = field(default_factory=list)
    document_language: str = "en"


ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICON_DIR = ASSETS_DIR / "cv_icons"
PHOTO_PLACEHOLDER = ASSETS_DIR / "cv_photo_placeholder.png"
CONTACT_ICON_FILE = {
    "github": ICON_DIR / "github.png",
    "linkedin": ICON_DIR / "linkedin.png",
    "google_scholar": ICON_DIR / "google_scholar.png",
    "orcid": ICON_DIR / "orcid.png",
    "email": ICON_DIR / "email.png",
    "phone": ICON_DIR / "phone.png",
    "location": ICON_DIR / "location.png",
    "birth": ICON_DIR / "cake.png",
}


def _cleanup(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


_INLINE_EMPHASIS_RE = re.compile(r"\*\*(.+?)\*\*|\*(.+?)\*")


def markdown_inline_to_reportlab(text: str) -> str:
    """
    Convert lightweight markdown inline emphasis to ReportLab paragraph markup.

    Supports ``**bold**`` and ``*italic*`` (non-nested). Plain text is XML-escaped.
    Used in Profile and experience bullets only; sidebar stays plain.
    """
    if not text:
        return ""
    if "**" not in text and "*" not in text:
        return xml_escape(text)

    chunks: list[str] = []
    pos = 0
    for match in _INLINE_EMPHASIS_RE.finditer(text):
        if match.start() > pos:
            chunks.append(xml_escape(text[pos : match.start()]))
        if match.group(1) is not None:
            chunks.append(f"<b>{xml_escape(match.group(1))}</b>")
        else:
            chunks.append(f"<i>{xml_escape(match.group(2))}</i>")
        pos = match.end()
    if pos < len(text):
        chunks.append(xml_escape(text[pos:]))
    return "".join(chunks)


def _parse_skills_list(skills_text: str) -> list[str]:
    """
    Parse ## Skills body. Use semicolons to group items that contain commas
    (e.g. ``CI/CD, monitoring``). Comma-only lines split on commas.
    """
    text = skills_text.strip().rstrip(".")
    sep = ";" if ";" in text else ","
    items: list[str] = []
    for part in text.split(sep):
        skill = part.strip().rstrip(".")
        if skill:
            items.append(skill)
    return items


def _split_degree_and_field(degree_line: str) -> tuple[str, str]:
    degree_line = degree_line.strip()
    match = re.match(r"^(.+?)\s*\(([^)]+)\)\s*$", degree_line)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return degree_line, ""


_EDUCATION_DATE_RE = re.compile(r"^\d{4}\s*[-–]\s*\d{4}$")
_EDUCATION_THESIS_RE = re.compile(r"^thesis\s*:", re.I)


def _education_item_from_block(block_lines: list[str]) -> EducationItem | None:
    """Parse one education block (lines until blank line or next ### heading)."""
    if not block_lines:
        return None
    degree_line = block_lines[0].strip()
    if degree_line.startswith("### "):
        degree_line = degree_line[4:].strip()
    if not degree_line:
        return None

    institute = ""
    duration = ""
    field = ""
    thesis = ""
    for cur in block_lines[1:]:
        cur = cur.strip()
        if not cur:
            continue
        if _EDUCATION_THESIS_RE.match(cur):
            thesis = re.split(r":", cur, maxsplit=1)[1].strip()
        elif not institute:
            institute = cur
        elif not duration and _EDUCATION_DATE_RE.match(cur):
            duration = cur
        elif not field:
            field = cur
        elif not thesis:
            thesis = cur

    degree, parsed_field = _split_degree_and_field(degree_line)
    if parsed_field and not field:
        field = parsed_field
    return EducationItem(
        degree=degree,
        institute=institute,
        duration=duration,
        field=field,
        thesis=thesis,
    )


def _parse_education_bullet_line(line: str) -> EducationItem:
    """Parse legacy one-line bullets: Degree (Field), Institute (dates). Thesis: …"""
    text = line.strip().rstrip(".")
    thesis = ""
    thesis_match = re.search(r"\.?\s*Thesis:\s*(.+)$", text, flags=re.I)
    if thesis_match:
        thesis = thesis_match.group(1).strip().rstrip(".")
        text = text[: thesis_match.start()].strip().rstrip(".")

    duration = ""
    dates_match = re.search(r"\((\d{4}\s*[-–]\s*\d{4})\)\s*\.?\s*$", text)
    if dates_match:
        duration = dates_match.group(1).strip()
        text = text[: dates_match.start()].strip().rstrip(".")

    degree, institute = "", ""
    if "," in text:
        degree, institute = [part.strip() for part in text.rsplit(",", 1)]
    else:
        degree = text

    degree, field = _split_degree_and_field(degree)
    return EducationItem(
        degree=degree,
        institute=institute,
        duration=duration,
        field=field,
        thesis=thesis,
    )


def _read_section_value(lines: list[str], start: int) -> tuple[str, int]:
    """Read first non-empty line in a section (skips blank lines after ## Heading)."""
    i = start
    while i < len(lines) and not lines[i].startswith("## "):
        cur = lines[i].strip()
        if cur:
            return cur, i + 1
        i += 1
    return "", i


def _parse_bullet_section(lines: list[str], start: int) -> tuple[list[str], int]:
    items: list[str] = []
    i = start
    while i < len(lines) and not lines[i].startswith("## "):
        cur = lines[i].strip()
        if cur.startswith("- "):
            items.append(cur[2:].strip())
        i += 1
    return items, i


def _detect_document_language(markdown_text: str) -> str:
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            heading = line[2:].strip().lower()
            if "bransje" in heading or heading == "cv" or "akademisk" in heading:
                return "no"
            break
    if re.search(r"^## profil\s*$", markdown_text, re.MULTILINE | re.IGNORECASE):
        return "no"
    return "en"


def _pdf_label(cv: CvContent, english: str, *, main: bool = False) -> str:
    if (cv.document_language or "en").lower() != "no":
        return english
    from cv_generation.cv_style import MAIN_LABELS_NO, SIDEBAR_LABELS_NO

    table = MAIN_LABELS_NO if main else SIDEBAR_LABELS_NO
    return table.get(english, english)


def parse_cv_markdown(markdown_text: str) -> CvContent:
    lines = markdown_text.splitlines()
    cv = CvContent()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        lower = line.lower()
        if line.startswith("# "):
            cv.title = line[2:].strip() or cv.title
        elif lower == "## name" or lower == "## navn":
            value, i = _read_section_value(lines, i + 1)
            if value:
                cv.full_name = value
            continue
        elif lower in ("## role", "## title", "## stilling"):
            value, i = _read_section_value(lines, i + 1)
            if value:
                cv.role_title = value
            continue
        elif lower in ("## summary", "## sammendrag"):
            cv.summary_bullets, i = _parse_bullet_section(lines, i + 1)
            continue
        elif lower in ("## profile", "## profil"):
            i += 1
            paragraphs: list[str] = []
            current: list[str] = []
            while i < len(lines) and not lines[i].startswith("## "):
                if lines[i].strip():
                    current.append(lines[i].strip())
                elif current:
                    paragraphs.append(_cleanup(" ".join(current)))
                    current = []
                i += 1
            if current:
                paragraphs.append(_cleanup(" ".join(current)))
            cv.profile_paragraphs = paragraphs
            cv.profile = "\n\n".join(paragraphs)
            continue
        elif lower in ("## date of birth", "## dob", "## birth date", "## fødselsdato"):
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                cur = lines[i].strip()
                if cur.startswith("- "):
                    cv.date_of_birth = cur[2:].strip()
                    break
                if cur:
                    cv.date_of_birth = cur
                    break
                i += 1
            continue
        elif lower == "## contact" or lower == "## kontakt":
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                cur = lines[i].strip()
                if cur.startswith("- "):
                    cv.contact.append(cur[2:].strip())
                i += 1
            continue
        elif lower in ("## skills", "## ferdigheter", "## technical skills"):
            i += 1
            buff: list[str] = []
            while i < len(lines) and not lines[i].startswith("## "):
                if lines[i].strip():
                    buff.append(lines[i].strip())
                i += 1
            skills_text = _cleanup(" ".join(buff))
            cv.skills = _parse_skills_list(skills_text)
            continue
        elif lower == "## languages" or lower == "## språk":
            cv.languages, i = _parse_bullet_section(lines, i + 1)
            continue
        elif lower in ("## experience", "## erfaring", "## research experience", "## forskningserfaring"):
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                if lines[i].startswith("### "):
                    heading = lines[i][4:].strip()
                    subtitle = ""
                    duration = ""
                    bullets: list[str] = []
                    i += 1
                    while i < len(lines) and not lines[i].startswith("### ") and not lines[i].startswith("## "):
                        cur = lines[i].strip()
                        if cur.startswith("- "):
                            bullets.append(cur[2:].strip())
                        elif cur and not subtitle:
                            subtitle = cur
                        elif cur and not duration:
                            duration = cur
                        i += 1
                    company, role = parse_experience_heading(heading, subtitle)
                    cv.experience.append(
                        ExperienceItem(role=role, company=company, duration=duration, bullets=bullets)
                    )
                    continue
                i += 1
            continue
        elif lower == "## education" or lower == "## utdanning":
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                cur = lines[i].strip()
                if not cur:
                    i += 1
                    continue
                if cur.startswith("- "):
                    cv.education.append(_parse_education_bullet_line(cur[2:]))
                    i += 1
                    continue

                block_lines: list[str] = []
                while i < len(lines) and not lines[i].startswith("## "):
                    line = lines[i]
                    stripped = line.strip()
                    if not stripped:
                        i += 1
                        break
                    if stripped.startswith("- "):
                        break
                    if line.startswith("### ") and block_lines:
                        break
                    if line.startswith("### "):
                        block_lines.append(line[4:].strip())
                    else:
                        block_lines.append(stripped)
                    i += 1

                item = _education_item_from_block(block_lines)
                if item is not None:
                    cv.education.append(item)
            continue
        elif lower in ("## research and publications", "## forskning og publikasjoner"):
            i += 1
            research_lines: list[str] = []
            while i < len(lines) and not lines[i].startswith("## "):
                cur = lines[i].strip()
                if cur.startswith("- "):
                    research_lines.append(cur[2:].strip())
                elif cur:
                    research_lines.append(cur)
                i += 1
            cv.research_publications = research_lines
            continue
        elif lower in ("## teaching and supervision", "## undervisning og veiledning"):
            cv.teaching, i = _parse_bullet_section(lines, i + 1)
            continue
        elif lower in ("## selected publications", "## utvalgte publikasjoner"):
            cv.publications, i = _parse_bullet_section(lines, i + 1)
            continue
        elif lower == "## hobbies" or lower == "## hobbyer":
            cv.hobbies, i = _parse_bullet_section(lines, i + 1)
            continue
        i += 1
    cv.document_language = _detect_document_language(markdown_text)
    return cv


def _styles(styles) -> dict[str, ParagraphStyle]:
    return {
        "sidebar_title": ParagraphStyle(
            "sidebar_title",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=colors.white,
            spaceAfter=SIDEBAR_TITLE_AFTER_GAP,
        ),
        "sidebar_body": ParagraphStyle(
            "sidebar_body",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.white,
            leading=14,
        ),
        "sidebar_bullet": ParagraphStyle(
            "sidebar_bullet",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.white,
            leading=17,
            leftIndent=10,
            firstLineIndent=-8,
            bulletIndent=0,
            spaceAfter=SIDEBAR_BULLET_AFTER_GAP,
        ),
        "name": ParagraphStyle(
            "name",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=30,
            textColor=colors.HexColor("#0E1A2A"),
            spaceAfter=6,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#3A4C62"),
            spaceAfter=MAIN_AFTER_TITLE_GAP,
        ),
        "section": ParagraphStyle(
            "section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=16,
            textColor=colors.HexColor("#1E2E44"),
            spaceBefore=4,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=styles["Normal"],
            fontSize=12,
            leading=14,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#1C1C1C"),
        ),
        "profile": ParagraphStyle(
            "profile",
            parent=styles["Normal"],
            fontSize=PROFILE_FONT_SIZE,
            leading=PROFILE_LEADING,
            alignment=TA_LEFT,
            spaceAfter=PROFILE_PARA_SPACE_AFTER,
            textColor=colors.HexColor("#2A2A2A"),
        ),
        "company": ParagraphStyle(
            "company",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            textColor=colors.HexColor("#1C1C1C"),
            spaceAfter=1,
        ),
        "role": ParagraphStyle(
            "role",
            parent=styles["Normal"],
            fontSize=11,
            leading=13,
            textColor=colors.HexColor("#5D6A7A"),
            spaceAfter=0,
        ),
        "edu_degree": ParagraphStyle(
            "edu_degree",
            parent=styles["Normal"],
            fontSize=11,
            leading=13,
            textColor=colors.HexColor("#1C1C1C"),
            spaceAfter=0,
        ),
        "date": ParagraphStyle(
            "date",
            parent=styles["Normal"],
            fontSize=10,
            leading=12,
            alignment=TA_RIGHT,
            textColor=colors.HexColor("#5D6A7A"),
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=styles["Normal"],
            fontSize=12,
            leading=MAIN_BULLET_LEADING,
            leftIndent=MAIN_BULLET_LEFT_INDENT,
            bulletIndent=MAIN_BULLET_BULLET_INDENT,
            firstLineIndent=0,
            alignment=TA_LEFT,
            spaceAfter=MAIN_BULLET_SPACE_AFTER,
            textColor=colors.HexColor("#202020"),
        ),
        "publication": ParagraphStyle(
            "publication",
            parent=styles["Normal"],
            fontSize=PUBLICATION_FONT_SIZE,
            leading=PUBLICATION_LEADING,
            leftIndent=MAIN_BULLET_LEFT_INDENT,
            bulletIndent=MAIN_BULLET_BULLET_INDENT,
            firstLineIndent=0,
            alignment=TA_LEFT,
            spaceAfter=PUBLICATION_SPACE_AFTER,
            textColor=colors.HexColor("#202020"),
        ),
        "wire": ParagraphStyle(
            "wire",
            parent=styles["Normal"],
            fontSize=9,
            leading=11,
            textColor=colors.HexColor("#C5CCD3"),
        ),
    }


def _sidebar_inner_w() -> float:
    return SIDEBAR_W - SIDEBAR_PAD_X - SIDEBAR_PAD_RIGHT


def _sidebar_frame_height() -> float:
    return PAGE_H - 2 * SIDEBAR_PAD_TOP


def _flowables_height(flowables: list, width: float) -> float:
    total = 0.0
    for flowable in flowables:
        _, height = flowable.wrap(width, 1e6)
        total += height
    return total


def _spread_gap(
    available: float,
    content_h: float,
    between_count: int,
    min_gap: float,
    *,
    max_gap: float | None = SIDEBAR_SPREAD_MAX_GAP,
) -> float:
    if between_count <= 0:
        return min_gap
    extra = available - content_h - (2 * min_gap)
    gap = max(min_gap, extra / between_count) if extra > 0 else min_gap
    if max_gap is None:
        return gap
    return min(gap, max_gap)


def _spread_sections_vertically(
    sections: list[list],
    width: float,
    *,
    available_height: float | None = None,
    min_gap: float = SIDEBAR_SECTION_GAP,
    max_gap: float | None = SIDEBAR_SPREAD_MAX_GAP,
) -> list:
    """Insert flexible gaps between sidebar sections to fill available height."""
    if not sections:
        return []
    heights = [_flowables_height(section, width) for section in sections]
    content_h = sum(heights)
    avail = available_height if available_height is not None else _sidebar_frame_height()
    gap_slots = len(sections) + 1
    gap = _spread_gap(avail, content_h, gap_slots, min_gap, max_gap=max_gap)

    spread: list = []
    for index, section in enumerate(sections):
        spread.append(Spacer(1, gap))
        spread.extend(section)
    spread.append(Spacer(1, gap))
    return spread


def _draw_flowables_top_down(canvas, flowables: list, x: float, y_top: float, width: float) -> float:
    y = y_top
    for flowable in flowables:
        _, height = flowable.wrap(width, 1e6)
        flowable.drawOn(canvas, x, y - height)
        y -= height
    return y


def _draw_spread_sections_on_canvas(
    canvas,
    sections: list[list],
    x: float,
    width: float,
    y_top: float,
    y_bottom: float,
    min_gap: float = SIDEBAR_SECTION_GAP,
    *,
    max_gap: float | None = None,
) -> None:
    """Spread sections vertically to fill the sidebar."""
    if not sections:
        return
    heights = [_flowables_height(section, width) for section in sections]
    content_h = sum(heights)
    avail = y_top - y_bottom
    gap_slots = len(sections) + 1
    gap = _spread_gap(avail, content_h, gap_slots, min_gap, max_gap=max_gap)
    y = y_top - gap
    for section in sections:
        y = _draw_flowables_top_down(canvas, section, x, y, width)
        y -= gap


def _draw_centered_sidebar_sections_on_canvas(
    canvas,
    sections: list[list],
    x: float,
    width: float,
    y_top: float,
    y_bottom: float,
    between_gap: float = SIDEBAR_LANG_HOBBY_GAP,
) -> None:
    """Center languages + hobbies as one block; fixed gap between sections, equal margin above/below."""
    if not sections:
        return
    heights = [_flowables_height(section, width) for section in sections]
    internal_gaps = between_gap * max(len(sections) - 1, 0)
    content_h = sum(heights) + internal_gaps
    avail = y_top - y_bottom
    block_top = y_bottom + (avail + content_h) / 2
    y = block_top
    for index, section in enumerate(sections):
        y = _draw_flowables_top_down(canvas, section, x, y, width)
        if index < len(sections) - 1:
            y -= between_gap


def _ensure_photo_placeholder() -> Path:
    """Circular PNG placeholder for sidebar headshot when no private photo is configured."""
    if PHOTO_PLACEHOLDER.is_file():
        return PHOTO_PLACEHOLDER

    from PIL import Image, ImageDraw

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    size = 256
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    margin = 6
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(186, 196, 208, 255),
        outline=(232, 238, 245, 255),
        width=3,
    )
    cx, cy = size // 2, size // 2 + 8
    draw.ellipse([cx - 34, cy - 72, cx + 34, cy - 8], fill=(148, 160, 176, 255))
    draw.ellipse([cx - 58, cy + 4, cx + 58, cy + 78], fill=(148, 160, 176, 255))
    im.save(PHOTO_PLACEHOLDER)
    return PHOTO_PLACEHOLDER


def _prepare_sidebar_photo_file(source: Path) -> Path:
    """Center-crop to square and apply a circular mask (matches sidebar headshot style)."""
    from PIL import Image, ImageDraw

    im = Image.open(source).convert("RGBA")
    width, height = im.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    im = im.crop((left, top, left + side, top + side))
    size = 512
    im = im.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
    im.putalpha(mask)
    handle = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    im.save(handle.name, format="PNG")
    handle.close()
    return Path(handle.name)


def resolve_sidebar_photo_path(profile_photo: str | Path | None = None) -> Path:
    """Private photo (env/mapping/CLI) or in-repo placeholder."""
    private = resolve_profile_photo_path(profile_photo)
    if private is not None:
        try:
            return _prepare_sidebar_photo_file(private)
        except Exception:
            return private
    return _ensure_photo_placeholder()


def _sidebar_photo_block(profile_photo: str | Path | None = None) -> list:
    inner = _sidebar_inner_w()
    photo_path = resolve_sidebar_photo_path(profile_photo)
    photo = RLImage(str(photo_path), width=PHOTO_SIZE, height=PHOTO_SIZE)
    block = Table([[photo]], colWidths=[inner])
    block.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [block, Spacer(1, 14)]


def _icon_row(
    icon_key: str,
    label: str,
    st: dict[str, ParagraphStyle],
    *,
    item_pad: float = 4,
) -> Table | Paragraph:
    icon_path = CONTACT_ICON_FILE.get(icon_key)
    inner = _sidebar_inner_w()
    icon_col = 7 * mm
    text_col = max(inner - icon_col, 20 * mm)
    if icon_path and icon_path.is_file():
        row = Table(
            [[RLImage(str(icon_path), width=5 * mm, height=5 * mm), Paragraph(label, st["sidebar_body"])]],
            colWidths=[icon_col, text_col],
        )
        row.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), item_pad),
                ]
            )
        )
        return row
    return Paragraph(label, st["sidebar_body"])


def _contact_icon_key(line: str) -> tuple[str, str]:
    if ":" in line:
        key, value = line.split(":", 1)
        key_lower = key.strip().lower()
        if key_lower in WORK_PERMIT_CONTACT_KEYS:
            return "work_permit", value.strip()
        return CONTACT_KEY_MAP.get(key_lower, ""), value.strip()
    return "", line.strip()


def _contact_href(icon_key: str, value: str) -> str:
    text = value.strip()
    if icon_key == "email":
        email = text.removeprefix("mailto:").strip()
        return f"mailto:{email}"
    if icon_key == "phone":
        digits = re.sub(r"[^\d+]", "", text)
        return f"tel:{digits}" if digits else ""
    if icon_key in ("github", "linkedin", "google_scholar", "orcid"):
        if text.startswith(("http://", "https://")):
            return text
        return f"https://{text.lstrip('/')}"
    return ""


def _social_profile_label(icon_key: str, value: str) -> str:
    href = _contact_href(icon_key, value)
    if not href:
        return value.strip()
    path = urlparse(href).path.strip("/")
    if not path:
        return value.strip()
    if icon_key == "linkedin":
        parts = path.split("/")
        if len(parts) >= 2 and parts[0] == "in":
            return parts[1]
        return parts[-1]
    if icon_key == "github":
        return path.split("/")[0]
    if icon_key == "google_scholar":
        return "Google Scholar"
    if icon_key == "orcid":
        return "ORCID"
    return path.split("/")[-1]


def _contact_paragraph_markup(icon_key: str, value: str) -> str:
    """Build ReportLab paragraph XML: hyperlinks for URLs/email/phone; plain text for location."""
    text = value.strip()
    if not text:
        return ""
    if icon_key in ("github", "linkedin", "google_scholar", "orcid", "email", "phone"):
        href = _contact_href(icon_key, text)
        if not href:
            return xml_escape(text)
        if icon_key in ("github", "linkedin"):
            label = _social_profile_label(icon_key, text)
            host = urlparse(href).netloc + urlparse(href).path
            host = host.rstrip("/")
            return (
                f'<a href="{xml_escape(href)}" color="white">{xml_escape(label)}</a>'
                f' <font size="9" color="#B8C4D4">{xml_escape(host)}</font>'
            )
        if icon_key in ("google_scholar", "orcid"):
            label = _social_profile_label(icon_key, text)
            return f'<a href="{xml_escape(href)}" color="white">{xml_escape(label)}</a>'
        elif icon_key == "email":
            label = text.removeprefix("mailto:").strip()
        else:
            label = text
        return f'<a href="{xml_escape(href)}" color="white">{xml_escape(label)}</a>'
    return xml_escape(text)


def _experience_header_row(
    item: ExperienceItem,
    st: dict[str, ParagraphStyle],
    col_width: float,
) -> Table:
    """Company first, then role; dates right-aligned."""
    left_parts: list = []
    if item.company:
        left_parts.append(Paragraph(item.company, st["company"]))
    if item.role:
        left_parts.append(Paragraph(item.role, st["role"]))
    elif not item.company:
        left_parts.append(Paragraph("", st["role"]))

    left_cell = left_parts if left_parts else [Paragraph("", st["role"])]
    date_cell = Paragraph(item.duration, st["date"]) if item.duration else Paragraph("", st["date"])

    date_w = col_width * 0.30
    row = Table(
        [[left_cell, date_cell]],
        colWidths=[col_width - date_w, date_w],
        splitByRow=0,
    )
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return row


def _education_degree_field_line(item: EducationItem) -> str:
    if item.degree and item.field:
        return f"{item.degree}, {item.field}"
    return item.degree or item.field


def _education_header_row(
    item: EducationItem,
    st: dict[str, ParagraphStyle],
    col_width: float,
) -> Table:
    """Institute emphasized on the left; degree and field as subtitle; dates on the right."""
    left_parts: list = []
    if item.institute:
        left_parts.append(Paragraph(item.institute, st["company"]))
    elif item.degree:
        left_parts.append(Paragraph(item.degree, st["company"]))
    degree_field = _education_degree_field_line(item)
    if degree_field and item.institute:
        left_parts.append(Paragraph(degree_field, st["edu_degree"]))

    left_cell = left_parts if left_parts else [Paragraph("", st["role"])]
    date_cell = Paragraph(item.duration, st["date"]) if item.duration else Paragraph("", st["date"])

    date_w = col_width * 0.30
    row = Table(
        [[left_cell, date_cell]],
        colWidths=[col_width - date_w, date_w],
        splitByRow=0,
    )
    row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return row


def _education_flowables(
    items: list[EducationItem],
    st: dict[str, ParagraphStyle],
    col_width: float,
) -> list:
    flowables: list = []
    for idx, item in enumerate(items):
        entry: list = []
        if idx > 0:
            entry.append(Spacer(1, EXP_ENTRY_SPACING))
        entry.append(_education_header_row(item, st, col_width))
        entry.append(Spacer(1, 3))
        if item.thesis:
            thesis_text = item.thesis if item.thesis.lower().startswith("thesis:") else f"Thesis: {item.thesis}"
            entry.append(Paragraph(thesis_text, st["role"]))
        entry.append(Spacer(1, EXP_AFTER_BULLETS))
        flowables.extend(entry)
    return flowables


def _experience_flowables(
    items: list[ExperienceItem],
    st: dict[str, ParagraphStyle],
    col_width: float,
) -> list:
    flowables: list = []
    for idx, item in enumerate(items):
        entry: list = []
        if idx > 0:
            entry.append(Spacer(1, EXP_ENTRY_SPACING))
        entry.append(_experience_header_row(item, st, col_width))
        entry.append(Spacer(1, 3))
        for bullet in item.bullets:
            entry.append(_ats_list_paragraph(bullet, st["bullet"]))
        entry.append(Spacer(1, EXP_AFTER_BULLETS))
        flowables.append(KeepTogether(entry))
    return flowables


def _profile_paragraphs(cv: CvContent) -> list[str]:
    from cv_generation.cv_style import normalize_profile_paragraphs

    if cv.profile_paragraphs:
        paras = [p for p in cv.profile_paragraphs if p.strip()]
    else:
        text = (cv.profile or "").strip()
        if not text:
            return []
        if "\n\n" in text:
            paras = [p.strip() for p in text.split("\n\n") if p.strip()]
        else:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            if len(sentences) <= 2:
                paras = [text]
            else:
                mid = (len(sentences) + 1) // 2
                paras = [" ".join(sentences[:mid]), " ".join(sentences[mid:])]
    limited, warnings = normalize_profile_paragraphs(paras)
    for warning in warnings:
        print(f"Warning: CV profile — {warning}", flush=True)
    return limited


def _profile_flowables(cv: CvContent, st: dict[str, ParagraphStyle]) -> list:
    flowables: list = []
    paras = _profile_paragraphs(cv)
    style = st["profile"]
    for idx, para in enumerate(paras):
        last = idx == len(paras) - 1
        flowables.append(
            Paragraph(
                markdown_inline_to_reportlab(para),
                ParagraphStyle(
                    f"profile_{idx}",
                    parent=style,
                    spaceAfter=0 if last else PROFILE_PARA_SPACE_AFTER,
                ),
            )
        )
    return flowables


def _ats_list_paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    """Hyphen bullet via bulletText for hanging indents; left-aligned body for even word spacing."""
    body = text.strip()
    if body.startswith("- "):
        body = body[2:].strip()
    elif body.startswith("-"):
        body = body[1:].strip()
    return Paragraph(markdown_inline_to_reportlab(body), style, bulletText="-")


def _sidebar_bullet_list(
    items: list[str],
    st: dict[str, ParagraphStyle],
    *,
    bullet_after_gap: float | None = None,
) -> list:
    bullet_style = st["sidebar_bullet"]
    if bullet_after_gap is not None:
        bullet_style = ParagraphStyle(
            "sidebar_bullet_compact",
            parent=bullet_style,
            spaceAfter=bullet_after_gap,
        )
    flowables: list = []
    for item in items:
        text = item.strip()
        if text:
            flowables.append(_ats_list_paragraph(text, bullet_style))
    return flowables


def _sidebar_section_title(
    title: str,
    st: dict[str, ParagraphStyle],
    *,
    space_after: float | None = None,
) -> Paragraph:
    style = st["sidebar_title"]
    if space_after is not None:
        style = ParagraphStyle(
            f"sidebar_title_{title.lower()}",
            parent=style,
            spaceAfter=space_after,
        )
    return Paragraph(title, style)


def _sidebar_contact_section(cv: CvContent, st: dict[str, ParagraphStyle]) -> list:
    order = ["phone", "email", "location", "linkedin", "github", "google_scholar", "orcid"]
    icon_lines: list[tuple[str, str]] = []
    work_permit_lines: list[str] = []
    for line in cv.contact:
        icon_key, value = _contact_icon_key(line)
        if not value:
            continue
        if icon_key == "work_permit":
            work_permit_lines.append(value)
        else:
            icon_lines.append((icon_key, value))
    icon_lines.sort(key=lambda kv: order.index(kv[0]) if kv[0] in order else len(order))

    section: list = [
        _sidebar_section_title(_pdf_label(cv, "CONTACT"), st, space_after=SIDEBAR_CONTACT_TITLE_AFTER_GAP)
    ]
    for icon_key, value in icon_lines:
        markup = _contact_paragraph_markup(icon_key, value)
        if not markup:
            continue
        if icon_key:
            section.append(
                _icon_row(icon_key, markup, st, item_pad=SIDEBAR_CONTACT_ITEM_PAD)
            )
        else:
            section.append(Paragraph(markup, st["sidebar_body"]))
    for permit_text in work_permit_lines:
        section.append(Paragraph(xml_escape(permit_text), st["sidebar_body"]))
    section.append(Spacer(1, SIDEBAR_CONTACT_SECTION_PAD))
    return section


def _sidebar_titled_bullet_section(
    title: str,
    items: list[str],
    st: dict[str, ParagraphStyle],
    *,
    title_to_bullets_gap: float | None = None,
    bullet_after_gap: float | None = None,
) -> list:
    gap = (
        title_to_bullets_gap
        if title_to_bullets_gap is not None
        else SIDEBAR_TITLE_TO_BULLETS_GAP
    )
    section: list = [
        Paragraph(title, st["sidebar_title"]),
        Spacer(1, gap),
    ]
    if items:
        section.extend(_sidebar_bullet_list(items, st, bullet_after_gap=bullet_after_gap))
    else:
        section.append(Paragraph("—", st["sidebar_body"]))
    return section


def _sidebar_skills_section(cv: CvContent, st: dict[str, ParagraphStyle]) -> list:
    return _sidebar_titled_bullet_section(
        _pdf_label(cv, "SKILLS"),
        cv.skills,
        st,
        title_to_bullets_gap=SIDEBAR_SKILLS_TITLE_TO_BULLETS_GAP,
        bullet_after_gap=SIDEBAR_SKILLS_BULLET_AFTER_GAP,
    )


def _is_academic_cv(cv: CvContent) -> bool:
    return is_academic_title(cv.title)


def _is_industry_cv(cv: CvContent) -> bool:
    return not _is_academic_cv(cv)


def _compact_sidebar_stack(page1_sections: list[list]) -> list:
    """Fixed gaps between sidebar sections (no vertical stretch)."""
    stacked: list = [Spacer(1, SIDEBAR_SECTION_GAP)]
    for index, section in enumerate(page1_sections):
        stacked.extend(section)
        if index < len(page1_sections) - 1:
            stacked.append(Spacer(1, SIDEBAR_SECTION_GAP))
    return stacked


def _sidebar_languages_hobbies_sections(cv: CvContent, st: dict[str, ParagraphStyle]) -> list[list]:
    sections: list[list] = []
    if cv.languages:
        sections.append(_sidebar_titled_bullet_section(_pdf_label(cv, "LANGUAGES"), cv.languages, st))
    if cv.hobbies:
        sections.append(_sidebar_titled_bullet_section(_pdf_label(cv, "HOBBIES"), cv.hobbies, st))
    return sections


def _sidebar_page1_from_cv(
    cv: CvContent,
    st: dict[str, ParagraphStyle],
    *,
    profile_photo: str | Path | None = None,
) -> tuple[list, list[list]]:
    """
    Sidebar layout by track.

    Industry (corporate): page 1 = contact + skills (spread when tall); page 2 canvas = languages + hobbies.
    Academic: page 1 = contact + skills + languages (compact stack); page 2 canvas = hobbies only.
    """
    inner_w = _sidebar_inner_w()
    prefix: list = []
    prefix.extend(_sidebar_photo_block(profile_photo))
    if cv.date_of_birth:
        prefix.append(_icon_row("birth", cv.date_of_birth, st))
        prefix.append(Spacer(1, 12))

    page1_sections = [
        _sidebar_contact_section(cv, st),
        _sidebar_skills_section(cv, st),
    ]

    if _is_academic_cv(cv):
        if cv.languages:
            page1_sections.append(
                _sidebar_titled_bullet_section(_pdf_label(cv, "LANGUAGES"), cv.languages, st)
            )
        tail_sections: list[list] = []
        if cv.hobbies:
            tail_sections.append(
                _sidebar_titled_bullet_section(_pdf_label(cv, "HOBBIES"), cv.hobbies, st)
            )
    else:
        # Industry / corporate: unchanged — languages stay on continuation sidebar.
        tail_sections = _sidebar_languages_hobbies_sections(cv, st)

    prefix_h = _flowables_height(prefix, inner_w)
    avail = max(_sidebar_frame_height() - prefix_h, 80)

    sections_h = sum(_flowables_height(sec, inner_w) for sec in page1_sections)
    gap_slots = len(page1_sections) + 1
    fits_compact = sections_h + gap_slots * SIDEBAR_SECTION_GAP <= avail

    if _is_academic_cv(cv):
        spread = _compact_sidebar_stack(page1_sections)
    elif fits_compact:
        spread = _compact_sidebar_stack(page1_sections)
    else:
        spread = _spread_sections_vertically(
            page1_sections,
            inner_w,
            available_height=avail,
            max_gap=SIDEBAR_SPREAD_MAX_GAP,
        )
    return prefix + spread, tail_sections


def _sidebar_from_cv(cv: CvContent, st: dict[str, ParagraphStyle]) -> list:
    """Backward-compatible alias (page 1 sidebar only)."""
    flowables, _ = _sidebar_page1_from_cv(cv, st)
    return flowables


def _main_column_story_from_cv(cv: CvContent, st: dict[str, ParagraphStyle]) -> list:
    """Single main-column flow; ReportLab paginates when content exceeds frame height."""
    if _is_academic_cv(cv):
        return _academic_main_column_story_from_cv(cv, st)
    return _industry_main_column_story_from_cv(cv, st)


def _academic_main_column_story_from_cv(cv: CvContent, st: dict[str, ParagraphStyle]) -> list:
    flowables: list = [
        Spacer(1, MAIN_HEADER_GAP),
        Paragraph(cv.full_name, st["name"]),
        Spacer(1, ACADEMIC_NAME_TO_FIRST_SECTION_GAP),
    ]

    if cv.summary_bullets:
        from cv_generation.cv_style import normalize_summary_bullets

        summary_bullets, summary_warnings = normalize_summary_bullets(cv.summary_bullets)
        for warning in summary_warnings:
            print(f"Warning: CV summary — {warning}", flush=True)
        flowables.append(Paragraph(_pdf_label(cv, "SUMMARY", main=True), st["section"]))
        for bullet in summary_bullets:
            flowables.append(_ats_list_paragraph(bullet, st["bullet"]))
        flowables.append(Spacer(1, PROFILE_BEFORE_EXP_GAP))

    if cv.teaching:
        flowables.append(Paragraph(_pdf_label(cv, "TEACHING AND SUPERVISION", main=True), st["section"]))
        for item in cv.teaching:
            flowables.append(_ats_list_paragraph(item, st["bullet"]))
        flowables.append(Spacer(1, PROFILE_BEFORE_EXP_GAP))

    if cv.experience:
        flowables.append(Paragraph(_pdf_label(cv, "RESEARCH EXPERIENCE", main=True), st["section"]))
        flowables.extend(_experience_flowables(cv.experience, st, MAIN_COL_W))

    if cv.education:
        flowables.append(Spacer(1, 10))
        flowables.append(Paragraph(_pdf_label(cv, "EDUCATION", main=True), st["section"]))
        flowables.extend(_education_flowables(cv.education, st, MAIN_COL_W))
        flowables.append(Spacer(1, 4))

    pubs = cv.research_publications or cv.publications
    if pubs:
        label = "RESEARCH AND PUBLICATIONS" if cv.research_publications else "SELECTED PUBLICATIONS"
        flowables.append(Spacer(1, 6))
        flowables.append(Paragraph(_pdf_label(cv, label, main=True), st["section"]))
        for line in pubs:
            flowables.append(_ats_list_paragraph(line, st["publication"]))
        flowables.append(Spacer(1, 2))

    return flowables


def _industry_main_column_story_from_cv(cv: CvContent, st: dict[str, ParagraphStyle]) -> list:
    """Industry / corporate main column."""
    flowables: list = [
        Spacer(1, MAIN_HEADER_GAP),
        Paragraph(cv.full_name, st["name"]),
    ]
    if cv.role_title.strip():
        flowables.append(Paragraph(cv.role_title, st["subtitle"]))
    if cv.profile or cv.profile_paragraphs:
        flowables.append(Spacer(1, 6))
        flowables.append(Paragraph(_pdf_label(cv, "PROFILE", main=True), st["section"]))
        flowables.extend(_profile_flowables(cv, st))
        flowables.append(Spacer(1, PROFILE_BEFORE_EXP_GAP))

    if cv.experience:
        flowables.append(Paragraph(_pdf_label(cv, "WORK EXPERIENCE", main=True), st["section"]))
        flowables.extend(_experience_flowables(cv.experience, st, MAIN_COL_W))

    if cv.education:
        flowables.append(Spacer(1, 10))
        flowables.append(Paragraph(_pdf_label(cv, "EDUCATION", main=True), st["section"]))
        flowables.extend(_education_flowables(cv.education, st, MAIN_COL_W))
        flowables.append(Spacer(1, 4))

    if cv.publications:
        flowables.append(Spacer(1, 6))
        flowables.append(Paragraph(_pdf_label(cv, "SELECTED PUBLICATIONS", main=True), st["section"]))
        for line in cv.publications:
            flowables.append(_ats_list_paragraph(line, st["publication"]))
        flowables.append(Spacer(1, 2))

    return flowables


def _wireframe_sidebar(st: dict[str, ParagraphStyle]) -> list:
    return [
        *_sidebar_photo_block(),
        _icon_row("birth", DATE_OF_BIRTH_DEFAULT, st),
        Spacer(1, 12),
        Paragraph("CONTACT", st["sidebar_title"]),
        _icon_row("phone", _contact_paragraph_markup("phone", "+00-000-000-0000"), st),
        _icon_row("email", _contact_paragraph_markup("email", "email@example.com"), st),
        _icon_row("location", _contact_paragraph_markup("location", "City, Country"), st),
        _icon_row(
            "linkedin",
            _contact_paragraph_markup("linkedin", "https://linkedin.com/in/example"),
            st,
        ),
        _icon_row(
            "github",
            _contact_paragraph_markup("github", "https://github.com/example"),
            st,
        ),
        Spacer(1, SIDEBAR_SECTION_GAP),
        Paragraph("SKILLS", st["sidebar_title"]),
        _ats_list_paragraph("Python", st["sidebar_bullet"]),
        _ats_list_paragraph("MLOps", st["sidebar_bullet"]),
    ]


def _wireframe_main_page1(st: dict[str, ParagraphStyle]) -> list:
    return [
        Spacer(1, MAIN_HEADER_GAP),
        Paragraph("FULL NAME", st["name"]),
        Paragraph("ROLE TITLE", st["subtitle"]),
        Spacer(1, 6),
        Paragraph("PROFILE", st["section"]),
        Paragraph("[ profile placeholder ]", st["wire"]),
        Spacer(1, 6),
        Paragraph("WORK EXPERIENCE", st["section"]),
        Table(
            [
                [
                    [Paragraph("Organization Name", st["company"]), Paragraph("Role title", st["role"])],
                    Paragraph("Jan 2020 - Dec 2022", st["date"]),
                ]
            ],
            colWidths=[MAIN_COL_W * 0.70, MAIN_COL_W * 0.30],
        ),
        Paragraph("[ bullet ]", st["wire"]),
    ]


def _draw_full_height_sidebar(canvas, _doc) -> None:
    canvas.saveState()
    canvas.setFillColor(SIDEBAR_BG)
    canvas.rect(0, 0, SIDEBAR_W, PAGE_H, fill=1, stroke=0)
    canvas.restoreState()


def _on_cv_page(canvas, doc) -> None:
    _draw_full_height_sidebar(canvas, doc)
    # Languages/hobbies live on the first continuation page only (page 2). Redrawing on
    # page 3+ duplicated sidebar text when main content spanned three or more pages.
    if doc.page != 2:
        return
    sections = getattr(doc, "sidebar_p2_canvas_sections", None) or []
    if not sections:
        return
    _draw_centered_sidebar_sections_on_canvas(
        canvas,
        sections,
        SIDEBAR_PAD_X,
        _sidebar_inner_w(),
        PAGE_H - SIDEBAR_PAD_TOP,
        SIDEBAR_PAD_TOP,
    )


def _build_dual_column_layout(
    doc: BaseDocTemplate,
    sidebar_flowables: list,
    main_column_flowables: list,
    *,
    cv: CvContent | None = None,
    styles: dict[str, ParagraphStyle] | None = None,
    sidebar_p2_canvas_sections: list[list] | None = None,
) -> None:
    pad_side = SIDEBAR_PAD_X
    pad_main_x = PAD_MAIN_X

    sidebar_frame = Frame(
        pad_side,
        SIDEBAR_PAD_TOP,
        _sidebar_inner_w(),
        PAGE_H - 2 * SIDEBAR_PAD_TOP,
        id="sidebar",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    main_frame = Frame(
        SIDEBAR_W + pad_main_x,
        MAIN_PAD_TOP,
        MAIN_COL_W,
        PAGE_H - 2 * MAIN_PAD_TOP,
        id="main",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    # Page 2+ must not reuse the sidebar frame — overflow was flowing into the narrow
    # left column. Continuation pages use only the main column at the same geometry.
    main_continuation_frame = Frame(
        SIDEBAR_W + pad_main_x,
        MAIN_PAD_TOP,
        MAIN_COL_W,
        PAGE_H - 2 * MAIN_PAD_TOP,
        id="main_continuation",
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates(
        [
            PageTemplate(
                id="dual_column",
                frames=[sidebar_frame, main_frame],
                onPage=_on_cv_page,
            ),
            PageTemplate(
                id="main_continuation",
                frames=[main_continuation_frame],
                onPage=_on_cv_page,
            ),
        ]
    )

    if cv is not None:
        doc.cv_content = cv
    if styles is not None:
        doc.pdf_styles = styles
    doc.sidebar_p2_canvas_sections = sidebar_p2_canvas_sections or []

    story: list = []
    story.extend(sidebar_flowables)
    story.append(FrameBreak())
    story.append(NextPageTemplate("main_continuation"))
    story.extend(main_column_flowables)

    doc.build(story)


def render_styled_cv_pdf(
    markdown_path: Path,
    pdf_path: Path,
    *,
    profile_photo: str | Path | None = None,
    document_language: str | None = None,
) -> None:
    cv = parse_cv_markdown(markdown_path.read_text(encoding="utf-8"))
    if document_language:
        cv.document_language = document_language
    st = _styles(getSampleStyleSheet())

    if LAYOUT_ONLY:
        sidebar, p2_sections = _wireframe_sidebar(st), []
        main_column = _wireframe_main_page1(st)
        doc = BaseDocTemplate(
            str(pdf_path),
            pagesize=A4,
            leftMargin=0,
            rightMargin=0,
            topMargin=0,
            bottomMargin=0,
        )
        sidebar, p2_sections = _sidebar_page1_from_cv(cv, st, profile_photo=profile_photo)
        _build_dual_column_layout(
            doc, sidebar, main_column, cv=cv, styles=st, sidebar_p2_canvas_sections=p2_sections
        )
        return

    main_column = _main_column_story_from_cv(cv, st)
    sidebar, p2_sections = _sidebar_page1_from_cv(cv, st, profile_photo=profile_photo)
    doc = BaseDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=0,
        rightMargin=0,
        topMargin=0,
        bottomMargin=0,
    )
    _build_dual_column_layout(
        doc,
        sidebar,
        main_column,
        cv=cv,
        styles=st,
        sidebar_p2_canvas_sections=p2_sections,
    )
