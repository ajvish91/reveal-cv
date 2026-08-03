"""Shared industry vs academic CV track detection (used by PDF layout and tooling)."""
from __future__ import annotations

from typing import Literal

Track = Literal["industry", "academic"]


def cv_track_from_title(title: str) -> Track:
    """
    Detect track from markdown H1 (e.g. ``# Industry CV``, ``# Academic CV``).

    Industry (corporate) is the default when the title is ambiguous.
    """
    t = (title or "").strip().lower()
    if "academic" in t or "akademisk" in t:
        return "academic"
    return "industry"


def is_academic_title(title: str) -> bool:
    return cv_track_from_title(title) == "academic"


def is_industry_title(title: str) -> bool:
    return cv_track_from_title(title) == "industry"
