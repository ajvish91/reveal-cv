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
    from cv_generation.cv_application_artifacts import is_plain_pdf_markdown, looks_like_cover_letter
    from cv_generation.plain_markdown_pdf import render_plain_markdown_pdf

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
    use_plain = args.plain or is_plain_pdf_markdown(md, text)

    render_styled_cv_pdf = None
    resolve_profile_photo_path = None
    if not use_plain:
        render_styled_cv_pdf, resolve_profile_photo_path = _import_renderer()

    if use_plain:
        render_plain_markdown_pdf(
            md,
            pdf,
            normalize_upper_names=looks_like_cover_letter(md, text),
        )
    else:
        assert render_styled_cv_pdf is not None
        render_styled_cv_pdf(md, pdf, profile_photo=explicit)

    if not pdf.is_file() or pdf.stat().st_size < 500:
        print(f"PDF was not created successfully: {pdf}", file=sys.stderr)
        return 3

    if use_plain:
        print("Layout: plain one-column")
    else:
        assert resolve_profile_photo_path is not None
        used = resolve_profile_photo_path(explicit)
        if used:
            print(f"Profile photo: {used}")
        else:
            print("Profile photo: placeholder (set CV_PROFILE_PHOTO or _profile_photo_path)")
    print(f"Wrote: {pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
