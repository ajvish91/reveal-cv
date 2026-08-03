"""Opt-in debug tracing for the Streamlit job search dashboard."""
from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from secrets import token_hex
from typing import Any

DEBUG_LOG_PATH = Path(__file__).resolve().parent / "data" / "dashboard_debug.log"
MAX_UI_EVENTS = 120
MAX_UI_RERUNS = 12
SESSION_ENABLED_KEY = "dashboard_debug_mode"
SESSION_EVENTS_KEY = "_dashboard_debug_events"
SESSION_EVENT_RECORDS_KEY = "_dashboard_debug_event_records"
SESSION_RERUN_CONTEXT_KEY = "_dashboard_debug_rerun_context"
SESSION_RERUN_HISTORY_KEY = "_dashboard_debug_rerun_history"
SESSION_STATE_SNAPSHOT_KEY = "_dashboard_debug_state_snapshot"
SESSION_LAST_JS_SCROLL_EVENT_KEY = "_dashboard_debug_last_js_scroll_event"

_SENSITIVE_KEY_PARTS = ("description", "notes", "path", "private", "home")
_STATE_PREFIXES = ("job_page_explorer_", "overview_min_score_")
_STATE_KEYS = (
    "apply_dialog_open",
    "apply_dialog_key",
    "pipeline_phase",
    "pipeline_job_key",
    "pipeline_running",
    "pipeline_panel_rendered",
    "pipeline_queue",
    "pipeline_recent_completion",
    "cv_track",
    "show_academic_roles_only",
    "job_explorer_text_search",
    "default_apply_language",
    "default_apply_prompts",
)


def debug_enabled_from_env() -> bool:
    """True when ``JOB_SEARCH_DEBUG=1`` (or true/yes)."""
    return os.environ.get("JOB_SEARCH_DEBUG", "").strip().lower() in ("1", "true", "yes")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _generate_rerun_id() -> str:
    return token_hex(3)


def _sanitize_value(key: str, value: Any) -> Any:
    key_l = key.lower()
    if any(part in key_l for part in _SENSITIVE_KEY_PARTS):
        if value is None:
            return None
        text = str(value)
        if len(text) > 80:
            return f"{text[:77]}..."
        return "[redacted]"
    if isinstance(value, str) and len(value) > 200:
        return f"{value[:197]}..."
    if isinstance(value, (list, tuple)):
        return [_sanitize_value(key, item) for item in list(value)[:12]]
    if isinstance(value, dict):
        return {str(k): _sanitize_value(str(k), v) for k, v in list(value.items())[:20]}
    return value


def _sanitize_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {key: _sanitize_value(key, value) for key, value in kwargs.items()}


def _format_event(record: dict[str, Any]) -> str:
    payload = {k: v for k, v in record.items() if k not in ("timestamp", "event")}
    if payload:
        details = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)
        return f"{record['timestamp']} {record['event']} {details}"
    return f"{record['timestamp']} {record['event']}"


def _append_file(line: str) -> None:
    try:
        DEBUG_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with DEBUG_LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        pass


def _hash_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]


def short_fingerprint(value: Any) -> str:
    """Stable short hash for debug-visible cache keys and filters."""
    try:
        encoded = json.dumps(value, ensure_ascii=True, default=str, sort_keys=True)
    except TypeError:
        encoded = repr(value)
    return _hash_text(encoded)


def init_dashboard_debug(session_state: Any) -> None:
    """Seed debug session keys (safe when Streamlit is unavailable)."""
    if debug_enabled_from_env():
        session_state[SESSION_ENABLED_KEY] = True
    if SESSION_EVENTS_KEY not in session_state:
        session_state[SESSION_EVENTS_KEY] = []
    if SESSION_EVENT_RECORDS_KEY not in session_state:
        session_state[SESSION_EVENT_RECORDS_KEY] = []
    if SESSION_RERUN_HISTORY_KEY not in session_state:
        session_state[SESSION_RERUN_HISTORY_KEY] = []
    if SESSION_RERUN_CONTEXT_KEY not in session_state:
        session_state[SESSION_RERUN_CONTEXT_KEY] = {"completed": True}
    if SESSION_STATE_SNAPSHOT_KEY not in session_state:
        session_state[SESSION_STATE_SNAPSHOT_KEY] = {}


def is_debug_enabled(session_state: Any) -> bool:
    return debug_enabled_from_env() or bool(session_state.get(SESSION_ENABLED_KEY))


def _active_rerun_context(session_state: Any | None) -> dict[str, Any]:
    if session_state is None:
        return {}
    return dict(session_state.get(SESSION_RERUN_CONTEXT_KEY) or {})


