"""Optional user tailoring instructions for a CV run folder."""
from __future__ import annotations

from pathlib import Path

APPLY_PROMPTS_FILENAME = "apply_prompts.txt"

APPLY_LANGUAGE_CODES = ("en", "no")
APPLY_LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "no": "Norwegian (Bokmål)",
}


def normalize_apply_language(code: str | None) -> str:
    value = (code or "en").strip().lower()
    return value if value in APPLY_LANGUAGE_CODES else "en"


def resolve_apply_language(sidebar_default: str | None, popover_choice: str | None) -> str:
    """Per-job popover may override sidebar; ``inherit`` keeps the sidebar default."""
    choice = (popover_choice or "inherit").strip().lower()
    if choice in APPLY_LANGUAGE_CODES:
        return choice
    return normalize_apply_language(sidebar_default)


def normalize_apply_prompts(text: str | None) -> str:
    return (text or "").strip()


def merge_apply_prompts(*parts: str | None) -> str:
    chunks = [normalize_apply_prompts(part) for part in parts]
    return "\n\n".join(chunk for chunk in chunks if chunk)


def apply_prompts_path(run_dir: Path) -> Path:
    return run_dir / APPLY_PROMPTS_FILENAME


def read_apply_prompts(run_dir: Path) -> str:
    path = apply_prompts_path(run_dir)
    if not path.is_file():
        return ""
    return normalize_apply_prompts(path.read_text(encoding="utf-8"))


def write_apply_prompts(run_dir: Path, text: str) -> Path | None:
    normalized = normalize_apply_prompts(text)
    if not normalized:
        return None
    path = apply_prompts_path(run_dir)
    path.write_text(normalized + "\n", encoding="utf-8")
    return path


def apply_prompts_markdown_section(text: str) -> str:
    body = normalize_apply_prompts(text)
    if not body:
        return ""
    return (
        "\n## User tailoring instructions\n\n"
        "The applicant provided these notes for this application. "
        "Follow them when tailoring CV bullets and supplementary documents "
        "(within honesty rules in `cv_style.py`).\n\n"
        f"{body}\n"
    )


def apply_language_markdown_section(language: str) -> str:
    code = normalize_apply_language(language)
    label = APPLY_LANGUAGE_LABELS[code]
    lines = [
        "\n## Application language\n",
        f"Output language: **{label}** (`{code}`).",
    ]
    if code == "no":
        lines.append(
            "After English assembly, generate `final_cv_no.md` / `final_cv_no.pdf` "
            "and Norwegian cover-letter artifacts when applicable."
        )
    lines.append("")
    return "\n".join(lines)
