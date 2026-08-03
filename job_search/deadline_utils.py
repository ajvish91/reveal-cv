"""Parse job application deadlines and compute urgency."""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

# ISO: 2026-08-15, 2026-08-15T23:59:59Z, 2026-08-15T23:59:59+02:00
_ISO_DATE_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})"
    r"(?:[T\s](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)
# Norwegian / dotted: 15.08.2026, 15.08.26
_DOTTED_DATE_RE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{2,4})\b")
# "15. august 2026" / "15 august 2026"
_NO_MONTH_DATE_RE = re.compile(
    r"\b(\d{1,2})\.?\s+"
    r"(januar|februar|mars|april|mai|juni|juli|august|september|oktober|november|desember)"
    r"\s+(\d{4})\b",
    re.IGNORECASE,
)

_NO_MONTHS = {
    "januar": 1,
    "februar": 2,
    "mars": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "desember": 12,
}

# schema.org / scrape artefacts that must never appear as a deadline label
_GARBAGE_EXPIRES_VALUES = frozenset(
    {
        "place",
        "@type",
        "jobposting",
        "postaladdress",
        "organization",
        "applicationdue",
    }
)
_VALID_THROUGH_IN_JSON_RE = re.compile(r'"validThrough"\s*:\s*"([^"]+)"', re.IGNORECASE)


def _normalize_year(year: int) -> int:
    if year < 100:
        return 2000 + year if year < 70 else 1900 + year
    return year


def _safe_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(_normalize_year(year), month, day)
    except ValueError:
        return None


def coerce_expires_value(value: Any) -> str | None:
    """Normalize expires / validThrough from DB, API, or JSON-LD to a plain string or None."""
    if value is None:
        return None
    if isinstance(value, float) and str(value) == "nan":
        return None
    if isinstance(value, dict):
        for key in ("validThrough", "date", "value", "expires", "endDate", "applicationDue"):
            if key in value:
                inner = coerce_expires_value(value[key])
                if inner:
                    return inner
        if str(value.get("@type") or "").casefold() == "place":
            return None
        return None
    text = str(value).strip()
    if not text:
        return None
    low = text.casefold()
    if low in _GARBAGE_EXPIRES_VALUES:
        return None
    if low == "place" or low.startswith("place,") or low.startswith("place "):
        return None
    if text.startswith("{") and "@type" in text and "place" in low:
        match = _VALID_THROUGH_IN_JSON_RE.search(text)
        if match:
            return coerce_expires_value(match.group(1))
        return None
    return text


def parse_deadline(value: str | None) -> date | None:
    """Parse ISO or Norwegian deadline text into a calendar date."""
    if value is None:
        return None
    text = coerce_expires_value(value)
    if not text:
        return None

    match = _ISO_DATE_RE.match(text)
    if match:
        y, m, d = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return _safe_date(y, m, d)

    match = _NO_MONTH_DATE_RE.search(text)
    if match:
        day = int(match.group(1))
        month = _NO_MONTHS[match.group(2).casefold()]
        year = int(match.group(3))
        return _safe_date(year, month, day)

    for match in _DOTTED_DATE_RE.finditer(text):
        day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        parsed = _safe_date(year, month, day)
        if parsed is not None:
            return parsed

    return None


def reference_today(today: date | None = None) -> date:
    if today is not None:
        return today
    return datetime.now(timezone.utc).date()


def days_until_deadline(
    value: str | None,
    *,
    today: date | None = None,
) -> int | None:
    """Days from today until deadline (0 = today). None if unknown or past parsing."""
    deadline = parse_deadline(value)
    if deadline is None:
        return None
    ref = reference_today(today)
    return (deadline - ref).days


def is_apply_soon(
    value: str | None,
    *,
    within_days: int = 7,
    today: date | None = None,
) -> bool:
    """True when deadline is today or within the next ``within_days`` days."""
    days = days_until_deadline(value, today=today)
    if days is None:
        return False
    return 0 <= days <= within_days


def deadline_display(value: str | None) -> str:
    """Human-readable deadline label for tables; em dash when unknown or garbage."""
    coerced = coerce_expires_value(value)
    if not coerced:
        return "—"
    parsed = parse_deadline(coerced)
    if parsed is not None:
        return parsed.isoformat()
    return "—"


def apply_soon_badge(
    value: str | None,
    *,
    within_days: int = 7,
    today: date | None = None,
) -> str:
    """Return urgency badge text or empty string."""
    days = days_until_deadline(value, today=today)
    if days is None:
        return ""
    if days < 0:
        return "Expired"
    if 0 <= days <= within_days:
        if days == 0:
            return "Apply soon (today)"
        if days == 1:
            return "Apply soon (1d)"
        return f"Apply soon ({days}d)"
    return ""


def row_expires(row: dict[str, Any] | Any) -> str | None:
    """Extract expires field from a DB row or pandas Series."""
    if hasattr(row, "get"):
        val = row.get("expires")
    else:
        val = getattr(row, "expires", None)
    return coerce_expires_value(val)