def start_rerun_trace(
    session_state: Any,
    *,
    scope: str,
    trigger: str | None = None,
    force_new: bool = False,
) -> dict[str, Any]:
    """Start a new rerun trace if needed, else reuse the active trace."""
    init_dashboard_debug(session_state)
    ctx = dict(session_state.get(SESSION_RERUN_CONTEXT_KEY) or {})
    should_start = force_new or not ctx or ctx.get("completed", True)
    if should_start:
        ctx = {
            "rerun_id": _generate_rerun_id(),
            "scope": scope,
            "trigger": trigger or "unknown",
            "started_at": time.monotonic(),
            "started_ts": _utc_now(),
            "completed": False,
        }
        session_state[SESSION_RERUN_CONTEXT_KEY] = ctx
        debug_log(
            "rerun_start",
            session_state=session_state,
            scope=scope,
            trigger=ctx["trigger"],
        )
        return ctx
    if scope and not ctx.get("scope"):
        ctx["scope"] = scope
        session_state[SESSION_RERUN_CONTEXT_KEY] = ctx
    if trigger and ctx.get("trigger") != trigger:
        ctx["trigger"] = trigger
        session_state[SESSION_RERUN_CONTEXT_KEY] = ctx
    return ctx


def finish_rerun_trace(session_state: Any, *, note: str | None = None) -> dict[str, Any]:
    """Mark the active rerun trace complete and retain a short sidebar summary."""
    ctx = dict(session_state.get(SESSION_RERUN_CONTEXT_KEY) or {})
    if not ctx or ctx.get("completed"):
        return ctx
    elapsed_ms = round((time.monotonic() - float(ctx.get("started_at") or time.monotonic())) * 1000.0, 1)
    ctx["completed"] = True
    ctx["elapsed_ms"] = elapsed_ms
    if note:
        ctx["note"] = note
    session_state[SESSION_RERUN_CONTEXT_KEY] = ctx
    history = list(session_state.get(SESSION_RERUN_HISTORY_KEY) or [])
    history.append(
        {
            "rerun_id": ctx.get("rerun_id"),
            "scope": ctx.get("scope"),
            "trigger": ctx.get("trigger"),
            "elapsed_ms": elapsed_ms,
            "note": note,
        }
    )
    session_state[SESSION_RERUN_HISTORY_KEY] = history[-MAX_UI_RERUNS:]
    return ctx


def debug_log(event: str, session_state: Any | None = None, **kwargs: Any) -> None:
    """Append one debug event to the in-session ring buffer and optional log file."""
    if session_state is not None and not is_debug_enabled(session_state):
        return
    if session_state is None and not debug_enabled_from_env():
        return

    payload = dict(kwargs)
    ctx = _active_rerun_context(session_state)
    if ctx.get("rerun_id") and "rerun_id" not in payload:
        payload["rerun_id"] = ctx["rerun_id"]
    if ctx.get("scope") and "scope" not in payload:
        payload["scope"] = ctx["scope"]
    record = {"timestamp": _utc_now(), "event": event, **_sanitize_kwargs(payload)}
    line = _format_event(record)
    if session_state is not None:
        events = list(session_state.get(SESSION_EVENTS_KEY) or [])
        events.append(line)
        session_state[SESSION_EVENTS_KEY] = events[-MAX_UI_EVENTS:]
        records = list(session_state.get(SESSION_EVENT_RECORDS_KEY) or [])
        records.append(record)
        session_state[SESSION_EVENT_RECORDS_KEY] = records[-MAX_UI_EVENTS:]
    _append_file(line)


@contextmanager
def timing_span(
    event: str,
    *,
    session_state: Any | None,
    label: str,
    scope: str | None = None,
    **kwargs: Any,
):
    """Context manager that logs a timing event on exit."""
    started = time.monotonic()
    try:
        yield
    finally:
        duration_ms = round((time.monotonic() - started) * 1000.0, 1)
        debug_log(
            event,
            session_state=session_state,
            label=label,
            duration_ms=duration_ms,
            scope=scope,
            **kwargs,
        )


def _normalize_state_value(value: Any) -> Any:
    if isinstance(value, str):
        value = value.strip()
        return value if len(value) <= 120 else f"{value[:117]}..."
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in list(value)[:10]]
    if isinstance(value, dict):
        return {str(k): _normalize_state_value(v) for k, v in list(value.items())[:12]}
    return value


def snapshot_state_subset(session_state: Any) -> dict[str, Any]:
    """Snapshot a small, high-signal subset of session state for rerun diffs."""
    snapshot: dict[str, Any] = {}
    for key in _STATE_KEYS:
        if key in session_state:
            snapshot[key] = _normalize_state_value(session_state.get(key))
    for key in sorted(session_state.keys()):
        if any(key.startswith(prefix) for prefix in _STATE_PREFIXES):
            snapshot[key] = _normalize_state_value(session_state.get(key))
    return snapshot


