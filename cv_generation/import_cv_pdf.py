#!/usr/bin/env python3
"""
Extract plain text from a CV PDF into cv/_extracted/ for merging into academic.md / industry.md.

  python import_cv_pdf.py academic ~/Downloads/cv_academic.pdf
  python import_cv_pdf.py industry  ~/Downloads/cv_industry.pdf

Does not overwrite your .md sources automatically — copy relevant sections by hand or paste the .txt into the body.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from pypdf import PdfReader

from shared.cv_loader import resolve_cv_dir


def sanitize_filename(stem: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9._-]+", "_", stem).strip("_")
    return stem or "cv"


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        parts.append(t)
    return "\n\n".join(parts).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract CV PDF text into cv/_extracted/")
    parser.add_argument(
        "label",
        choices=("academic", "industry"),
        help="Which variant this PDF belongs to",
    )
    parser.add_argument("pdf", type=Path, help="Path to PDF file")
    args = parser.parse_args()
    pdf: Path = args.pdf.expanduser().resolve()
    if not pdf.is_file():
        print(f"Not a file: {pdf}", file=sys.stderr)
        return 1

    extract_dir = resolve_cv_dir() / "_extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    out = extract_dir / f"{args.label}_{sanitize_filename(pdf.stem)}.txt"
    text = extract_pdf_text(pdf)
    if not text:
        print("Warning: no text extracted (scanned PDFs need OCR).", file=sys.stderr)
    out.write_text(text + "\n", encoding="utf-8")
    print(out)
    print(
        f"Merge into shared/cv/{args.label}.md under the markdown body (after the closing ---), "
        f"or copy phrases into front matter keywords/skills.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
