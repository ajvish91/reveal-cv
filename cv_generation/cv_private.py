#!/usr/bin/env python3
"""
Resolve private paths and URLs from env or mapping file outside the repo.

Keys in the identity mapping JSON that start with ``_`` are metadata (not search/replace
keys themselves). Supported metadata:

- ``_profile_photo_path`` — headshot image for PDF render
- ``_github_url`` — full GitHub profile URL (https://github.com/…)
- ``_linkedin_url`` — full LinkedIn profile URL (https://linkedin.com/in/… or https://www.linkedin.com/in/…)
- ``_google_scholar_url`` — full Google Scholar profile URL (academic CV contact lines only)
- ``_orcid_url`` — full ORCID profile URL (academic CV contact lines only; industry CVs ignore if absent)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

MAPPING_ENV = "CV_IDENTITY_MAPPING"
PROFILE_PHOTO_ENV = "CV_PROFILE_PHOTO"
PROFILE_PHOTO_MAPPING_KEY = "_profile_photo_path"
GITHUB_URL_MAPPING_KEY = "_github_url"
LINKEDIN_URL_MAPPING_KEY = "_linkedin_url"
GOOGLE_SCHOLAR_URL_MAPPING_KEY = "_google_scholar_url"
ORCID_URL_MAPPING_KEY = "_orcid_url"
ANON_GITHUB_URL = "https://github.com/cv-placeholder"
ANON_LINKEDIN_URL = "https://linkedin.com/in/cv-placeholder"
ANON_GOOGLE_SCHOLAR_URL = "https://scholar.google.com/citations?user=cv-placeholder"
ANON_ORCID_URL = "https://orcid.org/0000-0000-0000-0000"


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def profile_photo_from_mapping(mapping_path: Path) -> Path | None:
    raw = _mapping_raw(mapping_path)
    if not raw:
        return None
    value = raw.get(PROFILE_PHOTO_MAPPING_KEY)
    if not isinstance(value, str) or not value.strip():
        return None
    photo = _expand(value.strip())
    return photo if photo.is_file() else None


def _mapping_raw(mapping_path: Path) -> dict:
    if not mapping_path.is_file():
        return {}
    try:
        raw = json.loads(mapping_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _is_real_http_url(value: str) -> bool:
    text = value.strip()
    return bool(text) and text.startswith(("http://", "https://")) and not text.startswith("REPLACE_WITH_")


def social_url_replacements_from_raw(raw: dict) -> dict[str, str]:
    """
    Build deanonymize search/replace pairs from ``_*_url`` metadata keys.

    Template CVs use anonymized URLs; private mapping supplies your real profile URLs.
  """
    pairs: dict[str, str] = {}
    for meta_key, anon_url, label in (
        (GITHUB_URL_MAPPING_KEY, ANON_GITHUB_URL, "GitHub"),
        (LINKEDIN_URL_MAPPING_KEY, ANON_LINKEDIN_URL, "LinkedIn"),
        (GOOGLE_SCHOLAR_URL_MAPPING_KEY, ANON_GOOGLE_SCHOLAR_URL, "Google Scholar"),
        (ORCID_URL_MAPPING_KEY, ANON_ORCID_URL, "ORCID"),
    ):
        val = raw.get(meta_key)
        if not isinstance(val, str) or not _is_real_http_url(val):
            continue
        real = val.strip()
        pairs[anon_url] = real
        pairs[f"{label}: {anon_url}"] = f"{label}: {real}"
    return pairs


def resolve_profile_photo_path(explicit: str | Path | None = None) -> Path | None:
    """
    Return path to a profile photo file, or None to use the in-repo placeholder.

    Precedence: explicit argument > CV_PROFILE_PHOTO > _profile_photo_path in mapping JSON.
    """
    if explicit:
        candidate = _expand(explicit)
        if candidate.is_file():
            return candidate

    env_path = os.environ.get(PROFILE_PHOTO_ENV, "").strip()
    if env_path:
        candidate = _expand(env_path)
        if candidate.is_file():
            return candidate

    mapping_env = os.environ.get(MAPPING_ENV, "").strip()
    if mapping_env:
        from_mapping = profile_photo_from_mapping(_expand(mapping_env))
        if from_mapping is not None:
            return from_mapping

    return None
