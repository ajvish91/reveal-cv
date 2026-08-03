#!/usr/bin/env python3
"""
Render styled CV PDF from markdown (industry or academic track; see cv_tracks.py).

Profile photo (optional, keep outside the repo):
  --profile-photo PATH
  CV_PROFILE_PHOTO env var
  _profile_photo_path in CV_IDENTITY_MAPPING JSON
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

CV_PACKAGE_DIR = Path(__file__).resolve().parent


def _ensure_project_cwd() -> None:
    os.chdir(CV_PACKAGE_DIR)


def _import_renderer():
    _ensure_project_cwd()
    from cv_generation.cv_pdf_renderer import render_styled_cv_pdf
    from cv_generation.cv_private import resolve_profile_photo_path

    return render_styled_cv_pdf, resolve_profile_photo_path


def _looks_like_plain_document(markdown_path: Path, text: str) -> bool:
    from cv_generation.cv_application_artifacts import is_plain_pdf_markdown

    return is_plain_pdf_markdown(markdown_path, text)


def _looks_like_cover_letter(markdown_path: Path, text: str) -> bool:
    name = markdown_path.name.lower()
    if "cover_letter" in name or "cover-letter" in name:
        return True
    lowered = text.lower()
    return "dear " in lowered and "sincerely" in lowered


def _to_name_case_if_upper(line: str) -> str:
    from cv_generation.plain_markdown_pdf import _to_name_case_if_upper as _name_case

    return _name_case(line)


def _render_plain_markdown_pdf(
    markdown_path: Path,
    pdf_path: Path,
    *,
    normalize_upper_names: bool = False,
) -> None:
    from cv_generation.plain_markdown_pdf import render_plain_markdown_pdf

    render_plain_markdown_pdf(
        markdown_path,
        pdf_path,
        normalize_upper_names=normalize_upper_names,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Render CV markdown to styled PDF")
    p.add_argument("markdown", type=Path, help="Path to CV markdown (e.g. final_cv.md)")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output PDF path (default: same name as markdown with .pdf)",
    )
    p.add_argument(
        "--profile-photo",
        type=Path,
        default=None,
        help="Headshot image (jpg/png); also reads CV_PROFILE_PHOTO / mapping JSON",
    )
    p.add_argument(
        "--plain",
        action="store_true",
        help="Render as plain one-column PDF (recommended for cover letters)",
    )
    return p.parse_args()


def main() -> int:
    original_cwd = Path.cwd()
    args = parse_args()
    md = (original_cwd / args.markdown).expanduser().resolve()
    if not md.is_file():
        print(f"Markdown not found: {md}", file=sys.stderr)
        return 1

    output_arg = args.output or md.with_suffix(".pdf")
    pdf = (original_cwd / output_arg).expanduser().resolve()
    explicit = (
        (original_cwd / args.profile_photo).expanduser().resolve()
        if args.profile_photo
        else None
    )
    if explicit and not explicit.is_file():
        print(f"Profile photo not found: {explicit}", file=sys.stderr)
        return 2

    pdf.parent.mkdir(parents=True, exist_ok=True)
    text = md.read_text(encoding="utf-8")
    use_plain = args.plain or _looks_like_plain_document(md, text)

    if use_plain:
        _render_plain_markdown_pdf(
            md,
            pdf,
            normalize_upper_names=_looks_like_cover_letter(md, text),
        )
    else:
        render_styled_cv_pdf, resolve_profile_photo_path = _import_renderer()
        render_styled_cv_pdf(md, pdf, profile_photo=explicit)

    if not pdf.is_file() or pdf.stat().st_size < 500:
        print(f"PDF was not created successfully: {pdf}", file=sys.stderr)
        return 3

    if use_plain:
        print("Layout: plain one-column")
    else:
        _, resolve_profile_photo_path = _import_renderer()
        used = resolve_profile_photo_path(explicit)
        if used:
            print(f"Profile photo: {used}")
        else:
            print("Profile photo: placeholder (set CV_PROFILE_PHOTO or _profile_photo_path)")
    print(f"Wrote: {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
