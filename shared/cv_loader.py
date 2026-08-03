#!/usr/bin/env python3
"""
Load CV markdown files with optional YAML front matter into JobProfile objects.
Used by later phases (job fetch, scoring, cover letters).

Real CVs (gitignored): shared/cv/industry.md + academic.md, or ~/private/cv/cv/, or CV_SOURCE_DIR.
Repo ships industry.demo.md / academic.demo.md only.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_PACKAGE_CV_DIR = Path(__file__).resolve().parent / "cv"
_DEFAULT_PRIVATE_CV_DIR = Path.home() / "private" / "cv" / "cv"
_PROFILE_STEMS = ("industry", "academic")


def _profile_path(cv_dir: Path, stem: str) -> Path | None:
    """Prefer stem.md (your real CV); fall back to stem.demo.md (repo template)."""
    personal = cv_dir / f"{stem}.md"
    if personal.is_file():
        return personal
    demo = cv_dir / f"{stem}.demo.md"
    if demo.is_file():
        return demo
    return None


def _dir_has_profiles(cv_dir: Path, *, personal_only: bool = False) -> bool:
    for stem in _PROFILE_STEMS:
        if (cv_dir / f"{stem}.md").is_file():
            return True
        if not personal_only and (cv_dir / f"{stem}.demo.md").is_file():
            return True
    return False


def resolve_cv_dir() -> Path:
    """
    Directory used as the CV root for load_default_profiles().

    Precedence:
      1. CV_SOURCE_DIR
      2. ~/private/cv/cv/ (if industry.md or academic.md exists)
      3. shared/cv/ (if your gitignored industry.md or academic.md exists)
      4. shared/cv/ (demo *.demo.md)
    """
    env = os.environ.get("CV_SOURCE_DIR", "").strip()
    if env:
        path = Path(env).expanduser().resolve()
        if path.is_dir() and _dir_has_profiles(path):
            return path

    private = _DEFAULT_PRIVATE_CV_DIR
    if _dir_has_profiles(private, personal_only=True):
        return private

    package = _PACKAGE_CV_DIR
    if (package / "industry.md").is_file() or (package / "academic.md").is_file():
        return package

    return package


# Backward-compatible alias for imports
CV_DIR = resolve_cv_dir()


@dataclass
class JobProfile:
    """Structured view of one CV variant for matching and generation."""

    track: str  # e.g. "academic" | "industry"
    source_path: Path
    front_matter: dict
    body_markdown: str

    @property
    def locations_preferred(self) -> list[str]:
        loc = self.front_matter.get("locations_preferred") or []
        if isinstance(loc, str):
            return [loc]
        return list(loc)

    @property
    def keywords(self) -> list[str]:
        k = self.front_matter.get("keywords") or []
        if isinstance(k, str):
            return [s.strip() for s in k.split(",") if s.strip()]
        return [str(x).strip() for x in k if str(x).strip()]

    @property
    def skills(self) -> list[str]:
        s = self.front_matter.get("skills") or []
        if isinstance(s, str):
            return [x.strip() for x in s.split(",") if x.strip()]
        return [str(x).strip() for x in s if str(x).strip()]

    @property
    def languages(self) -> dict[str, str]:
        raw = self.front_matter.get("languages") or {}
        if not isinstance(raw, dict):
            return {}
        return {str(k).strip(): str(v).strip() for k, v in raw.items()}

    @property
    def seniority_years(self) -> int | None:
        y = self.front_matter.get("seniority_years")
        if y is None:
            return None
        try:
            return int(y)
        except (TypeError, ValueError):
            return None

    def plain_text_summary(self) -> str:
        """Strip markdown-ish noise lightly for keyword pipelines."""
        text = self.body_markdown
        text = re.sub(r"^#+\s+.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"[#*_`]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()


def parse_cv_markdown(raw: str) -> tuple[dict, str]:
    """Split YAML front matter (--- ... ---) from markdown body."""
    raw = raw.lstrip("\ufeff")
    if not raw.startswith("---"):
        return {}, raw
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)$", raw, re.DOTALL)
    if not m:
        return {}, raw
    fm_block, body = m.group(1), m.group(2)
    try:
        meta = yaml.safe_load(fm_block) or {}
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def load_profile(path: Path) -> JobProfile:
    path = path.expanduser().resolve()
    raw = path.read_text(encoding="utf-8")
    front_matter, body = parse_cv_markdown(raw)
    track = str(front_matter.get("track") or path.stem.replace(".demo", ""))
    return JobProfile(
        track=track,
        source_path=path,
        front_matter=front_matter,
        body_markdown=body.strip(),
    )


def load_default_profiles() -> list[JobProfile]:
    """Load industry + academic from resolve_cv_dir() (personal .md preferred over .demo.md)."""
    cv_dir = resolve_cv_dir()
    profiles: list[JobProfile] = []
    for stem in _PROFILE_STEMS:
        p = _profile_path(cv_dir, stem)
        if p is not None:
            profiles.append(load_profile(p))
    return profiles


def main() -> int:
    """CLI: load and print a summary of default CVs."""
    import sys

    cv_dir = resolve_cv_dir()
    if not cv_dir.is_dir():
        print(f"Missing directory: {cv_dir}", file=sys.stderr)
        return 1
    profiles = load_default_profiles()
    if not profiles:
        print(f"No industry/academic (.md or .demo.md) in {cv_dir}", file=sys.stderr)
        return 1
    print(f"CV source dir: {cv_dir}")
    for pr in profiles:
        print(f"--- {pr.track} ({pr.source_path.name}) ---")
        print(f"  locations_preferred: {pr.locations_preferred}")
        print(f"  keywords ({len(pr.keywords)}): {', '.join(pr.keywords[:12])}{'…' if len(pr.keywords) > 12 else ''}")
        print(f"  skills ({len(pr.skills)}): {', '.join(pr.skills[:12])}{'…' if len(pr.skills) > 12 else ''}")
        print(f"  seniority_years: {pr.seniority_years}")
        print(f"  body: {len(pr.body_markdown)} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
