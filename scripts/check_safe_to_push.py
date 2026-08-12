#!/usr/bin/env python3
"""
Scan tracked-ish paths for patterns that should not be pushed to a public git remote.

Usage (from repo root):
  python scripts/check_safe_to_push.py
  python scripts/check_safe_to_push.py --paths shared cv_generation job_search
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from repo_paths import REPO_ROOT

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

SKIP_REL_PREFIXES = (
    "job_search/data/",
    "job_search/teknorge/",
    "cv_generation/jobs/",
    "docs/",
)


def _rel_posix(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def _is_skip_prefix_dir(rel_s: str) -> bool:
    """True if this relative directory is covered by SKIP_REL_PREFIXES."""
    rel_norm = rel_s.rstrip("/")
    for prefix in SKIP_REL_PREFIXES:
        p = prefix.rstrip("/")
        if rel_norm == p or rel_norm.startswith(p + "/"):
            return True
    return False


def should_scan(path: Path) -> bool:
    if path.is_dir():
        return False
    if path.suffix in (".pdf", ".pyc", ".db", ".sqlite", ".sqlite3", ".log"):
        return False

    rel_s = _rel_posix(path)
    if rel_s in SKIP_REL_FILES:
        return False
    if any(substr in rel_s for substr in ALLOW_PATH_SUBSTR):
        return False
    if any(rel_s.startswith(prefix) for prefix in SKIP_REL_PREFIXES):
        return False

    parts = path.relative_to(REPO_ROOT).parts
    if any(p in SKIP_DIRS for p in parts):
        return False
    if "cv_runs" in parts:
        return False
    return True


def iter_files(root: Path) -> Iterator[Path]:
    """Yield files under root without descending into SKIP_DIRS or skip-prefix dirs."""
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current = Path(dirpath)
        # Prune directories we should never enter
        keep: list[str] = []
        for name in dirnames:
            if name in SKIP_DIRS:
                continue
            child_rel = _rel_posix(current / name)
            if _is_skip_prefix_dir(child_rel):
                continue
            keep.append(name)
        dirnames[:] = keep
        for name in filenames:
            yield current / name


def scan_file(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    hits: list[str] = []
    rel = _rel_posix(path)
    lines = text.splitlines()
    for label, pat in SENSITIVE_PATTERNS:
        if label in ("real_email_not_example", "czech_phone"):
            for line in lines:
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
        if not root.exists():
            continue
        for path in iter_files(root):
            if should_scan(path):
                all_hits.extend(scan_file(path))

    unique_hits = sorted(set(all_hits))
    if unique_hits:
        print("Possible sensitive content (review before push):\n", file=sys.stderr)
        for h in unique_hits[:50]:
            print(f"  ! {h}", file=sys.stderr)
        if len(unique_hits) > 50:
            print(f"  ... and {len(unique_hits) - 50} more", file=sys.stderr)
        print("\nEnsure .gitignore excludes cv_runs/, private/, *.pdf, mapping JSON.", file=sys.stderr)
        return 1

    print("No obvious sensitive patterns in scanned paths.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
