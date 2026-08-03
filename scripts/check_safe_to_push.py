#!/usr/bin/env python3
"""
Scan tracked-ish paths for patterns that should not be pushed to a public git remote.

Usage (from repo root):
  python scripts/check_safe_to_push.py
  python scripts/check_safe_to_push.py --paths shared cv_generation job_search
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Paths always skipped
SKIP_DIRS = {
    ".venv",
    ".git",
    "__pycache__",
    "node_modules",
    "cv_runs",
    "deanonymized",
    "private",
    ".tmp_private_cv",
    "archive",
}

# Heuristics: likely real PII that should not ship in git
SENSITIVE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("czech_phone", re.compile(r"\+420[-\s]?\d")),
    ("real_email_not_example", re.compile(r"@[a-z0-9.-]+\.(com|no|cz|io)\b", re.I)),
    ("rough_cv_doc", re.compile(r"rough\s*CV\.docx", re.I)),
    ("real_name_fragment", re.compile(r"\bAJAY\b|\bVishwanath\b|uia\.no|/Users/ajayv\b", re.I)),
]

# Skip lines that are documentation / example placeholders
DOC_SKIP_IF_LINE_CONTAINS = (
    "example.com",
    "REPLACE_WITH_",
    "cv-placeholder",
    "DEMO CV",
    "master_cv@gmail.com",  # intentional anonymized contact token
    "MITCH EVANS",  # intentional anonymized name token
    "Prague, Czech Republic",  # intentional anonymized location token
    "demo.candidate",
    "+420-588-290-1458",  # intentional anonymized phone token
)

# Allowed in demo templates / docs that explain the anonymization scheme
ALLOW_PATH_SUBSTR = (
    "shared/cv/industry.demo.md",
    "shared/cv/academic.demo.md",
    "shared/cv/demo_only/",
    "cv_identity_mapping.example.json",
    "check_safe_to_push.py",
    "GIT_AND_PRIVACY.md",
    "CV_AUTOMATION.md",
    "PRIVACY.md",
    "AGENTS.md",
    "README.md",
)

# Personal CV copies (gitignored); never scan for push safety
SKIP_REL_FILES = {
    "shared/cv/industry.md",
    "shared/cv/academic.md",
}


def should_scan(path: Path) -> bool:
    rel = path.relative_to(REPO_ROOT)
    rel_s = str(rel).replace("\\", "/")
    if rel_s in SKIP_REL_FILES:
        return False
    if any(substr in rel_s for substr in ALLOW_PATH_SUBSTR):
        return False
    parts = rel.parts
    if any(p in SKIP_DIRS for p in parts):
        return False
    if parts[:2] == ("job_search", "data"):
        return False
    if parts[:2] == ("cv_generation", "jobs"):
        # Public job-ad text often contains recruiter emails; not applicant PII.
        return False
    if path.suffix in (".pdf", ".pyc", ".db", ".sqlite", ".sqlite3", ".log"):
        return False
    if path.is_dir():
        return False
    if "cv_runs" in parts:
        return False
    return True


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    hits: list[str] = []
    rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    if rel.startswith("job_search/teknorge"):
        return []
    if rel.startswith("docs/") or rel.endswith("check_safe_to_push.py"):
        return []

    for label, pat in SENSITIVE_PATTERNS:
        if label in ("real_email_not_example", "czech_phone"):
            for line in text.splitlines():
                if any(s in line for s in DOC_SKIP_IF_LINE_CONTAINS):
                    continue
                if pat.search(line):
                    hits.append(f"{rel}: {label if label != 'real_email_not_example' else 'suspicious email'}")
                    break
            continue
        if pat.search(text):
            hits.append(f"{rel}: {label}")
    return hits


def main() -> int:
    p = argparse.ArgumentParser(description="Check repo for likely sensitive content before git push")
    p.add_argument(
        "--paths",
        nargs="*",
        default=["shared", "cv_generation", "job_search", "scripts", "README.md", "AGENTS.md"],
        help="Top-level paths to scan (default: main code + shared)",
    )
    args = p.parse_args()

    all_hits: list[str] = []
    for top in args.paths:
        root = REPO_ROOT / top
        if root.is_file():
            if should_scan(root):
                all_hits.extend(scan_file(root))
            continue
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if should_scan(path):
                all_hits.extend(scan_file(path))

    if all_hits:
        print("Possible sensitive content (review before push):\n", file=sys.stderr)
        for h in sorted(set(all_hits))[:50]:
            print(f"  ! {h}", file=sys.stderr)
        if len(set(all_hits)) > 50:
            print(f"  ... and {len(set(all_hits)) - 50} more", file=sys.stderr)
        print("\nEnsure .gitignore excludes cv_runs/, private/, *.pdf, mapping JSON.", file=sys.stderr)
        return 1

    print("No obvious sensitive patterns in scanned paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