def log_state_diff(session_state: Any) -> dict[str, Any]:
    """Log only state keys that changed since the previous completed rerun."""
    current = snapshot_state_subset(session_state)
    previous = dict(session_state.get(SESSION_STATE_SNAPSHOT_KEY) or {})
    changed: dict[str, Any] = {}
    for key in sorted(set(previous) | set(current)):
        before = previous.get(key)
        after = current.get(key)
        if before != after:
            changed[key] = {"before": before, "after": after}
    session_state[SESSION_STATE_SNAPSHOT_KEY] = current
    if changed:
        debug_log("state_diff", session_state=session_state, changed=changed, changed_keys=list(changed))
    return changed


def note_js_scroll_event(session_state: Any, **payload: Any) -> bool:
    """Log one JS-side scroll event once, even across repeated fragment reruns."""
    if not is_debug_enabled(session_state):
        return False
    key = json.dumps(_sanitize_kwargs(payload), ensure_ascii=True, default=str, sort_keys=True)
    if session_state.get(SESSION_LAST_JS_SCROLL_EVENT_KEY) == key:
        return False
    session_state[SESSION_LAST_JS_SCROLL_EVENT_KEY] = key
    debug_log("scroll_timeline", session_state=session_state, **payload)
    return True


def recent_debug_events(session_state: Any, *, limit: int = MAX_UI_EVENTS) -> list[str]:
    events = list(session_state.get(SESSION_EVENTS_KEY) or [])
    return events[-limit:]


def recent_debug_records(session_state: Any, *, limit: int = MAX_UI_EVENTS) -> list[dict[str, Any]]:
    records = list(session_state.get(SESSION_EVENT_RECORDS_KEY) or [])
    return records[-limit:]


def summarize_recent_reruns(session_state: Any, *, limit: int = MAX_UI_RERUNS) -> list[dict[str, Any]]:
    """Group recent records by rerun id for the debug sidebar timeline."""
    grouped: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for record in recent_debug_records(session_state):
        rerun_id = record.get("rerun_id")
        if not rerun_id:
            continue
        if current is None or current["rerun_id"] != rerun_id:
            current = {
                "rerun_id": rerun_id,
                "scope": record.get("scope"),
                "trigger": None,
                "duration_ms": None,
                "state_changes": [],
                "expensive": [],
                "scroll": [],
            }
            grouped.append(current)
        if record["event"] == "rerun_start":
            current["trigger"] = record.get("trigger")
            current["scope"] = record.get("scope") or current["scope"]
        elif record["event"] == "state_diff":
            keys = list(record.get("changed_keys") or [])
            current["state_changes"].extend(str(key) for key in keys[:12])
        elif record["event"] in ("render_timing", "data_load_timing"):
            label = str(record.get("label") or "timing")
            duration = record.get("duration_ms")
            current["expensive"].append(f"{label} {duration}ms")
            if record["event"] == "render_timing" and label == "main_render":
                current["duration_ms"] = duration
        elif record["event"] == "scroll_timeline":
            action = str(record.get("action") or "scroll")
            current["scroll"].append(action)
    return grouped[-limit:][::-1]


def render_debug_sidebar(session_state: Any) -> None:
    """Sidebar toggle and trace expander (requires Streamlit)."""
    import streamlit as st

    init_dashboard_debug(session_state)
    env_on = debug_enabled_from_env()
    if env_on:
        st.sidebar.caption("Debug mode: on (`JOB_SEARCH_DEBUG=1`)")
    st.sidebar.checkbox(
        "Debug mode",
        value=bool(session_state.get(SESSION_ENABLED_KEY)),
        key=SESSION_ENABLED_KEY,
        disabled=env_on,
        help="Log dashboard reruns, loaders, state diffs, cache reuse, and scroll hooks.",
    )
    if not is_debug_enabled(session_state):
        return

    with st.sidebar.expander("Debug timeline", expanded=False):
        reruns = summarize_recent_reruns(session_state)
        if not reruns:
            st.caption("No reruns captured yet this session.")
        for item in reruns:
            trigger = item.get("trigger") or "unknown"
            scope = item.get("scope") or "unknown"
            duration = item.get("duration_ms")
            title = f"{item['rerun_id']} | {scope} | {trigger}"
            with st.expander(title, expanded=False):
                if duration is not None:
                    st.caption(f"Duration: {duration} ms")
                changes = item.get("state_changes") or []
                if changes:
                    st.caption("State changes: " + ", ".join(dict.fromkeys(changes)))
                expensive = item.get("expensive") or []
                if expensive:
                    st.caption("Expensive work: " + "; ".join(expensive[:6]))
                scroll = item.get("scroll") or []
                if scroll:
                    st.caption("Scroll: " + ", ".join(dict.fromkeys(scroll)))

    with st.sidebar.expander("Debug trace (raw)", expanded=False):
        events = recent_debug_events(session_state)
        if events:
            st.code("\n".join(events), language="text")
        else:
            st.caption("No events yet this session.")
