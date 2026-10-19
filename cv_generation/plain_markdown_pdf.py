"""
Render supplementary application markdown (proposals, letters) to plain PDF.

Handles ATX headings, inline **bold** / *italic*, bullet and numbered lists,
and pipe tables. Cover letters and research proposals share this path.
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from cv_generation.cv_pdf_renderer import markdown_inline_to_reportlab

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")
_ORDERED_RE = re.compile(r"^(\d+)\.\s+(.+)$")
_BULLET_RE = re.compile(r"^[-*]\s+(.+)$")


def _to_name_case_if_upper(line: str) -> str:
    stripped = line.strip()
    if not stripped:
        return line
    has_letters = any(ch.isalpha() for ch in stripped)
    if has_letters and stripped == stripped.upper():
        return " ".join(part.capitalize() for part in stripped.split())
    return line


def _parse_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _is_table_separator_row(cells: list[str]) -> bool:
    if not cells:
        return True
    return all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells if cell)


def _paragraph_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    body = ParagraphStyle(
        "plain_doc_body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        spaceAfter=4,
    )
    return {
        "body": body,
        "h1": ParagraphStyle(
            "plain_doc_h1",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            spaceBefore=4,
            spaceAfter=10,
        ),
        "h2": ParagraphStyle(
            "plain_doc_h2",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "h3": ParagraphStyle(
            "plain_doc_h3",
            parent=body,
            fontName="Helvetica-Bold",
            fontSize=11.5,
            leading=15,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "list": ParagraphStyle(
            "plain_doc_list",
            parent=body,
            leftIndent=14,
            bulletIndent=0,
            spaceAfter=3,
        ),
    }


def _add_paragraph(story: list, text: str, style: ParagraphStyle, *, bullet: str | None = None) -> None:
    markup = markdown_inline_to_reportlab(text)
    if bullet:
        story.append(Paragraph(markup, style, bulletText=bullet))
    else:
        story.append(Paragraph(markup, style))


def _add_table(story: list, rows: list[list[str]], body_style: ParagraphStyle) -> None:
    if not rows:
        return
    col_count = max(len(row) for row in rows)
    normalized = [row + [""] * (col_count - len(row)) for row in rows]
    table_data = [
        [Paragraph(markdown_inline_to_reportlab(cell), body_style) for cell in row]
        for row in normalized
    ]
    col_width = (A4[0] - 40 * mm) / max(col_count, 1)
    table = Table(table_data, colWidths=[col_width] * col_count, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(Spacer(1, 6))
    story.append(table)
    story.append(Spacer(1, 8))


def build_plain_markdown_story(
    lines: list[str],
    *,
    normalize_upper_names: bool = False,
) -> list:
    para_styles = _paragraph_styles()
    story: list = []
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        stripped = line.strip()

        if normalize_upper_names:
            stripped = _to_name_case_if_upper(stripped)

        if not stripped:
            story.append(Spacer(1, 8))
            idx += 1
            continue

        table_row = _parse_table_row(stripped)
        if table_row is not None:
            table_rows: list[list[str]] = []
            while idx < len(lines):
                row = _parse_table_row(lines[idx].strip())
                if row is None:
                    break
                if not _is_table_separator_row(row):
                    table_rows.append(row)
                idx += 1
            _add_table(story, table_rows, para_styles["body"])
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            style_key = "h1" if level == 1 else "h2" if level == 2 else "h3"
            _add_paragraph(story, heading.group(2).strip(), para_styles[style_key])
            idx += 1
            continue

        ordered = _ORDERED_RE.match(stripped)
        if ordered:
            _add_paragraph(
                story,
                ordered.group(2).strip(),
                para_styles["list"],
                bullet=f"{ordered.group(1)}.",
            )
            idx += 1
            continue

        bullet = _BULLET_RE.match(stripped)
        if bullet:
            _add_paragraph(story, bullet.group(1).strip(), para_styles["list"], bullet="•")
            idx += 1
            continue

        if stripped == "---":
            story.append(Spacer(1, 6))
            idx += 1
            continue

        _add_paragraph(story, stripped, para_styles["body"])
        idx += 1

    return story


def render_plain_markdown_pdf(
    markdown_path: Path,
    pdf_path: Path,
    *,
    normalize_upper_names: bool = False,
) -> None:
    raw_text = markdown_path.read_text(encoding="utf-8")
    lines = [line.rstrip() for line in raw_text.splitlines()]
    story = build_plain_markdown_story(lines, normalize_upper_names=normalize_upper_names)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=markdown_path.stem.replace("_", " ").title(),
    )
    doc.build(story)
