"""Dashboard data refresh helpers (no Streamlit dependency)."""
from __future__ import annotations

AUTO_REFRESH_MINUTE_OPTIONS: tuple[int, ...] = (0, 2, 5, 10)


def refresh_interval_seconds(minutes: int) -> int | None:
    """Return interval length in seconds, or ``None`` when auto-refresh is off."""
    if minutes <= 0:
        return None
    return minutes * 60


def format_auto_refresh_label(minutes: int) -> str:
    if minutes <= 0:
        return "Off"
    return f"Every {minutes} min"


def should_periodic_refresh(
    *,
    interval_minutes: int,
    last_refresh_monotonic: float,
    now_monotonic: float,
) -> bool:
    """True when ``now_monotonic`` is at or past the next scheduled cache refresh."""
    interval_s = refresh_interval_seconds(interval_minutes)
    if interval_s is None:
        return False
    return (now_monotonic - last_refresh_monotonic) >= interval_s
