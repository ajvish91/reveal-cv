#!/usr/bin/env python3
"""
Replace anonymized CV placeholders with real personal info.

Intended use:
- Keep real data in a private JSON file outside this repo.
- Run this script after CVs are generated.

Example (from repository root; mapping file lives outside this repo):
  .venv/bin/python -m cv_generation.deanonymize_cvs \
    --mapping ~/private/cv/cv_identity_mapping.json \
    --input-dir cv_runs \
    --glob "final_cv.md" \
    --recursive \
    --output-dir ~/private/cv/deanonymized \
    --strict

Or set CV_IDENTITY_MAPPING and omit --mapping.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from cv_generation.cv_application_artifacts import normalize_upper_name_variants
from cv_generation.cv_private import social_url_replacements_from_raw

DEFAULT_MAPPING_ENV = "CV_IDENTITY_MAPPING"

# Substrings that indicate an unfilled example/template value (not real data).
PLACEHOLDER_VALUE_MARKERS: tuple[str, ...] = (
    "REPLACE_WITH_",
    "Your Full Name",
    "Your publication",
    "Your hobby",
    "Your Ph.D.",
    "Your master's",
    "Your bachelor's",
    "Postdoc institution",
    "Ph.D. institution",
    "B.Eng. institution",
    "Backend developer employer",
    "E-commerce / integration employer",
    "NLP research employer",
    "Research assistant institution",
    "M.Sc. institution",
    "Mon YYYY",
    "YYYY - YYYY",
    "DD Mon YYYY",
    "City, Country",
    "you@example.com",
    "+XX-XXX",
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Apply private identity mapping to CV files")
    p.add_argument(
        "--mapping",
        type=Path,
        default=None,
        help=f"Path to private JSON mapping (default: ${DEFAULT_MAPPING_ENV} env var)",
    )
    p.add_argument("--input-dir", required=True, type=Path, help="Directory containing generated CVs")
    p.add_argument("--glob", default="*.md", help="Filename pattern to process (default: *.md)")
    p.add_argument("--recursive", action="store_true", help="Search recursively in input directory")
    p.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Write transformed files here. If omitted, files are edited in place.",
    )
    p.add_argument("--dry-run", action="store_true", help="Show planned replacements without writing files")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error if no replacements were made or anonymized keys remain in output",
    )
    return p.parse_args()


def is_placeholder_value(key: str, value: str) -> bool:
    """True when the mapping value is still an unfilled template, not real PII."""
    if not value:
        return True
    if value.startswith("REPLACE_WITH_"):
        return True
    if value.strip() == key.strip():
        return True
    if any(marker in value for marker in PLACEHOLDER_VALUE_MARKERS):
        return True
    if re.match(r"^[-+]?\s*Your\s", value):
        return True
    return False


def load_mapping(path: Path) -> tuple[dict[str, str], list[str]]:
    if not path.is_file():
        raise SystemExit(f"Mapping file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as err:
        raise SystemExit(
            f"Invalid JSON in {path} at line {err.lineno}, column {err.colno}: {err.msg}\n"
            "Common cause: a line break inside a quoted value. Keep each entry on one line, "
            "or use \\n inside the string for intentional breaks."
        ) from err
    if not isinstance(raw, dict):
        raise SystemExit("Mapping JSON must be an object of {'from': 'to'} pairs.")

    out: dict[str, str] = {}
    skipped: list[str] = []
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        if not isinstance(k, str) or not isinstance(v, str):
            raise SystemExit("All mapping keys/values must be strings.")
        key = k.strip()
        if not key:
            raise SystemExit("Mapping keys cannot be empty.")
        value = v.strip()
        if is_placeholder_value(key, value):
            skipped.append(key)
            continue
        out[key] = value
    for key, value in social_url_replacements_from_raw(raw).items():
        out.setdefault(key, value)
    out = normalize_upper_name_variants(out)
    return out, skipped


def list_files(input_dir: Path, pattern: str, recursive: bool) -> list[Path]:
    if not input_dir.is_dir():
        raise SystemExit(f"Input directory not found: {input_dir}")
    if recursive:
        return sorted(p for p in input_dir.rglob(pattern) if p.is_file())
    return sorted(p for p in input_dir.glob(pattern) if p.is_file())


_CV_DATE_KEY_RE = re.compile(
    r"(?:\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\b|\b\d{4}\b|Present|nå)",
    re.IGNORECASE,
)


def looks_like_cv_date_key(key: str) -> bool:
    return bool(_CV_DATE_KEY_RE.search(key))


def _abbreviate_norwegian_months(text: str) -> str:
    """CV experience lines often use mar./jul./jun. instead of mars/juli/juni."""
    out = text
    # Keep "15. mars 1992" — only abbreviate standalone month words in ranges.
    if re.search(r"\d+\.\s+mars\s+\d{4}", out, flags=re.IGNORECASE):
        return out
    out = re.sub(r"\bmars\b", "mar.", out, flags=re.IGNORECASE)
    out = re.sub(r"\bjuni\b", "jun.", out, flags=re.IGNORECASE)
    out = re.sub(r"\bjuli\b", "jul.", out, flags=re.IGNORECASE)
    return out


def norwegian_date_variants(text: str) -> set[str]:
    """Plausible Norwegian date strings produced from an English mapping key/value."""
    from cv_generation.cv_norwegian import localize_dates_no

    variants: set[str] = set()
    base = text.strip()
    if not base:
        return variants
    variants.add(base)
    if " - " in base:
        variants.add(base.replace(" - ", " – "))
    localized = localize_dates_no(base)
    variants.add(localized)
    variants.add(_abbreviate_norwegian_months(localized))
    if " - " in base:
        hyphen_localized = localize_dates_no(base.replace(" - ", " – "))
        variants.add(hyphen_localized)
        variants.add(_abbreviate_norwegian_months(hyphen_localized))
    return {v for v in variants if v}


def _preferred_norwegian_date_value(dst: str) -> str:
    """Pick the abbreviated Norwegian form used in localized CV markdown."""
    if not looks_like_cv_date_key(dst):
        return dst
    candidates = norwegian_date_variants(dst)
    abbreviated = [c for c in candidates if re.search(r"\b[a-z]{3}\.\s+\d{4}", c, flags=re.IGNORECASE)]
    if abbreviated:
        return max(abbreviated, key=len)
    return max(candidates, key=len)


def expand_mapping_norwegian_dates(mapping: dict[str, str]) -> dict[str, str]:
    """
    Add Norwegian date aliases so English mapping keys work on final_cv_no.md.

    Norwegian CVs use en-dashes (–), Norwegian month names, and abbreviations (mar., sep.),
    so keys like ``Mar 2026 - Present`` never match ``mar. 2026 – nå``.
    """
    expanded = dict(mapping)
    for src, dst in mapping.items():
        if not looks_like_cv_date_key(src):
            continue
        dst_out = _preferred_norwegian_date_value(dst)
        for src_no in norwegian_date_variants(src):
            if src_no not in expanded:
                expanded[src_no] = dst_out
    return expanded


def apply_replacements(text: str, mapping: dict[str, str]) -> tuple[str, dict[str, int]]:
    # Longer keys first avoids partial replacement conflicts.
    ordered = sorted(mapping.items(), key=lambda kv: len(kv[0]), reverse=True)
    counts: dict[str, int] = {}
    out = text
    for src, dst in ordered:
        n = out.count(src)
        if n:
            out = out.replace(src, dst)
            counts[src] = n
    return out, counts


def remaining_placeholder_keys(text: str, mapping: dict[str, str]) -> list[str]:
    return [key for key in mapping if key in text]


def remaining_skipped_in_text(text: str, skipped_keys: list[str]) -> list[str]:
    """Template keys still present because their mapping values were not filled in."""
    return [key for key in skipped_keys if key in text]


# Shown prominently when these anonymized tokens survive deanonymization.
IDENTITY_HINT_KEYS: tuple[str, ...] = ("ALEX RIVERA", "MITCH EVANS", "AI SPECIALIST")


def partial_document_glob_hint(glob_pattern: str) -> str | None:
    """Extra stderr context when the glob targets a non-CV artifact."""
    g = glob_pattern.lower()
    if g.endswith("_no.md"):
        return (
            "Norwegian/localized markdown uses different section labels and dates. "
            "English date keys are auto-expanded to Norwegian forms (mar., –, nå). "
            "You only need English date keys in your mapping JSON."
        )
    if "cover" in g and "final_cv" not in g:
        return (
            "Many keys are CV-only (education, publications, hobbies, date ranges). "
            "That is expected when deanonymizing cover_letter.md alone; private_cv apply "
            "runs the CV first, then supplementary artifacts."
        )
    if "research_proposal" in g or "application_letter" in g:
        return (
            "Supplementary academic artifacts usually contain only the applicant name and "
            "contact placeholders. Use MITCH EVANS (all caps) in source markdown so mapping "
            "keys match; title-case aliases are added automatically."
        )
    return None


def target_path(src: Path, base_dir: Path, output_dir: Path | None) -> Path:
    if output_dir is None:
        return src
    rel = src.relative_to(base_dir)
    return output_dir / rel


def resolve_mapping_path(arg: Path | None) -> Path:
    if arg is not None:
        return arg.expanduser().resolve()
    env = os.environ.get(DEFAULT_MAPPING_ENV, "").strip()
    if not env:
        raise SystemExit(
            f"Missing --mapping and {DEFAULT_MAPPING_ENV} is not set.\n"
            "Keep your real values in a JSON file outside this repo, e.g.\n"
            "  ~/private/cv/cv_identity_mapping.json"
        )
    return Path(env).expanduser().resolve()


def main() -> int:
    args = parse_args()
    mapping_path = resolve_mapping_path(args.mapping)
    mapping, skipped_keys = load_mapping(mapping_path)
    if skipped_keys:
        print(
            f"Skipped {len(skipped_keys)} mapping entries with unfilled template values in {mapping_path}:",
            file=sys.stderr,
        )
        for key in skipped_keys:
            marker = " ← name/role" if key in IDENTITY_HINT_KEYS else ""
            print(f"  ! {key}{marker}", file=sys.stderr)
    if not mapping:
        raise SystemExit(
            f"No active replacements in {mapping_path} "
            "(empty file or only placeholder/template values)."
        )
    if args.glob.lower().endswith("_no.md"):
        mapping = expand_mapping_norwegian_dates(mapping)
    input_dir = args.input_dir.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve() if args.output_dir else None
    files = list_files(input_dir, args.glob, args.recursive)

    if not files:
        print("No files matched.")
        if args.strict:
            return 2
        return 0

    changed_files = 0
    total_replacements = 0
    matched_keys: set[str] = set()
    leftover_by_file: dict[Path, list[str]] = {}

    for src in files:
        original = src.read_text(encoding="utf-8")
        updated, counts = apply_replacements(original, mapping)
        matched_keys.update(counts)
        remaining = remaining_placeholder_keys(updated, mapping)
        unfilled_skipped = remaining_skipped_in_text(updated, skipped_keys)
        combined = sorted(set(remaining) | set(unfilled_skipped))
        if combined:
            leftover_by_file[src] = combined

        if not counts:
            print(f"{src} (no replacements)")

        if not counts and output_dir is None:
            continue

        changed_files += 1
        total_replacements += sum(counts.values())
        dst = target_path(src, input_dir, output_dir)

        print(f"{src} -> {dst}")
        for key, n in counts.items():
            print(f"  replaced {n:>3}x: {key}")

        if args.dry_run:
            continue

        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(updated, encoding="utf-8")

    unmatched_keys = sorted(set(mapping) - matched_keys)

    print(f"Mapping:           {mapping_path}")
    print(f"Processed files:   {len(files)}")
    print(f"Changed files:     {changed_files}")
    print(f"Replacements:      {total_replacements}")
    if args.dry_run:
        print("Dry run only. No files were written.")

    if unmatched_keys:
        partial_hint = partial_document_glob_hint(args.glob)
        print(
            f"\nMapping keys not found in any processed file ({len(unmatched_keys)})",
            file=sys.stderr,
        )
        if partial_hint:
            print(f"  {partial_hint}", file=sys.stderr)
        else:
            print(
                "  Remove stale keys from your private JSON or add matching text to the CV.",
                file=sys.stderr,
            )
        for key in unmatched_keys[:20]:
            print(f"  - {key}", file=sys.stderr)
        if len(unmatched_keys) > 20:
            print(f"  ... and {len(unmatched_keys) - 20} more", file=sys.stderr)

    if leftover_by_file:
        print("\nAnonymized text still present after replacement:", file=sys.stderr)
        for src, keys in leftover_by_file.items():
            print(f"  {src}:", file=sys.stderr)
            for key in keys[:10]:
                hint = " — set a real value in your mapping JSON (not REPLACE_WITH_* / Your …)" if key in skipped_keys else ""
                print(f"    - {key}{hint}", file=sys.stderr)
            if len(keys) > 10:
                print(f"    ... and {len(keys) - 10} more", file=sys.stderr)

    if args.strict:
        if changed_files == 0:
            print("\n--strict: no replacements were applied.", file=sys.stderr)
            return 3
        if unmatched_keys or leftover_by_file:
            print("\n--strict: deanonymization incomplete.", file=sys.stderr)
            return 4

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
