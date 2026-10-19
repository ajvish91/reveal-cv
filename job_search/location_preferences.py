from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from shared.cv_loader import JobProfile

_SEPARATOR_RE = re.compile(r"[^0-9A-ZÆØÅ]+")
_BROAD_TOKENS = {
    "NORGE",
    "NORWAY",
    "REMOTE",
    "HYBRID",
}


def normalize_location_token(text: str | None) -> str:
    token = _SEPARATOR_RE.sub(" ", (text or "").strip().upper())
    return re.sub(r"\s+", " ", token).strip()


@dataclass(frozen=True)
class LocationMatch:
    matched: bool
    label: str | None = None


def _preferred_tokens(preferred_locations: Iterable[str]) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw in preferred_locations:
        token = normalize_location_token(raw)
        if not token or token in _BROAD_TOKENS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _candidate_tokens(
    municipal: str | None,
    county: str | None,
    feed_municipal: str | None = None,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in (municipal, county, feed_municipal):
        token = normalize_location_token(raw)
        if token and token not in seen:
            seen.add(token)
            out.append(token)
    return out


def match_preferred_location(
    preferred_locations: Iterable[str],
    *,
    municipal: str | None,
    county: str | None,
    feed_municipal: str | None = None,
) -> LocationMatch:
    wanted = _preferred_tokens(preferred_locations)
    if not wanted:
        return LocationMatch(False, None)
    candidates = _candidate_tokens(municipal, county, feed_municipal)
    for preferred in wanted:
        for candidate in candidates:
            if candidate == preferred:
                return LocationMatch(True, preferred.title())
    return LocationMatch(False, None)


def merged_preferred_locations(profiles: Iterable[JobProfile]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for profile in profiles:
        for raw in profile.locations_preferred:
            token = normalize_location_token(raw)
            if not token or token in _BROAD_TOKENS or token in seen:
                continue
            seen.add(token)
            out.append(raw)
    return out
