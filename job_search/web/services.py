#!/usr/bin/env python3
"""Streamlit-free job-search dashboard services (filters, loads, ingest, apply pipeline)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from collections.abc import Mapping
from typing import Any

_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd

from cv_generation.apply_prompts import (
    merge_apply_prompts,
    normalize_apply_language,
)
from cv_generation.cv_application_artifacts import (
    CV_MARKDOWN,
    detect_supplementary_artifacts,
    supplementary_artifact_filenames,
)
from cv_generation.pipeline_metrics import (
    format_pipeline_metrics_summary,
    load_pipeline_metrics,
    resolve_run_dir,
)
from job_search.deadline_utils import (
    apply_soon_badge,
    deadline_display,
    is_apply_soon,
    is_expired,
    row_expires,
)
from job_search.job_db import (
    DEFAULT_DB_PATH,
    connect,
    delete_application,
    init_schema,
    upsert_application,
    upsert_job,
    utc_now_iso,
)
from job_search.job_dedup import dedupe_jobs_df as _dedupe_jobs_df
from job_search.job_filters import (
    ACADEMIC_ROLE_TITLE_TERMS,
    haystack_for_filter,
    has_profile_relevance,
    matches_academic_role_display,
    matches_any_include_term,
    matches_exclude_terms,
    matches_phd_student_opening,
    merge_exclude_terms,
    merge_include_terms,
    sql_require_academic_role_display,
    sql_exclude_fragments,
    sql_phd_student_exclude,
    sql_require_any_include,
    sql_require_profile_relevance,
)
from job_search.logging_config import get_logger

log = get_logger("job_search.web")

STATUS_OPTIONS = [
    "interested",
    "drafted",
    "applied",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "skipped",
]

QUICK_JOB_ACTIONS = (
    "pin",
    "unpin",
    "mark_applied",
    "skip",
    "interested",
    "reject",
    "withdraw",
    "clear",
    "mark_expired",
)

DEFAULT_DRAFTS_STATUS_FILTER = ("drafted",)

DEFAULT_APPLIED_STATUS_FILTER = ("applied", "interested")

DRAFTS_STATUS_OPTIONS = ["drafted"]

JOB_EXPLORER_ROW_COLUMNS = [5.0, 0.9, 1.0, 1.3]

APPLIED_ROLE_ROW_COLUMNS = [5.0, 1.1, 0.7, 1.3, 1.2]

APPLIED_ROLE_ROW_COLUMNS_DRAFTED = [4.6, 1.0, 0.6, 1.15, 1.4, 1.1]

MODIFY_STATUSES = frozenset(
    {"drafted", "applied", "interview", "offer", "rejected", "withdrawn"}
)

# Hidden from explorer when "Hide jobs with an application" is on (pinned still show).
HIDE_APPLIED_STATUSES = MODIFY_STATUSES | frozenset({"skipped"})

DEFAULT_HIDE_APPLIED = True

DEFAULT_HIDE_EXPIRED = True

DEFAULT_DEDUPE_CROSS_SOURCE = True

PIPELINE_TOTAL_STEPS = 11

PIPELINE_LOG_MAX_LINES = 100

PIPELINE_POLL_SECONDS = 0.75

PIPELINE_MAX_WAITING = 2

PIPELINE_MAX_IN_FLIGHT = 1 + PIPELINE_MAX_WAITING

LOG_DELETE_BUTTON_COLUMNS = [1.2, 8.8]

_PIPELINE_WORKERS_ATTR = "_job_search_apply_pipeline_workers_v1"

def _pipeline_worker_registry() -> tuple[threading.Lock, dict[str, dict[str, Any]]]:
    reg = getattr(sys, _PIPELINE_WORKERS_ATTR, None)
    if not isinstance(reg, dict) or "lock" not in reg or "workers" not in reg:
        reg = {"lock": threading.Lock(), "workers": {}}
        setattr(sys, _PIPELINE_WORKERS_ATTR, reg)
    return reg["lock"], reg["workers"]


_STATUS_BADGE_COLOR = {
    "interested": "blue",
    "drafted": "orange",
    "applied": "green",
    "interview": "violet",
    "offer": "green",
    "rejected": "red",
    "withdrawn": "gray",
    "skipped": "gray",
}

_CV_RUN_NOTES_RE = re.compile(r"CV run:\s*(.+?)(?:\s*\(Norwegian\))?\s*$")

_CACHE_EXEC_COUNTS: dict[str, int] = {}

CV_JOBS_DIR = _root / "cv_generation" / "jobs"

_SOURCE_PREFIX = {
    "finn_no": "finn",
    "nav_arbeidsplassen": "nav",
    "jobbnorge": "jobbnorge",
}

_JOB_SELECT_COLUMNS = """
        j.uuid,
        j.source,
        j.title,
        j.jobtitle,
        j.employer_name,
        j.county,
        j.municipal,
        j.in_rogaland,
        j.location_matched,
        j.location_label,
        j.link,
        j.application_url,
        j.published,
        j.expires,
        j.description_text,
        j.status AS job_status,
        j.fetched_at,
        s.track,
        s.score_total,
        s.score_base,
        s.boost_rogaland,
        s.boost_tek,
        s.matched_keywords,
        s.matched_skills,
        s.tek_match_name,
        ap.status AS app_status,
        ap.applied_at,
        ap.notes AS app_notes,
        COALESCE(ap.pinned, 0) AS pinned
"""

def title_slug(title: str, max_len: int = 48) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", (title or "").strip().lower()).strip("_")
    return (value[:max_len] if value else "role")


def _mark_cache_exec(name: str) -> None:
    _CACHE_EXEC_COUNTS[name] = int(_CACHE_EXEC_COUNTS.get(name) or 0) + 1


def _cache_exec_count(name: str) -> int:
    return int(_CACHE_EXEC_COUNTS.get(name) or 0)


def cv_job_filename(source: str, uuid: str, title: str) -> str:
    prefix = _SOURCE_PREFIX.get(source, "job")
    safe_uuid = re.sub(r"[^a-zA-Z0-9-]+", "", uuid or "unknown")
    return f"{prefix}_{safe_uuid}_{title_slug(title)}.txt"


def _subprocess_env() -> dict[str, str]:
    """Env for child Python processes so stdout lines flush while piped."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    return env


def resolve_project_python(explicit: str | None = None) -> str:
    """Interpreter for dashboard subprocesses (CV Apply, ingest cycle).

    Prefer ``PROJECT_ROOT/.venv/bin/python`` (or ``python3``) when that binary
    exists and is executable, so children get project dependencies even if the
    dashboard itself was launched with system/miniconda Python. Fall back to
    ``sys.executable`` when no project venv is present.
    """
    if explicit:
        return explicit
    for name in ("python", "python3"):
        candidate = _root / ".venv" / "bin" / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return sys.executable


def source_label_short(source: str) -> str:
    if source == "finn_no":
        return "FINN"
    if source == "nav_arbeidsplassen":
        return "NAV"
    if source == "jobbnorge":
        return "Jobbnorge"
    return (source or "?")[:12]


def source_display(source: str, uuid: str) -> str:
    if source == "finn_no":
        return f"FINN.no (ad {uuid})"
    if source == "nav_arbeidsplassen":
        return "NAV Arbeidsplassen"
    if source == "jobbnorge":
        return f"Jobbnorge (id {uuid})"
    return source or "unknown"


def _safe_str(val: object) -> str:
    """Coerce pandas/DB cell values to stripped str; None/NaN -> ''."""
    if val is None:
        return ""
    try:
        if pd.isna(val):
            return ""
    except (TypeError, ValueError):
        pass
    return str(val).strip()


def format_location(row: dict[str, Any]) -> str:
    label = _safe_str(row.get("location_label"))
    if label:
        return label
    municipal = _safe_str(row.get("municipal"))
    county = _safe_str(row.get("county"))
    if municipal and county:
        return f"{municipal}, {county}"
    return municipal or county or ""


def format_job_export_text(row: dict[str, Any]) -> str:
    lines = [
        f"Role: {_safe_str(row.get('title'))}",
        f"Company: {_safe_str(row.get('employer_name'))}",
        f"Source: {source_display(_safe_str(row.get('source')), _safe_str(row.get('uuid')))}",
        f"Location: {format_location(row)}",
        "",
        _safe_str(row.get("description_text")),
    ]
    return "\n".join(lines).strip() + "\n"


def export_job_to_cv_file(row: dict[str, Any], jobs_dir: Path | None = None) -> Path:
    out_dir = jobs_dir or CV_JOBS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / cv_job_filename(
        str(row.get("source") or ""),
        str(row.get("uuid") or ""),
        str(row.get("title") or ""),
    )
    path.write_text(format_job_export_text(row), encoding="utf-8")
    return path


def run_cv_tailoring_subprocess(
    job_file: Path,
    *,
    company: str,
    role: str,
    apply_prompts: str | None = None,
    language: str = "en",
    run_dir: Path | None = None,
    force: bool = False,
    python_exe: str | None = None,
) -> tuple[int, str, str]:
    exe = resolve_project_python(python_exe)
    cmd = [
        exe,
        "-m",
        "cv_generation.run_cv_tailoring",
        "--job-file",
        str(job_file),
        "--company",
        company,
        "--role",
        role,
        "--output-language",
        normalize_apply_language(language),
    ]
    if run_dir is not None:
        cmd.extend(["--run-dir", str(run_dir)])
        if force:
            cmd.append("--force")
    merged_prompts = merge_apply_prompts(apply_prompts)
    if merged_prompts:
        cmd.extend(["--apply-prompts", merged_prompts])
    proc = subprocess.run(
        cmd,
        cwd=str(_root),
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


@dataclass
class ApplyPipelineOptions:
    """User-selected Apply / Modify pipeline options from the dashboard dialog."""

    language: str = "en"
    provider: str = ""
    model: str = ""
    apply_prompts: str | None = None
    generate_cover_letter: bool = True
    generate_application_letter: bool = False
    generate_research_proposal: bool = False
    overwrite_cv: bool = False
    overwrite_cover_letter: bool = False
    overwrite_application_letter: bool = False
    overwrite_research_proposal: bool = False
    modify_mode: bool = False
    existing_run_id: str | None = None


_APPLY_PIPELINE_OPTION_FIELDS = {field.name for field in fields(ApplyPipelineOptions)}

def apply_dialog_language_key(key_prefix: str) -> str:
    return f"{key_prefix}_dialog_language"


def apply_pipeline_options_to_mapping(opts: ApplyPipelineOptions) -> dict[str, Any]:
    """Serialize options for ``pipeline_params`` (Streamlit-safe plain dict)."""
    data = asdict(opts)
    data["language"] = normalize_apply_language(data.get("language"))
    return data


def apply_pipeline_options_from_mapping(
    raw: Any,
    *,
    language: str | None = None,
) -> ApplyPipelineOptions:
    """Rebuild options from session state / worker params; never silently drop language."""
    if isinstance(raw, ApplyPipelineOptions):
        payload = asdict(raw)
    elif isinstance(raw, dict):
        payload = dict(raw)
    else:
        payload = {}
    if language is not None:
        payload["language"] = normalize_apply_language(language)
    else:
        payload["language"] = normalize_apply_language(payload.get("language"))
    kwargs = {name: payload[name] for name in _APPLY_PIPELINE_OPTION_FIELDS if name in payload}
    if "language" not in kwargs:
        kwargs["language"] = normalize_apply_language(language)
    return ApplyPipelineOptions(**kwargs)


def apply_button_label(app_status: str | None) -> str:
    status = (app_status or "").strip()
    if status in MODIFY_STATUSES:
        return "Modify"
    return "Apply"


def is_modify_mode(app_status: str | None) -> bool:
    return (app_status or "").strip() in MODIFY_STATUSES


def default_artifact_options(job_text: str, *, track: str) -> dict[str, bool]:
    """Pre-check artifact generation toggles from posting detection."""
    detected = {artifact.filename for artifact in detect_supplementary_artifacts(job_text, track=track)}
    if track == "academic":
        return {
            # Application letter is the academic default; cover letter only when JD asks.
            "generate_cover_letter": "cover_letter.md" in detected,
            "generate_application_letter": True,
            "generate_research_proposal": "research_proposal.md" in detected,
        }
    return {
        "generate_cover_letter": "cover_letter.md" in detected or track == "industry",
        "generate_application_letter": False,
        "generate_research_proposal": False,
    }


def row_suggests_academic_documents(row_dict: dict[str, Any]) -> bool:
    """True when title/employer look like a postdoc/researcher call (cheap; no JD regex)."""
    title = str(row_dict.get("title") or "")
    jobtitle = str(row_dict.get("jobtitle") or title)
    employer = str(row_dict.get("employer_name") or "")
    return matches_academic_role_display(title, jobtitle, None, employer)


def existing_artifact_flags(run_dir: Path | None) -> dict[str, bool]:
    """Which supplementary artifacts already exist in a run folder."""
    flags = {name: False for name in supplementary_artifact_filenames()}
    flags[CV_MARKDOWN] = False
    if run_dir is None or not run_dir.is_dir():
        return flags
    flags[CV_MARKDOWN] = (run_dir / CV_MARKDOWN).is_file()
    for name in supplementary_artifact_filenames():
        flags[name] = (run_dir / name).is_file()
    return flags


def resolve_modify_run_dir(notes: str | None, *, run_id: str | None = None) -> Path | None:
    if run_id:
        return resolve_run_dir(run_id, repo_root=_root)
    run_ids = extract_run_ids_from_notes(notes)
    if not run_ids:
        return None
    return resolve_run_dir(run_ids[-1], repo_root=_root)


def _dialog_artifact_bundle(
    row_dict: dict[str, Any],
    *,
    track: str,
    modify: bool,
) -> dict[str, Any]:
    """One-shot artifact defaults / existing-file flags for the Apply dialog."""
    existing_run: Path | None = None
    existing_flags: dict[str, bool] = {}
    if modify:
        existing_run = resolve_modify_run_dir(row_dict.get("app_notes"))
        existing_flags = existing_artifact_flags(existing_run)

    has_academic_files = bool(
        existing_flags.get("application_letter.md") or existing_flags.get("research_proposal.md")
    )
    looks_academic = track == "academic" or row_suggests_academic_documents(row_dict)
    show_academic_docs = track == "academic" or looks_academic or has_academic_files

    job_text = str(row_dict.get("description_text") or "")
    if track == "industry" and not show_academic_docs:
        # Plain industry: cover letter only — skip JD regex scan on open.
        artifact_defaults = {
            "generate_cover_letter": True,
            "generate_application_letter": False,
            "generate_research_proposal": False,
        }
    elif track == "industry" and show_academic_docs:
        # Industry track but academic-looking role (or existing academic files on Modify).
        # Cover letter stays primary; academic docs use academic-track detection defaults.
        academic_defaults = default_artifact_options(job_text, track="academic")
        artifact_defaults = {
            "generate_cover_letter": True,
            "generate_application_letter": academic_defaults["generate_application_letter"],
            "generate_research_proposal": academic_defaults["generate_research_proposal"],
        }
    else:
        artifact_defaults = default_artifact_options(job_text, track=track)

    return {
        "artifact_defaults": artifact_defaults,
        "show_academic_docs": show_academic_docs,
        "existing_run_name": existing_run.name if existing_run is not None else None,
        "existing_flags": existing_flags,
    }


_PIPELINE_ACTIVE_PHASES = ("queued", "running", "complete", "error")

_PIPELINE_BUSY_PHASES = ("queued", "running")

_PIPELINE_RESULT_ARTIFACTS = (
    CV_MARKDOWN,
    "final_cv_no.md",
    "cover_letter.md",
    "cover_letter_no.md",
    "application_letter.md",
    "research_proposal.md",
    "application_artifacts.md",
)

def pipeline_phase_is_busy(phase: str | None) -> bool:
    """True while a worker is queued or running (not finished)."""
    return phase in _PIPELINE_BUSY_PHASES


def pipeline_job_display_title(title: str | None, employer: str | None = None) -> str:
    """Human-readable job label for status bar / queue captions."""
    label = str(title or "Job").strip() or "Job"
    emp = str(employer or "").strip()
    if emp:
        return f"{label} — {emp}"
    return label


def pipeline_queue_slots_used(*, has_active: bool, queue_len: int) -> int:
    """Count of in-flight pipelines (active + waiting)."""
    return (1 if has_active else 0) + max(0, int(queue_len))


def pipeline_queue_is_full(
    *,
    has_active: bool,
    queue_len: int,
    max_in_flight: int = PIPELINE_MAX_IN_FLIGHT,
) -> bool:
    """True when no more Apply/Modify jobs can be started or enqueued."""
    return pipeline_queue_slots_used(has_active=has_active, queue_len=queue_len) >= max_in_flight


def pipeline_queue_remaining(
    *,
    has_active: bool,
    queue_len: int,
    max_in_flight: int = PIPELINE_MAX_IN_FLIGHT,
) -> int:
    """How many more jobs can still be enqueued (or started if idle)."""
    return max(0, max_in_flight - pipeline_queue_slots_used(has_active=has_active, queue_len=queue_len))


def can_enqueue_pipeline(
    *,
    has_active: bool,
    active_job_key: str | None,
    queue: list[dict[str, Any]] | None,
    job_key: str,
    ingest_running: bool = False,
    max_in_flight: int = PIPELINE_MAX_IN_FLIGHT,
) -> tuple[bool, str]:
    """Return ``(ok, reason)`` for starting or enqueueing ``job_key``.

    When idle (``has_active`` False), returns ok so the job starts immediately.
    When busy, checks capacity and duplicate keys in the waiting queue.
    """
    key = str(job_key or "").strip()
    if not key:
        return False, "Missing job key."
    if ingest_running:
        return False, "Ingest is running — wait until it finishes."
    waiting = [item for item in (queue or []) if isinstance(item, dict)]
    if not has_active:
        return True, ""
    if str(active_job_key or "") == key:
        return False, "This role already has an active pipeline."
    if any(str(item.get("job_key") or "") == key for item in waiting):
        return False, "This role is already in the queue."
    if pipeline_queue_is_full(
        has_active=True,
        queue_len=len(waiting),
        max_in_flight=max_in_flight,
    ):
        max_waiting = max(0, max_in_flight - 1)
        return False, f"Queue full (max {max_waiting} waiting)."
    return True, ""


def build_pipeline_queue_item(
    job_key: str,
    row_dict: dict[str, Any],
    *,
    track: str,
    options: ApplyPipelineOptions | Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Build a Streamlit-safe waiting-queue entry for one Apply/Modify job."""
    opts = apply_pipeline_options_from_mapping(options)
    resolved_language = normalize_apply_language(opts.language)
    return {
        "job_key": str(job_key),
        "row_dict": dict(row_dict),
        "track": str(track or "industry"),
        "language": resolved_language,
        "options": apply_pipeline_options_to_mapping(opts),
        "title": str(row_dict.get("title") or ""),
        "employer": str(row_dict.get("employer_name") or ""),
    }


def enqueue_pipeline_item(
    queue: list[dict[str, Any]] | None,
    item: dict[str, Any],
    *,
    max_waiting: int = PIPELINE_MAX_WAITING,
) -> tuple[list[dict[str, Any]], bool, str]:
    """Append ``item`` to the waiting queue. Returns ``(queue, ok, reason)``."""
    waiting = [dict(entry) for entry in (queue or []) if isinstance(entry, dict)]
    job_key = str(item.get("job_key") or "").strip()
    if not job_key:
        return waiting, False, "Missing job key."
    if any(str(entry.get("job_key") or "") == job_key for entry in waiting):
        return waiting, False, "This role is already in the queue."
    if len(waiting) >= max_waiting:
        return waiting, False, f"Queue full (max {max_waiting} waiting)."
    waiting.append(dict(item))
    return waiting, True, ""


def dequeue_pipeline_item(
    queue: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Pop the next waiting job. Returns ``(remaining_queue, item_or_none)``."""
    waiting = [dict(entry) for entry in (queue or []) if isinstance(entry, dict)]
    if not waiting:
        return waiting, None
    item = waiting.pop(0)
    return waiting, item


def pipeline_queue_display_titles(
    queue: list[dict[str, Any]] | None,
    *,
    limit: int = 3,
) -> list[str]:
    """Short titles for status-bar captions."""
    titles: list[str] = []
    for item in (queue or []):
        if not isinstance(item, dict):
            continue
        titles.append(
            pipeline_job_display_title(item.get("title"), item.get("employer"))
        )
        if len(titles) >= limit:
            break
    return titles


def pipeline_active_for_job_key(
    job_key: str | None,
    *,
    pipeline_job_key: str | None,
    pipeline_phase: str | None,
) -> bool:
    """True when session holds an active pipeline for ``job_key`` (no Streamlit)."""
    if not job_key or not pipeline_job_key:
        return False
    return str(pipeline_job_key) == str(job_key) and pipeline_phase in _PIPELINE_ACTIVE_PHASES


def apply_dialog_ready(
    *,
    use_dialog: bool,
    apply_dialog_open: bool,
    apply_dialog_key: str | None,
    apply_dialog_context: dict[str, Any] | None,
    pipeline_job_key: str | None = None,
    pipeline_phase: str | None = None,
) -> bool:
    """True when Apply/Modify may open: valid row context or active pipeline for the key."""
    if not use_dialog or not apply_dialog_open:
        return False
    key = str(apply_dialog_key or "").strip()
    if not key:
        return False
    ctx = apply_dialog_context if isinstance(apply_dialog_context, dict) else {}
    if ctx.get("view_completion") and isinstance(ctx.get("completion"), dict):
        return True
    row_dict = ctx.get("row_dict")
    if isinstance(row_dict, dict) and row_dict:
        return True
    return pipeline_active_for_job_key(
        key,
        pipeline_job_key=pipeline_job_key,
        pipeline_phase=pipeline_phase,
    )


def reconcile_apply_dialog_flags(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return session-state patches that clear stale dialog flags (no Streamlit)."""
    if not snapshot.get("apply_dialog_open"):
        return {}
    if apply_dialog_ready(
        use_dialog=bool(snapshot.get("_use_dialog", True)),
        apply_dialog_open=True,
        apply_dialog_key=snapshot.get("apply_dialog_key"),
        apply_dialog_context=snapshot.get("apply_dialog_context"),
        pipeline_job_key=snapshot.get("pipeline_job_key"),
        pipeline_phase=snapshot.get("pipeline_phase"),
    ):
        return {}
    return {
        "apply_dialog_open": False,
        "apply_dialog_key": None,
        "apply_dialog_context": None,
    }


def yield_to_apply_modify_dialog(snapshot: dict[str, Any]) -> bool:
    """True when Apply/Modify dialog flags are ready (pure helper for tests + dashboard)."""
    return apply_dialog_ready(
        use_dialog=bool(snapshot.get("_use_dialog", True)),
        apply_dialog_open=bool(snapshot.get("apply_dialog_open")),
        apply_dialog_key=snapshot.get("apply_dialog_key"),
        apply_dialog_context=snapshot.get("apply_dialog_context"),
        pipeline_job_key=snapshot.get("pipeline_job_key"),
        pipeline_phase=snapshot.get("pipeline_phase"),
    )


_FORCE_SCROLL_RESTORE_KEY = "_dashboard_force_scroll_restore"

# Process-level explorer snapshot cache (FastAPI). Streamlit session keys below are unused
# leftovers kept so older tests/imports do not break.
_EXPLORER_JOBS_CACHE_KEY = "_explorer_jobs_cache_key"
_EXPLORER_JOBS_CACHE_DF = "_explorer_jobs_cache_df"
# Base explorer frame cache: keyed by filters + order_by + DB fingerprint, but NOT
# by the free-text query. Text search is applied on top of the cached base so each
# keystroke only pays for the (vectorized) substring match, not SQL/dedupe/enrich.
_EXPLORER_DF_CACHE: dict[tuple[Any, ...], tuple[pd.DataFrame, int]] = {}
_EXPLORER_DF_CACHE_MAX = 24
# Post-text-search results, keyed by (base key, normalized query): makes retyping or
# backspacing through the same query instant.
_EXPLORER_SEARCH_CACHE: dict[tuple[Any, ...], tuple[pd.DataFrame, int]] = {}
_EXPLORER_SEARCH_CACHE_MAX = 24
# Overview preview frames (relevant/newest/rogaland), keyed like the explorer base.
_OVERVIEW_CACHE: dict[tuple[Any, ...], tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
_OVERVIEW_CACHE_MAX = 16
# Overview metric block, keyed by track + urgency window + DB fingerprint.
_OVERVIEW_METRICS_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}
_OVERVIEW_METRICS_CACHE_MAX = 16
# Research-role counts, keyed by DB fingerprint.
_RESEARCH_COUNT_CACHE: dict[tuple[Any, ...], int] = {}
_RESEARCH_COUNT_CACHE_MAX = 8


def _cache_store(cache: dict[Any, Any], key: Any, value: Any, maxsize: int) -> None:
    """Insert into a dict-backed LRU-ish cache, evicting the oldest entry."""
    if key in cache:
        cache[key] = value
        return
    if len(cache) >= maxsize:
        cache.pop(next(iter(cache)), None)
    cache[key] = value


def clear_explorer_jobs_cache() -> None:
    """Drop all dashboard dataframes (call after ingest/score mutates the DB)."""
    _EXPLORER_DF_CACHE.clear()
    _EXPLORER_SEARCH_CACHE.clear()
    _OVERVIEW_CACHE.clear()
    _OVERVIEW_METRICS_CACHE.clear()
    _RESEARCH_COUNT_CACHE.clear()


def _explorer_db_fingerprint(path_s: str) -> tuple[float, int]:
    """Invalidate cache when the SQLite file changes."""
    try:
        st = Path(path_s).stat()
        return (st.st_mtime, st.st_size)
    except OSError:
        return (0.0, 0)

def run_agent_pipeline_streaming(
    run_dir: Path,
    *,
    language: str = "en",
    options: ApplyPipelineOptions | None = None,
    on_line: Any | None = None,
    python_exe: str | None = None,
) -> tuple[int, str, str]:
    """Run agent pipeline, optionally invoking ``on_line`` for each stdout line."""
    exe = resolve_project_python(python_exe)
    opts = apply_pipeline_options_from_mapping(options, language=language)
    resolved_language = normalize_apply_language(opts.language)
    cmd = [
        exe,
        "-u",
        "-m",
        "cv_generation.run_agent_pipeline",
        "--run-dir",
        str(run_dir),
        "--language",
        resolved_language,
    ]
    if opts.provider.strip():
        cmd.extend(["--provider", opts.provider.strip()])
    if opts.model.strip():
        cmd.extend(["--model", opts.model.strip()])
    if opts.overwrite_cv:
        cmd.append("--overwrite")
    if opts.generate_cover_letter:
        cmd.append("--generate-cover-letter")
    else:
        cmd.append("--no-generate-cover-letter")
    if opts.generate_application_letter:
        cmd.append("--generate-application-letter")
    else:
        cmd.append("--no-generate-application-letter")
    if opts.generate_research_proposal:
        cmd.append("--generate-research-proposal")
    else:
        cmd.append("--no-generate-research-proposal")
    if opts.overwrite_cover_letter:
        cmd.append("--overwrite-cover-letter")
    if opts.overwrite_application_letter:
        cmd.append("--overwrite-application-letter")
    if opts.overwrite_research_proposal:
        cmd.append("--overwrite-research-proposal")
    proc = subprocess.Popen(
        cmd,
        cwd=str(_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=_subprocess_env(),
    )
    lines: list[str] = []
    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            lines.append(line)
            if on_line is not None:
                on_line(line)
    finally:
        code = proc.wait()
    return code, "\n".join(lines).strip(), ""


def pipeline_stage_label(line: str) -> str | None:
    """Map agent pipeline log lines to user-visible stage labels."""
    total = PIPELINE_TOTAL_STEPS
    if "01_jd_parser" in line:
        return f"3/{total} Parse job description"
    if "02_keyword_ranker" in line:
        return f"4/{total} Rank keywords"
    if "03_track_selector" in line:
        return f"5/{total} Select track"
    if "04_bullet_tailor" in line:
        return f"6/{total} Tailor bullets"
    if "05_ats_checker" in line:
        return f"7/{total} ATS check"
    if any(token in line for token in ("06_assembler", "tailored_cv.md")):
        return f"8/{total} Assemble CV"
    if "final_cv.md" in line or "final_cv.pdf" in line:
        return f"8/{total} Assemble CV"
    if "07_cover_letter" in line or (
        "cover_letter" in line and ("Wrote:" in line or "Skip" in line)
    ):
        return f"9/{total} Cover letter"
    if "08_application_letter" in line or (
        "application_letter" in line and ("Wrote:" in line or "Skip" in line)
    ):
        return f"9/{total} Application letter"
    if "09_research_proposal" in line or (
        "research_proposal" in line and ("Wrote:" in line or "Skip" in line)
    ):
        return f"9/{total} Research proposal"
    if "final_cv_no.md" in line or "cover_letter_no.md" in line or "localize" in line.lower():
        return f"10/{total} Norwegian localization"
    return None


def pipeline_stage_number(label: str) -> int:
    """Extract the 1–11 step index from a pipeline stage label."""
    match = re.match(rf"^(\d+)/{PIPELINE_TOTAL_STEPS}", (label or "").strip())
    return int(match.group(1)) if match else 0


def pipeline_fallback_eligible(
    *,
    apply_dialog_open: bool,
    pipeline_job_key: str | None,
    pipeline_panel_rendered: bool,
    pipeline_phase: str | None,
) -> bool:
    """True when the page-level fallback should render the active pipeline."""
    if apply_dialog_open:
        return False
    if not pipeline_job_key or pipeline_panel_rendered:
        return False
    return pipeline_phase in ("queued", "running", "complete", "error")


def pipeline_notice_id(
    *,
    job_key: str | None,
    phase: str | None,
    run_name: str | None,
) -> str:
    return "|".join(
        [
            str(job_key or ""),
            str(phase or ""),
            str(run_name or ""),
        ]
    )


def pipeline_result_details(run_name: str | None, *, repo_root: Path | None = None) -> dict[str, Any]:
    """Resolve stable result metadata so completed runs can be reopened later."""
    details: dict[str, Any] = {
        "run_dir": None,
        "artifact_paths": [],
        "deanonymize_cmd": None,
    }
    if not run_name:
        return details
    run_dir = resolve_run_dir(run_name, repo_root=repo_root or _root)
    if run_dir is None:
        return details
    details["run_dir"] = str(run_dir)
    details["deanonymize_cmd"] = f"~/private/cv/cv apply {run_name}"
    artifact_paths = [
        str(run_dir / name)
        for name in _PIPELINE_RESULT_ARTIFACTS
        if (run_dir / name).is_file()
    ]
    details["artifact_paths"] = artifact_paths
    return details


def _build_pipeline_result(run_name: str | None, errs: list[str]) -> dict[str, Any]:
    payload = {
        "run_name": run_name,
        "errs": list(errs or []),
    }
    payload.update(pipeline_result_details(run_name))
    return payload


def refresh_finn_job_description(conn, row: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Fetch FINN detail HTML when the DB row has no description_text."""
    from job_search.finn_job_client import FinnJobSession
    from job_search.ingest_common import strip_html

    uuid = _safe_str(row.get("uuid"))
    if not uuid:
        return row, ["Missing FINN ad id."]
    try:
        detail = FinnJobSession(sleep_s=0.2).fetch_job_detail(uuid)
    except Exception as exc:  # noqa: BLE001 — surface fetch errors to the UI
        return row, [f"FINN detail fetch failed: {exc}"]

    desc_html = detail.get("description") or ""
    desc_text = strip_html(str(desc_html))[:20000] if desc_html else ""
    if not desc_text.strip():
        return row, ["FINN detail page had no description text."]

    updated = dict(row)
    updated["description_text"] = desc_text
    if detail.get("title"):
        updated["title"] = detail.get("title")
    if detail.get("employer_name"):
        updated["employer_name"] = detail.get("employer_name")
    if detail.get("municipal"):
        updated["municipal"] = detail.get("municipal")
    if detail.get("county"):
        updated["county"] = detail.get("county")

    raw_obj: dict[str, Any] = {}
    raw_existing = updated.get("raw_json")
    if isinstance(raw_existing, str) and raw_existing.strip():
        try:
            parsed = json.loads(raw_existing)
            if isinstance(parsed, dict):
                raw_obj = parsed
        except json.JSONDecodeError:
            raw_obj = {}
    elif isinstance(raw_existing, dict):
        raw_obj = dict(raw_existing)
    raw_obj["detail"] = detail.get("raw") or detail
    updated["raw_json"] = json.dumps(raw_obj, ensure_ascii=False)
    updated["fetched_at"] = utc_now_iso()
    upsert_job(conn, updated)
    conn.commit()
    return updated, []


def _pipeline_worker_entry(job_key: str) -> dict[str, Any] | None:
    lock, workers = _pipeline_worker_registry()
    with lock:
        return workers.get(job_key)


def _pipeline_worker_thread_alive(job_key: str) -> bool:
    name = f"apply-pipeline-{job_key}"
    return any(t.name == name and t.is_alive() for t in threading.enumerate())


def _start_pipeline_worker(
    job_key: str,
    *,
    db_path: Path,
    row_dict: dict[str, Any],
    track: str,
    options: ApplyPipelineOptions | None,
) -> None:
    """Launch apply work on a daemon thread so the HTTP server can keep serving."""
    store: dict[str, Any] = {
        "lock": threading.Lock(),
        "phase": "running",
        "stage": f"1/{PIPELINE_TOTAL_STEPS} Export job posting",
        "elapsed": 0.0,
        "log_lines": [],
        "result": None,
    }
    lock, workers = _pipeline_worker_registry()
    with lock:
        workers[job_key] = store

    def _worker() -> None:
        conn = None
        try:
            conn = connect(db_path)
            init_schema(conn)

            def on_stage(label: str, elapsed: float, state: str) -> None:
                del state
                with store["lock"]:
                    store["stage"] = label
                    store["elapsed"] = elapsed

            def on_log_line(line: str) -> None:
                text = (line or "").rstrip()
                if not text:
                    return
                with store["lock"]:
                    lines = store["log_lines"]
                    lines.append(text)
                    if len(lines) > PIPELINE_LOG_MAX_LINES:
                        store["log_lines"] = lines[-PIPELINE_LOG_MAX_LINES:]

            run_name, errs = execute_apply_pipeline(
                conn,
                row_dict,
                track=track,
                status=None,
                options=options,
                on_stage=on_stage,
                on_log_line=on_log_line,
                clear_streamlit_cache=False,
            )
            with store["lock"]:
                store["result"] = _build_pipeline_result(run_name, errs)
                store["phase"] = "error" if (errs and not run_name) else "complete"
        except Exception as exc:  # noqa: BLE001 — surface unexpected worker failures
            log.exception("apply pipeline worker failed job_key=%s", job_key)
            with store["lock"]:
                store["result"] = _build_pipeline_result(None, [str(exc)])
                store["phase"] = "error"
        finally:
            if conn is not None:
                conn.close()

    threading.Thread(
        target=_worker,
        name=f"apply-pipeline-{job_key}",
        daemon=True,
    ).start()


def run_agent_pipeline_subprocess(
    run_dir: Path,
    *,
    language: str = "en",
    python_exe: str | None = None,
) -> tuple[int, str, str]:
    exe = resolve_project_python(python_exe)
    proc = subprocess.run(
        [
            exe,
            "-u",
            "-m",
            "cv_generation.run_agent_pipeline",
            "--run-dir",
            str(run_dir),
            "--language",
            normalize_apply_language(language),
        ],
        cwd=str(_root),
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _log_dashboard_filter_state(
    *,
    track: str,
    academic_roles_only: bool,
    stage: str,
    count_before: int,
    count_after: int | None = None,
) -> None:
    if count_after is None:
        log.info(
            "filter track=%s academic_roles_only=%s stage=%s rows=%d",
            track,
            academic_roles_only,
            stage,
            count_before,
        )
    else:
        dropped = count_before - count_after
        log.info(
            "filter track=%s academic_roles_only=%s stage=%s rows_before=%d rows_after=%d dropped=%d",
            track,
            academic_roles_only,
            stage,
            count_before,
            count_after,
            dropped,
        )


def effective_academic_roles_only(*, track: str, academic_roles_only: bool) -> bool:
    """Academic CV track always applies the strict research-role display filter."""
    return track == "academic" or academic_roles_only


def count_research_roles_in_db(db_path_str: str) -> int:
    """Active jobs whose title matches postdoc/researcher/lecturer vocabulary."""
    cache_key = ("research_count", db_path_str, _explorer_db_fingerprint(db_path_str))
    cached = _RESEARCH_COUNT_CACHE.get(cache_key)
    if cached is not None:
        _mark_cache_exec("research_count_hit")
        return cached
    _mark_cache_exec("research_count_miss")
    conn = connect(Path(db_path_str))
    init_schema(conn)
    try:
        clauses = " OR ".join(
            f"instr(LOWER(COALESCE(title,'') || ' ' || COALESCE(jobtitle,'')), ?) > 0"
            for _ in ACADEMIC_ROLE_TITLE_TERMS
        )
        params = [t.casefold() for t in ACADEMIC_ROLE_TITLE_TERMS]
        row = conn.execute(
            f"""
            SELECT COUNT(*) AS n FROM job_postings
            WHERE (status IS NULL OR UPPER(status) = 'ACTIVE')
              AND ({clauses})
            """,
            params,
        ).fetchone()
        result = int(row[0]) if row else 0
        _cache_store(_RESEARCH_COUNT_CACHE, cache_key, result, _RESEARCH_COUNT_CACHE_MAX)
        return result
    finally:
        conn.close()


@dataclass
class IngestCycleOptions:
    """User-selected ingest cycle options from the dashboard sidebar."""

    skip_nav: bool = False
    skip_finn: bool = False
    skip_jobbnorge: bool = False
    academic_queries_only: bool = False
    db_path: str | None = None


def build_ingest_cycle_command(
    *,
    skip_nav: bool = False,
    skip_finn: bool = False,
    skip_jobbnorge: bool = False,
    academic_queries_only: bool = False,
    db_path: str | None = None,
    python_exe: str | None = None,
) -> list[str]:
    """Build ``scripts/run_job_search_cycle.py`` argv for dashboard ingest."""
    exe = resolve_project_python(python_exe)
    cmd = [exe, str(_root / "scripts" / "run_job_search_cycle.py")]
    if db_path:
        cmd.extend(["--db", db_path])
    if skip_nav and skip_finn and skip_jobbnorge:
        cmd.append("--skip-ingest")
    else:
        if skip_nav:
            cmd.append("--skip-nav-ingest")
        if skip_finn:
            cmd.append("--skip-finn-ingest")
        if skip_jobbnorge:
            cmd.append("--skip-jobbnorge-ingest")
    if academic_queries_only:
        # Values must use --finn-ingest-arg=ARG: bare "--search-track" is parsed as a flag, not a value.
        cmd.extend(["--finn-ingest-arg=--search-track", "--finn-ingest-arg=academic"])
        cmd.extend(["--jobbnorge-ingest-arg=--search-track", "--jobbnorge-ingest-arg=academic"])
    return cmd


def parse_ingest_cycle_output(stdout: str) -> dict[str, Any]:
    """Parse step labels and JSON summaries from ``run_job_search_cycle`` stdout."""
    steps: dict[str, dict[str, Any]] = {}
    current_step: str | None = None
    json_buf: list[str] = []
    depth = 0

    def flush_json() -> None:
        nonlocal json_buf, depth, current_step
        if depth != 0 or not json_buf:
            return
        block = "\n".join(json_buf)
        json_buf = []
        depth = 0
        try:
            obj = json.loads(block)
        except json.JSONDecodeError:
            return
        key = current_step or f"step_{len(steps) + 1}"
        steps[key] = obj

    for line in stdout.splitlines():
        match = re.match(r"\[job-search\] (\S+):", line)
        if match:
            flush_json()
            current_step = match.group(1)
            continue
        stripped = line.strip()
        if stripped.startswith("{") or json_buf:
            json_buf.append(line)
            depth += line.count("{") - line.count("}")
            if depth == 0:
                flush_json()
    flush_json()
    return {"steps": steps}


def run_ingest_cycle_subprocess(
    cmd: list[str],
    *,
    on_line: Any | None = None,
    python_exe: str | None = None,
) -> tuple[int, str, str]:
    """Run ingest cycle script, optionally invoking ``on_line`` for each stdout line."""
    del python_exe  # cmd already includes interpreter
    proc = subprocess.Popen(
        cmd,
        cwd=str(_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=_subprocess_env(),
    )
    lines: list[str] = []
    assert proc.stdout is not None
    try:
        for raw in proc.stdout:
            line = raw.rstrip("\n")
            lines.append(line)
            if on_line is not None:
                on_line(line)
    finally:
        code = proc.wait()
    return code, "\n".join(lines).strip(), ""


def ingest_active_source_counts(db_path: Path) -> dict[str, int]:
    """Active job counts per ingest source plus academic-track scored rows."""
    conn = connect(db_path)
    init_schema(conn)
    try:
        source_rows = conn.execute(
            """
            SELECT source, COUNT(*) AS n
            FROM job_postings
            WHERE status IS NULL OR UPPER(status) = 'ACTIVE'
            GROUP BY source
            """,
        ).fetchall()
        academic_n = int(
            conn.execute(
                """
                SELECT COUNT(DISTINCT s.uuid || s.source) AS n
                FROM job_scores s
                JOIN job_postings j ON j.uuid = s.uuid AND j.source = j.source
                WHERE s.track = 'academic'
                  AND (j.status IS NULL OR UPPER(j.status) = 'ACTIVE')
                """,
            ).fetchone()["n"]
        )
        counts = {str(row["source"]): int(row["n"]) for row in source_rows}
        counts["academic_track"] = academic_n
        return counts
    finally:
        conn.close()


def _ingest_failure_headline(result: dict[str, Any]) -> str:
    """One-line cause for the ingest error banner (stderr is usually empty; see stdout)."""
    exit_code = result.get("exit_code", 1)
    blob = "\n".join(
        part
        for part in (
            str(result.get("stderr") or "").strip(),
            str(result.get("stdout_tail") or "").strip(),
        )
        if part
    )
    if not blob:
        return f"Ingest failed (exit {exit_code})."

    exception_lines: list[str] = []
    for line in blob.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("File ") or stripped.startswith("raise ") or stripped.startswith("Traceback"):
            continue
        if re.match(r"^[A-Za-z_][\w.]*(?:Error|Exception|Exit):", stripped) or re.match(
            r"^NameError:",
            stripped,
        ):
            exception_lines.append(stripped)

    # Prefer the root cause (first exception) over outer CalledProcessError wrappers.
    for stripped in exception_lines:
        if stripped.startswith("subprocess.CalledProcessError"):
            continue
        return f"Ingest failed (exit {exit_code}): {stripped}"
    if exception_lines:
        return f"Ingest failed (exit {exit_code}): {exception_lines[0]}"

    last = next((ln.strip() for ln in reversed(blob.splitlines()) if ln.strip()), "")
    return f"Ingest failed (exit {exit_code}): {last}" if last else f"Ingest failed (exit {exit_code})."


def fetch_job_posting(conn, uuid: str, source: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM job_postings WHERE uuid = ? AND source = ?",
        (uuid.strip(), source.strip()),
    ).fetchone()
    return dict(row) if row else None


def get_db_path() -> Path:
    raw = os.environ.get("JOBS_DB", "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return DEFAULT_DB_PATH


def best_job_url(row: dict[str, Any] | Any) -> str:
    """Return the public ad/listing URL, not the login-gated apply endpoint.

    Jobbnorge and some NAV rows store an ATS ``application_url`` (often a login
    page); the human-readable ad is in ``link``. Prefer ``link`` and fall back to
    ``application_url`` for older rows that only have the latter.
    """
    for col in ("link", "application_url"):
        val = row.get(col) if hasattr(row, "get") else getattr(row, col, None)
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            text = str(val).strip()
            if text:
                return text
    return ""


_TEXT_SEARCH_COLUMNS = ("title", "jobtitle", "description_text", "employer_name", "uuid")


def _text_search_haystack(df: pd.DataFrame) -> pd.Series:
    """Casefolded whitespace-joined search text for title/employer/description/uuid."""
    parts: list[pd.Series] = []
    for col in _TEXT_SEARCH_COLUMNS:
        if col in df.columns:
            series = df[col]
            parts.append(series.where(series.notna(), "").astype(str))
    if not parts:
        return pd.Series("", index=df.index, dtype="object")
    joined = parts[0]
    for extra in parts[1:]:
        joined = joined.str.cat(extra, sep=" ")
    return joined.str.casefold()


def apply_text_search_filter(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Free-text search over title, employer, and description (vectorized post-filter)."""
    text = (query or "").strip()
    if not text or df.empty:
        return df
    tokens = [tok.casefold() for tok in re.split(r"\s+", text) if tok.strip()]
    if not tokens:
        return df
    hay = _text_search_haystack(df)
    mask = pd.Series(True, index=df.index)
    for token in tokens:
        mask &= hay.str.contains(token, regex=False, na=False)
    return df.loc[mask].reset_index(drop=True)


def build_explorer_filter_chips(
    *,
    track: str,
    source_filter: str,
    apply_academic_filter: bool,
    use_tech_allowlist: bool,
    include_tuple: tuple[str, ...],
    exclude_tuple: tuple[str, ...],
    hide_phd_student: bool,
    dedupe_cross_source: bool,
    min_score: float,
    rogaland_only: bool,
    hide_applied: bool,
    hide_expired: bool,
    text_query: str,
    order_by: str = "score",
) -> list[str]:
    """Human-readable labels for active explorer filters."""
    chips: list[str] = [f"Track: {track}"]
    if source_filter and source_filter != "all":
        chips.append(f"Source: {source_label_short(source_filter)}")
    if apply_academic_filter:
        suffix = " (track default)" if track == "academic" else ""
        chips.append(f"Academic roles{suffix}")
    elif use_tech_allowlist:
        if include_tuple:
            chips.append(f"ICT allowlist ({len(include_tuple)} terms)")
        else:
            chips.append("ICT allowlist (no terms)")
    else:
        chips.append("ICT allowlist off")
    if exclude_tuple:
        chips.append(f"Blocklist ({len(exclude_tuple)} terms)")
    if hide_phd_student:
        chips.append("Hide PhD student")
    if dedupe_cross_source:
        chips.append("Dedup cross-source")
    if min_score > 0:
        chips.append(f"Score ≥ {min_score:.0f}")
    if rogaland_only:
        chips.append("Preferred locations")
    if order_by and order_by != "score":
        chips.append(f"Sort: {order_by}")
    if hide_applied:
        chips.append("Hide applications")
    if hide_expired:
        chips.append("Hide expired")
    q = (text_query or "").strip()
    if q:
        preview = q if len(q) <= 36 else f"{q[:36]}…"
        chips.append(f'Search: "{preview}"')
    return chips


def _explorer_jobs_cache_fingerprint(
    *,
    path_s: str,
    track: str,
    min_score: float,
    rogaland_only: bool,
    hide_applied: bool,
    hide_expired: bool,
    query_include_terms: tuple[str, ...],
    exclude_tuple: tuple[str, ...],
    source_filter: str,
    hide_phd_student: bool,
    apply_academic_filter: bool,
    dedupe_cross_source: bool,
    use_tech_allowlist: bool,
    include_tuple: tuple[str, ...],
    urgency_days: int,
    text_query: str,
    order_by: str = "score",
) -> tuple[Any, ...]:
    """Hashable key for the in-process explorer dataframe snapshot."""
    return (
        path_s,
        _explorer_db_fingerprint(path_s),
        track,
        float(min_score),
        bool(rogaland_only),
        bool(hide_applied),
        bool(hide_expired),
        query_include_terms,
        exclude_tuple,
        source_filter,
        bool(hide_phd_student),
        bool(apply_academic_filter),
        bool(dedupe_cross_source),
        bool(use_tech_allowlist),
        include_tuple,
        int(urgency_days),
        (text_query or "").strip(),
        order_by if order_by in {"score", "published", "location"} else "score",
    )


def filter_expired_jobs_df(df: pd.DataFrame, hide_expired: bool) -> pd.DataFrame:
    """Drop rows whose application deadline is past (see ``is_expired``)."""
    if not hide_expired or df.empty:
        return df
    keep_mask = [not is_expired(row_expires(row)) for _, row in df.iterrows()]
    return df.loc[keep_mask].reset_index(drop=True)


def apply_dashboard_filters(
    df: pd.DataFrame,
    *,
    use_tech_allowlist: bool,
    include_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...],
    hide_phd_student: bool,
    min_score: float = 0.0,
    rogaland_only: bool = False,
    require_profile_match: bool = False,
    academic_roles_only: bool = False,
) -> pd.DataFrame:
    """Post-filter overview rows with the same rules as ingest / explorer."""
    if df.empty:
        return df
    out = df.copy()
    if min_score > 0 and "score_total" in out.columns:
        out = out[out["score_total"].fillna(0) >= min_score]
    keep_mask: list[bool] = []
    for _, row in out.iterrows():
        if require_profile_match and not has_profile_relevance(row):
            keep_mask.append(False)
            continue
        hay = haystack_for_filter(
            row.get("title"),
            row.get("jobtitle"),
            row.get("description_text"),
            row.get("employer_name"),
        )
        if use_tech_allowlist and include_terms and not matches_any_include_term(hay, include_terms):
            keep_mask.append(False)
            continue
        if exclude_terms and matches_exclude_terms(hay, exclude_terms):
            keep_mask.append(False)
            continue
        if hide_phd_student and matches_phd_student_opening(
            hay,
            haystack_for_filter(row.get("title"), row.get("jobtitle"), None, None),
        ):
            keep_mask.append(False)
            continue
        if academic_roles_only and not matches_academic_role_display(
            row.get("title"),
            row.get("jobtitle"),
            row.get("description_text"),
            row.get("employer_name"),
        ):
            keep_mask.append(False)
            continue
        if rogaland_only:
            in_r = bool(row.get("in_rogaland")) if not pd.isna(row.get("in_rogaland")) else False
            loc_ok = bool(row.get("location_matched")) if not pd.isna(row.get("location_matched")) else False
            if not (in_r or loc_ok):
                keep_mask.append(False)
                continue
        keep_mask.append(True)
    return out.loc[keep_mask].reset_index(drop=True)


def filter_phd_student_df(df: pd.DataFrame, hide: bool) -> pd.DataFrame:
    if not hide or df.empty:
        return df
    keep_mask: list[bool] = []
    for _, row in df.iterrows():
        hay = haystack_for_filter(
            row.get("title"),
            row.get("jobtitle"),
            row.get("description_text"),
            row.get("employer_name"),
        )
        keep_mask.append(
            not matches_phd_student_opening(
                hay,
                haystack_for_filter(row.get("title"), row.get("jobtitle"), None, None),
            )
        )
    return df.loc[keep_mask].reset_index(drop=True)


def enrich_jobs_df(df: pd.DataFrame, *, within_days: int = 7) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["deadline"] = out.apply(lambda r: deadline_display(row_expires(r)), axis=1)
    out["urgency"] = out.apply(lambda r: apply_soon_badge(row_expires(r), within_days=within_days), axis=1)
    out["apply_soon"] = out["urgency"].astype(str).str.startswith("Apply soon")
    return out


# FINN search-result cards store only a short teaser (no real description). Those
# thin rows are always hidden from the explorer/overview: they are kept in the DB
# so detail backfill can later fill them in, but they never appear as jobs.
MIN_FINN_DESCRIPTION_CHARS = 280
# Reusable predicate for "an ACTIVE posting the dashboard would show" (alias j).
_VISIBLE_ACTIVE_SQL = (
    "(j.status IS NULL OR UPPER(j.status) = 'ACTIVE') AND NOT ("
    "j.source = 'finn_no' AND "
    f"LENGTH(TRIM(COALESCE(j.description_text, ''))) < {MIN_FINN_DESCRIPTION_CHARS})"
)


def _jobs_query_fragments(
    *,
    track: str,
    min_score: float,
    preferred_location_only: bool,
    rogaland_section: bool,
    hide_applied: bool,
    include_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...],
    source_filter: str,
    hide_phd_student: bool,
    require_profile_match: bool,
    academic_roles_only: bool,
    order_by: str,
    limit: int | None,
) -> tuple[str, tuple[Any, ...]]:
    location_clause = "AND j.location_matched = 1" if preferred_location_only else ""
    if rogaland_section:
        location_clause = "AND (j.in_rogaland = 1 OR j.location_matched = 1)"
    profile_sql = ""
    profile_params: list[str] = []
    if require_profile_match:
        profile_sql, profile_params = sql_require_profile_relevance()
    source_clause = ""
    source_params: tuple[str, ...] = ()
    if source_filter and source_filter != "all":
        source_clause = "AND j.source = ?"
        source_params = (source_filter,)
    hide_clause = ""
    if hide_applied:
        hide_statuses = ", ".join(f"'{s}'" for s in sorted(HIDE_APPLIED_STATUSES))
        # Pinned roles stay visible even when their status would otherwise be hidden.
        hide_clause = f"""
        AND (
            COALESCE(ap.pinned, 0) = 1
            OR ap.status IS NULL
            OR ap.status NOT IN ({hide_statuses})
        )
        """
    include_sql, include_params = sql_require_any_include(include_terms)
    academic_sql, academic_params = (
        sql_require_academic_role_display() if academic_roles_only else ("", [])
    )
    noise_sql, noise_params = sql_exclude_fragments(exclude_terms)
    if hide_phd_student:
        phd_sql, phd_param_list = sql_phd_student_exclude()
        phd_params = tuple(phd_param_list)
    else:
        phd_sql = ""
        phd_params = ()

    if order_by == "published":
        order_sql = (
            "COALESCE(ap.pinned, 0) DESC, j.published DESC, s.score_total DESC, j.title"
        )
    elif order_by == "location":
        order_sql = (
            "COALESCE(ap.pinned, 0) DESC, "
            "COALESCE(NULLIF(j.location_label, ''), NULLIF(j.municipal, ''), "
            "NULLIF(j.county, ''), 'ZZZ') COLLATE NOCASE ASC, "
            "s.score_total DESC, j.title"
        )
    else:
        order_sql = (
            "COALESCE(ap.pinned, 0) DESC, s.score_total DESC, s.score_base DESC, j.title"
        )

    limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""

    q = f"""
    SELECT
    {_JOB_SELECT_COLUMNS}
    FROM job_postings j
    INNER JOIN job_scores s ON s.uuid = j.uuid AND s.source = j.source
    LEFT JOIN applications ap
        ON ap.uuid = j.uuid AND ap.source = j.source AND ap.track = s.track
    WHERE s.track = ?
      AND {_VISIBLE_ACTIVE_SQL}
      AND s.score_total >= ?
      {location_clause}
      {source_clause}
      {hide_clause}
      {include_sql}
      {academic_sql}
      {noise_sql}
      {phd_sql}
      {profile_sql}
    ORDER BY {order_sql}
    {limit_sql}
    """
    params: tuple[Any, ...] = (
        track,
        min_score,
        *source_params,
        *include_params,
        *academic_params,
        *noise_params,
        *phd_params,
        *profile_params,
    )
    return q, params


def dedupe_jobs_df(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse NAV + FINN rows with the same employer and title."""
    return _dedupe_jobs_df(df)


def load_jobs_df(
    db_path_str: str,
    track: str,
    min_score: float,
    preferred_location_only: bool,
    rogaland_section: bool,
    hide_applied: bool,
    include_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...],
    source_filter: str,
    hide_phd_student: bool,
    order_by: str = "score",
    limit: int | None = None,
    require_profile_match: bool = False,
    academic_roles_only: bool = False,
) -> pd.DataFrame:
    _mark_cache_exec("load_jobs_df")
    q, params = _jobs_query_fragments(
        track=track,
        min_score=min_score,
        preferred_location_only=preferred_location_only,
        rogaland_section=rogaland_section,
        hide_applied=hide_applied,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        source_filter=source_filter,
        hide_phd_student=hide_phd_student,
        require_profile_match=require_profile_match,
        academic_roles_only=academic_roles_only,
        order_by=order_by,
        limit=limit,
    )
    conn = connect(Path(db_path_str))
    init_schema(conn)
    try:
        df = pd.read_sql_query(q, conn, params=params)
        return filter_phd_student_df(df, hide_phd_student)
    finally:
        conn.close()


def load_overview_metrics(
    db_path_str: str,
    track: str,
    within_days: int,
) -> dict[str, Any]:
    # Counts are track-independent (track_split covers all tracks), so key on
    # DB fingerprint + urgency window to maximise cache hits.
    metrics_key = ("overview_metrics", db_path_str, _explorer_db_fingerprint(db_path_str), int(within_days))
    cached_metrics = _OVERVIEW_METRICS_CACHE.get(metrics_key)
    if cached_metrics is not None:
        _mark_cache_exec("overview_metrics_hit")
        return cached_metrics
    _mark_cache_exec("overview_metrics_miss")
    conn = connect(Path(db_path_str))
    init_schema(conn)
    try:
        source_active = pd.read_sql(
            f"""
            SELECT j.source AS source, COUNT(*) AS n
            FROM job_postings j
            WHERE {_VISIBLE_ACTIVE_SQL}
            GROUP BY j.source
            ORDER BY j.source
            """,
            conn,
        )
        n_scored = int(
            pd.read_sql(
                f"""
                SELECT COUNT(DISTINCT s.uuid || s.source || s.track) AS n
                FROM job_scores s
                JOIN job_postings j ON j.uuid = s.uuid AND j.source = s.source
                WHERE {_VISIBLE_ACTIVE_SQL}
                """,
                conn,
            )["n"].iloc[0]
        )
        n_active = int(
            pd.read_sql(
                f"""
                SELECT COUNT(*) AS n FROM job_postings j
                WHERE {_VISIBLE_ACTIVE_SQL}
                """,
                conn,
            )["n"].iloc[0]
        )
        n_apps = int(pd.read_sql("SELECT COUNT(*) AS n FROM applications", conn)["n"].iloc[0])
        track_split = pd.read_sql(
            f"""
            SELECT s.track, COUNT(DISTINCT s.uuid || s.source) AS n
            FROM job_scores s
            JOIN job_postings j ON j.uuid = s.uuid AND j.source = s.source
            WHERE {_VISIBLE_ACTIVE_SQL}
            GROUP BY s.track
            """,
            conn,
        )
        active_jobs = pd.read_sql(
            f"""
            SELECT j.uuid, j.source, j.expires FROM job_postings j
            WHERE {_VISIBLE_ACTIVE_SQL}
            """,
            conn,
        )
        apply_soon_count = sum(
            1 for _, row in active_jobs.iterrows() if is_apply_soon(row.get("expires"), within_days=within_days)
        )
        result = {
            "source_active": source_active,
            "n_scored": n_scored,
            "n_active": n_active,
            "n_apps": n_apps,
            "apply_soon_count": apply_soon_count,
            "track_split": track_split,
        }
        _cache_store(_OVERVIEW_METRICS_CACHE, metrics_key, result, _OVERVIEW_METRICS_CACHE_MAX)
        return result
    finally:
        conn.close()


def load_overview_jobs_bundle(
    db_path_str: str,
    track: str,
    include_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...],
    source_filter: str,
    hide_phd_student: bool,
    academic_roles_only: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Two capped overview lists in one cache entry (one SQLite connection)."""
    _mark_cache_exec("load_overview_jobs_bundle")
    common = dict(
        track=track,
        min_score=0.0,
        preferred_location_only=False,
        hide_applied=False,
        include_terms=include_terms,
        exclude_terms=exclude_terms,
        source_filter=source_filter,
        hide_phd_student=hide_phd_student,
        academic_roles_only=academic_roles_only,
    )
    conn = connect(Path(db_path_str))
    init_schema(conn)
    try:
        # Academic track has many low-score university ads (boost-only, no English CV hits).
        relevant_cap = 300 if track == "academic" else 30
        frames: list[pd.DataFrame] = []
        for order_by, limit, require_profile in (
            ("score", relevant_cap, True),
            ("published", 30, False),
        ):
            q, params = _jobs_query_fragments(
                rogaland_section=False,
                order_by=order_by,
                limit=limit,
                require_profile_match=require_profile,
                **common,
            )
            df = pd.read_sql_query(q, conn, params=params)
            frames.append(filter_phd_student_df(df, hide_phd_student))
        return frames[0], frames[1]
    finally:
        conn.close()


def load_overview_frames(
    *,
    path_s: str,
    track: str,
    source_filter: str,
    hide_phd_student: bool,
    dedupe_cross_source: bool,
    use_tech_allowlist: bool,
    include_tuple: tuple[str, ...],
    exclude_tuple: tuple[str, ...],
    apply_academic_filter: bool,
    query_include_terms: tuple[str, ...],
    urgency_days: int,
    min_score: float,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fully filtered + enriched overview preview frames (relevant, newest).

    Cached by every input (DB mtime included): repeated loads, unrelated filter
    changes, and the per-keystroke explorer refresh no longer rebuild these lists.
    """
    cache_key = (
        "overview_frames",
        path_s,
        _explorer_db_fingerprint(path_s),
        track,
        source_filter,
        bool(hide_phd_student),
        bool(dedupe_cross_source),
        bool(use_tech_allowlist),
        include_tuple,
        exclude_tuple,
        bool(apply_academic_filter),
        query_include_terms,
        int(urgency_days),
        float(min_score),
    )
    cached = _OVERVIEW_CACHE.get(cache_key)
    if cached is not None:
        _mark_cache_exec("overview_frames_hit")
        return cached
    _mark_cache_exec("overview_frames_miss")

    relevant_raw, newest_raw = load_overview_jobs_bundle(
        path_s,
        track,
        query_include_terms,
        exclude_tuple,
        source_filter,
        hide_phd_student,
        apply_academic_filter,
    )
    if dedupe_cross_source:
        relevant_raw = dedupe_jobs_df(relevant_raw)
        newest_raw = dedupe_jobs_df(newest_raw)
    filter_kwargs = dict(
        use_tech_allowlist=use_tech_allowlist and not apply_academic_filter,
        include_terms=include_tuple,
        exclude_terms=exclude_tuple,
        hide_phd_student=hide_phd_student,
        academic_roles_only=apply_academic_filter,
    )
    relevant = apply_dashboard_filters(
        relevant_raw,
        min_score=float(min_score),
        require_profile_match=True,
        **filter_kwargs,
    )
    newest = apply_dashboard_filters(newest_raw, require_profile_match=False, **filter_kwargs)
    relevant = enrich_jobs_df(relevant, within_days=urgency_days)
    newest = enrich_jobs_df(newest, within_days=urgency_days)
    value = (relevant, newest)
    _cache_store(_OVERVIEW_CACHE, cache_key, value, _OVERVIEW_CACHE_MAX)
    return value


_APPLIED_ROLES_SQL = """
SELECT
    a.uuid,
    a.source,
    a.track,
    a.status,
    a.applied_at,
    a.follow_up_at,
    a.notes,
    a.cover_letter_path,
    a.updated_at,
    COALESCE(a.pinned, 0) AS pinned,
    j.title,
    j.employer_name,
    j.link,
    j.application_url,
    j.description_text,
    j.in_rogaland,
    j.location_matched,
    j.location_label,
    s.score_total,
    s.score_base,
    s.boost_rogaland,
    s.boost_tek
FROM applications a
JOIN job_postings j ON j.uuid = a.uuid AND j.source = a.source
LEFT JOIN job_scores s
    ON s.uuid = a.uuid AND s.source = a.source AND s.track = a.track
WHERE a.track = ?
ORDER BY COALESCE(a.pinned, 0) DESC, COALESCE(a.applied_at, a.updated_at) DESC
"""

def extract_run_ids_from_notes(notes: str | None) -> list[str]:
    """Return CV run folder basenames from application notes (``CV run: …`` lines)."""
    if not notes:
        return []
    run_ids: list[str] = []
    for line in str(notes).splitlines():
        match = _CV_RUN_NOTES_RE.search(line)
        if match:
            run_ids.append(Path(match.group(1)).name)
    return run_ids


def pipeline_metrics_for_run_id(run_id: str) -> dict[str, Any] | None:
    """Load ``pipeline_metrics.json`` for a run basename, if present."""
    run_dir = resolve_run_dir(run_id, repo_root=_root)
    if run_dir is None:
        return None
    return load_pipeline_metrics(run_dir)


def pipeline_metrics_summary_for_notes(notes: str | None) -> str | None:
    """One-line impact summary from the latest CV run referenced in notes."""
    run_ids = extract_run_ids_from_notes(notes)
    if not run_ids:
        return None
    return format_pipeline_metrics_summary(pipeline_metrics_for_run_id(run_ids[-1]))


def status_badge_markdown(status: str | None) -> str:
    label = (status or "unknown").strip() or "unknown"
    color = _STATUS_BADGE_COLOR.get(label, "gray")
    return f":{color}[{label}]"


def row_dict_for_apply_from_app(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    """Build a job row dict suitable for ``execute_apply_pipeline`` from an application row."""
    data = row.to_dict() if isinstance(row, pd.Series) else dict(row)
    return {
        "uuid": data.get("uuid"),
        "source": data.get("source"),
        "title": data.get("title"),
        "employer_name": data.get("employer_name"),
        "description_text": data.get("description_text"),
        "link": data.get("link"),
        "application_url": data.get("application_url"),
        "app_notes": data.get("notes"),
    }


def load_applied_roles_df(path_str: str, track: str) -> pd.DataFrame:
    conn = connect(Path(path_str))
    init_schema(conn)
    try:
        return pd.read_sql_query(_APPLIED_ROLES_SQL, conn, params=(track,))
    finally:
        conn.close()


def load_applications_df(path_str: str) -> pd.DataFrame:
    """All applications across tracks (raw table)."""
    conn = connect(Path(path_str))
    init_schema(conn)
    try:
        return pd.read_sql_query(
            """
            SELECT
                a.uuid,
                a.source,
                a.track,
                a.status,
                a.applied_at,
                a.follow_up_at,
                a.notes,
                a.cover_letter_path,
                a.updated_at,
                j.title,
                j.employer_name,
                j.link,
                j.in_rogaland,
                j.location_matched,
                j.location_label,
                s.score_total
            FROM applications a
            JOIN job_postings j ON j.uuid = a.uuid AND j.source = a.source
            LEFT JOIN job_scores s
                ON s.uuid = a.uuid AND s.source = a.source AND s.track = a.track
            ORDER BY COALESCE(a.applied_at, a.updated_at) DESC
            """,
            conn,
        )
    finally:
        conn.close()


def execute_apply_pipeline(
    conn,
    row: dict[str, Any],
    *,
    track: str,
    status: Any | None = None,
    options: ApplyPipelineOptions | None = None,
    on_stage: Any | None = None,
    on_log_line: Any | None = None,
    clear_streamlit_cache: bool = True,
) -> tuple[str | None, list[str]]:
    """Export job, run tailoring + agent pipeline, log drafted application."""
    errors: list[str] = []
    started = time.monotonic()
    opts = apply_pipeline_options_from_mapping(options)
    total = PIPELINE_TOTAL_STEPS
    log.info(
        "apply pipeline start uuid=%s source=%s track=%s modify=%s language=%s",
        row.get("uuid"),
        row.get("source"),
        track,
        opts.modify_mode,
        opts.language,
    )

    def _emit_log(line: str) -> None:
        if on_log_line is not None:
            on_log_line(line)

    last_logged_stage: str | None = None

    def _update(label: str, *, state: str = "running") -> None:
        nonlocal last_logged_stage
        elapsed = time.monotonic() - started
        if status is not None:
            status.update(label=f"{label} ({elapsed:.0f}s)", state=state)
        if on_stage is not None:
            on_stage(label, elapsed, state)
        if label != last_logged_stage:
            last_logged_stage = label
            _emit_log(f"→ {label}")

    full = fetch_job_posting(conn, str(row["uuid"]), str(row["source"]))
    if not full:
        return None, ["Job not found in database."]

    if not _safe_str(full.get("description_text")):
        if str(full.get("source") or "") == "finn_no":
            _emit_log("Job description missing in DB; fetching FINN detail…")
            full, fetch_errs = refresh_finn_job_description(conn, full)
            if fetch_errs:
                errors.extend(fetch_errs)
                _update("Missing job description", state="error")
                return None, errors
        if not _safe_str(full.get("description_text")):
            msg = (
                "No job description stored for this posting. "
                "Re-run ingest with detail fetches, or open the job URL and retry after the "
                "description is available."
            )
            _emit_log(msg)
            _update("Missing job description", state="error")
            return None, [msg]

    _update(f"1/{total} Export job posting")
    try:
        job_path = export_job_to_cv_file(full)
    except OSError as exc:
        return None, [f"Export failed: {exc}"]

    apply_language = normalize_apply_language(opts.language)
    existing_run_dir = resolve_modify_run_dir(
        row.get("app_notes"),
        run_id=opts.existing_run_id,
    )
    use_existing_run = opts.modify_mode and existing_run_dir is not None

    _update(f"2/{total} Prepare CV run")
    code, stdout, stderr = run_cv_tailoring_subprocess(
        job_path,
        company=str(full.get("employer_name") or ""),
        role=str(full.get("title") or ""),
        apply_prompts=opts.apply_prompts,
        language=apply_language,
        run_dir=existing_run_dir if use_existing_run else None,
        force=use_existing_run,
    )
    if code != 0:
        errors.append(f"`run_cv_tailoring` failed (exit {code}).")
        if stderr:
            errors.append(stderr)
            _emit_log(stderr)
        if stdout:
            errors.append(stdout)
            _emit_log(stdout)
        log.error(
            "apply pipeline tailoring failed uuid=%s exit=%d stderr=%s",
            full.get("uuid"),
            code,
            (stderr or "")[:500],
        )
        _update(f"2/{total} Prepare CV run failed", state="error")
        return None, errors

    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    run_dir_text = lines[0] if lines else ""
    if not run_dir_text:
        errors.append("Tailoring did not return a run directory path.")
        return None, errors

    run_dir = Path(run_dir_text)
    _emit_log(f"Run directory: {run_dir}")
    _update(f"3/{total} Parse job description")

    def _on_pipeline_line(line: str) -> None:
        _emit_log(line)
        stage = pipeline_stage_label(line)
        if stage:
            _update(stage)
        elif apply_language == "no" and "final_cv_no.md" in line:
            _update(f"10/{total} Norwegian localization")

    pipe_code, pipe_out, pipe_err = run_agent_pipeline_streaming(
        run_dir,
        language=apply_language,
        options=opts,
        on_line=_on_pipeline_line,
    )
    if pipe_code != 0:
        errors.append(f"`run_agent_pipeline` failed (exit {pipe_code}).")
        agent_err = next(
            (ln for ln in reversed((pipe_out or "").splitlines()) if ln.startswith("Agent error")),
            "",
        )
        if agent_err:
            errors.append(agent_err)
        elif pipe_err:
            errors.append(pipe_err.strip()[:500])
            _emit_log(pipe_err)
        if pipe_out:
            _emit_log(pipe_out)
        log.error(
            "apply pipeline agent failed uuid=%s run=%s exit=%d",
            full.get("uuid"),
            run_dir.name,
            pipe_code,
        )
        _update("Agent pipeline failed", state="error")
        return run_dir.name, errors

    cover_letter_path: str | None = None
    cover_md = run_dir / "cover_letter.md"
    cover_no = run_dir / "cover_letter_no.md"
    if apply_language == "no" and cover_no.is_file():
        cover_letter_path = str(cover_no)
    elif cover_md.is_file():
        cover_letter_path = str(cover_md)
    elif cover_no.is_file():
        cover_letter_path = str(cover_no)

    note = f"CV run: {run_dir}"
    if apply_language == "no":
        note += " (Norwegian)"
    existing = _safe_str(row.get("app_notes"))
    if existing and run_dir_text not in existing:
        note = f"{existing}\n{note}"
    upsert_application(
        conn,
        {
            "uuid": str(full["uuid"]),
            "source": str(full["source"]),
            "track": track,
            "status": "drafted",
            "notes": note,
            "cover_letter_path": cover_letter_path,
            "applied_at": None,
            "follow_up_at": None,
            "updated_at": utc_now_iso(),
        },
    )
    conn.commit()
    del clear_streamlit_cache  # retained for call-site compatibility; caches live in the web layer
    impact_line = format_pipeline_metrics_summary(load_pipeline_metrics(run_dir))
    complete_label = f"{total}/{total} Complete — run `{run_dir.name}`"
    if impact_line:
        complete_label = f"{complete_label} · {impact_line}"
    _update(complete_label, state="complete")
    log.info(
        "apply pipeline complete uuid=%s run=%s track=%s duration_s=%.1f",
        full.get("uuid"),
        run_dir.name,
        track,
        time.monotonic() - started,
    )
    return run_dir.name, errors


def _score_display(row: pd.Series) -> str:
    score = row.get("score_total")
    if score is None or pd.isna(score):
        return "—"
    return f"{float(score):.0f}"


def _format_score_caption(row: pd.Series, *, empty: str = "No score") -> str:
    """Shared score + boost annotation used by card captions and meta lines."""
    score = row.get("score_total")
    if score is None or pd.isna(score):
        return empty
    base = row.get("score_base")
    boost_t = row.get("boost_tek")
    try:
        base_f = float(base) if base is not None and not pd.isna(base) else 0.0
        boost_t_f = float(boost_t) if boost_t is not None and not pd.isna(boost_t) else 0.0
        if base_f <= 0 and boost_t_f <= 0:
            return f"{float(score):.0f}"
        if base_f > 0 and boost_t_f > 0:
            return f"{float(score):.0f} (hits {base_f:.0f}, +TEK {boost_t_f:.0f})"
        if base_f > 0:
            return f"{float(score):.0f} ({base_f:.0f} keyword hits)"
        if boost_t_f > 0:
            return f"{float(score):.0f} (TEK only — no CV keyword match)"
    except (TypeError, ValueError):
        pass
    return f"{float(score):.0f}"


def _score_breakdown(row: pd.Series) -> str:
    return _format_score_caption(row, empty="No score")


def _job_meta_caption(row: pd.Series, *, within_days: int) -> str:
    _ = within_days  # reserved for urgency-aware meta captions
    score_txt = _format_score_caption(row, empty="—")
    loc = format_location(row.to_dict())
    src = source_label_short(_safe_str(row.get("sources")) or _safe_str(row.get("source")))
    dl = deadline_display(row_expires(row))
    return f"{loc} · score {score_txt} · deadline {dl} · {src}"


def _sql_optional_text(value: Any) -> str | None:
    """Normalize DB/pandas cell values to optional stripped text."""
    return _safe_str(value) or None


def application_status_upsert_row(
    row: Mapping[str, Any] | pd.Series,
    new_status: str,
    *,
    now: str | None = None,
    pinned: bool | int | None = None,
) -> dict[str, Any]:
    """Build ``upsert_application`` payload for a status change.

    Preserves notes, cover letter path, and follow-up. Sets ``applied_at`` when
    moving to ``applied`` if that timestamp is not already set.
    """
    stamp = now or utc_now_iso()
    status = (new_status or "").strip()
    if status not in STATUS_OPTIONS:
        raise ValueError(f"Unknown application status: {new_status!r}")
    applied_at = _sql_optional_text(row.get("applied_at"))
    if status == "applied" and not applied_at:
        applied_at = stamp
    if pinned is None:
        pinned_flag = 1 if int(row.get("pinned") or 0) else 0
    else:
        pinned_flag = 1 if pinned else 0
    return {
        "uuid": _safe_str(row.get("uuid")),
        "source": _sql_optional_text(row.get("source")) or "nav_arbeidsplassen",
        "track": _safe_str(row.get("track")),
        "status": status,
        "notes": _sql_optional_text(row.get("notes")),
        "cover_letter_path": _sql_optional_text(row.get("cover_letter_path")),
        "applied_at": applied_at,
        "follow_up_at": _sql_optional_text(row.get("follow_up_at")),
        "updated_at": stamp,
        "pinned": pinned_flag,
    }


def apply_job_quick_action(
    conn,
    *,
    uuid: str,
    source: str,
    track: str,
    action: str,
) -> dict[str, Any]:
    """
    Pin / skip / mark applied / etc. Creates an applications row when needed.

    ``clear`` deletes the application tracking row (role returns to untracked).
    """
    action_key = (action or "").strip().casefold()
    if action_key not in QUICK_JOB_ACTIONS:
        raise ValueError(f"Unknown action: {action!r}")

    job = fetch_job_posting(conn, uuid, source)
    if not job:
        raise LookupError("Job not found.")

    existing = conn.execute(
        "SELECT * FROM applications WHERE uuid = ? AND source = ? AND track = ?",
        (uuid, source, track),
    ).fetchone()
    base = dict(existing) if existing else {
        "uuid": uuid,
        "source": source,
        "track": track,
        "status": "interested",
        "notes": None,
        "cover_letter_path": None,
        "applied_at": None,
        "follow_up_at": None,
        "pinned": 0,
    }

    if action_key == "clear":
        delete_application(conn, uuid, source, track)
        clear_explorer_jobs_cache()
        return {"ok": True, "action": action_key, "cleared": True, "application": None}

    if action_key == "mark_expired":
        from job_search.finn_job_client import FINN_EXPIRED_SENTINEL
        from job_search.job_db import utc_now_iso

        # Hide from ACTIVE explorer / hide-expired without needing a FINN re-fetch.
        conn.execute(
            """
            UPDATE job_postings
            SET status = 'INACTIVE', expires = ?, fetched_at = ?
            WHERE uuid = ? AND source = ?
            """,
            (FINN_EXPIRED_SENTINEL, utc_now_iso(), uuid, source),
        )
        clear_explorer_jobs_cache()
        app_payload = None
        if existing:
            app_payload = {k: existing[k] for k in existing.keys()}
        return {
            "ok": True,
            "action": action_key,
            "cleared": False,
            "application": app_payload,
            "posting": {"uuid": uuid, "source": source, "status": "INACTIVE", "expires": FINN_EXPIRED_SENTINEL},
        }

    status = str(base.get("status") or "interested")
    pinned: bool | None = None
    if action_key == "pin":
        pinned = True
    elif action_key == "unpin":
        pinned = False
    elif action_key == "mark_applied":
        status = "applied"
    elif action_key == "skip":
        status = "skipped"
        pinned = False
    elif action_key == "interested":
        status = "interested"
    elif action_key == "reject":
        status = "rejected"
        pinned = False
    elif action_key == "withdraw":
        status = "withdrawn"
        pinned = False

    payload = application_status_upsert_row(base, status, pinned=pinned)
    upsert_application(conn, payload)
    clear_explorer_jobs_cache()
    return {"ok": True, "action": action_key, "cleared": False, "application": payload}


def filter_applied_roles_df(
    df: pd.DataFrame,
    *,
    status_filter: tuple[str, ...] | list[str],
) -> pd.DataFrame:
    if df.empty or not status_filter:
        return df
    allowed = {s.strip() for s in status_filter if s.strip()}
    if not allowed:
        return df
    return df[df["status"].astype(str).isin(allowed)].reset_index(drop=True)


def bulk_deanonymize_command(df: pd.DataFrame) -> str | None:
    """Combined ``cv apply`` command for drafted rows with CV run IDs in notes."""
    run_ids: list[str] = []
    for _, row in df.iterrows():
        if str(row.get("status") or "") != "drafted":
            continue
        for rid in extract_run_ids_from_notes(row.get("notes")):
            if rid not in run_ids:
                run_ids.append(rid)
    if len(run_ids) < 2:
        return None
    return "~/private/cv/cv apply " + " ".join(run_ids)


def _count_applied_roles(df: pd.DataFrame, *, statuses: set[str] | frozenset[str]) -> int:
    if df.empty:
        return 0
    return int(df["status"].astype(str).isin(statuses).sum())


def json_ready(value: Any) -> Any:
    """Convert pandas/numpy values to JSON-serializable Python objects."""
    if value is None:
        return None
    if isinstance(value, pd.DataFrame):
        return [json_ready(row) for row in value.to_dict(orient="records")]
    if isinstance(value, dict):
        return {str(key): json_ready(val) for key, val in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "item") and not isinstance(value, (bytes, str)):
        try:
            return json_ready(value.item())
        except (ValueError, AttributeError):
            pass
    return value


def job_row_payload(row: Mapping[str, Any] | pd.Series, *, within_days: int = 7) -> dict[str, Any]:
    """Compact JSON row used by explorer, overview, and applied-role lists."""
    data = row.to_dict() if isinstance(row, pd.Series) else dict(row)
    expires = row_expires(data)
    urgency = apply_soon_badge(expires, within_days=within_days)
    payload = json_ready(data)
    payload["location"] = format_location(data)
    payload["deadline"] = deadline_display(expires)
    payload["urgency"] = urgency
    payload["apply_soon"] = bool(urgency) and str(urgency).startswith("Apply soon")
    payload["expired"] = is_expired(expires) or str(data.get("job_status") or data.get("status") or "").upper() == "INACTIVE"
    payload["job_url"] = best_job_url(data)
    payload["source_label"] = source_label_short(_safe_str(data.get("sources") or data.get("source")))
    payload["apply_label"] = apply_button_label(_safe_str(data.get("app_status") or data.get("status")))
    payload["modify_mode"] = is_modify_mode(_safe_str(data.get("app_status") or data.get("status")))
    try:
        payload["pinned"] = bool(int(data.get("pinned") or 0))
    except (TypeError, ValueError):
        payload["pinned"] = False
    return payload


def _load_explorer_base_df(
    *,
    path_s: str,
    track: str,
    min_score: float,
    rogaland_only: bool,
    hide_applied: bool,
    hide_expired: bool,
    query_include_terms: tuple[str, ...],
    exclude_tuple: tuple[str, ...],
    source_filter: str,
    hide_phd_student: bool,
    apply_academic_filter: bool,
    dedupe_cross_source: bool,
    use_tech_allowlist: bool,
    include_tuple: tuple[str, ...],
    urgency_days: int,
    sort_key: str,
) -> tuple[tuple[Any, ...], pd.DataFrame, int]:
    """Filtered + enriched explorer frame, cached by filters + ``order_by`` + DB mtime.

    The free-text query is deliberately *not* part of the key: text search runs on
    top of this cached frame, so typing only pays for the substring match.
    """
    cache_key = (
        "explorer_base",
        path_s,
        _explorer_db_fingerprint(path_s),
        track,
        float(min_score),
        bool(rogaland_only),
        bool(hide_applied),
        bool(hide_expired),
        query_include_terms,
        exclude_tuple,
        source_filter,
        bool(hide_phd_student),
        bool(apply_academic_filter),
        bool(dedupe_cross_source),
        bool(use_tech_allowlist),
        include_tuple,
        int(urgency_days),
        sort_key,
    )
    cached = _EXPLORER_DF_CACHE.get(cache_key)
    if cached is not None:
        _mark_cache_exec("explorer_base_hit")
        return cache_key, cached[0], cached[1]

    _mark_cache_exec("explorer_base_miss")
    df = load_jobs_df(
        path_s,
        track,
        min_score,
        rogaland_only,
        False,
        hide_applied,
        query_include_terms,
        exclude_tuple,
        source_filter,
        hide_phd_student,
        sort_key,
        None,
        academic_roles_only=apply_academic_filter,
    )
    raw_count = len(df)
    _log_dashboard_filter_state(
        track=track,
        academic_roles_only=apply_academic_filter,
        stage="explorer_sql",
        count_before=raw_count,
    )
    if dedupe_cross_source and not df.empty:
        df = dedupe_jobs_df(df)
        _log_dashboard_filter_state(
            track=track,
            academic_roles_only=apply_academic_filter,
            stage="explorer_after_dedup",
            count_before=raw_count,
            count_after=len(df),
        )
    explorer_before = len(df)
    df = apply_dashboard_filters(
        df,
        use_tech_allowlist=use_tech_allowlist and not apply_academic_filter,
        include_terms=include_tuple,
        exclude_terms=exclude_tuple,
        hide_phd_student=hide_phd_student,
        academic_roles_only=apply_academic_filter,
    )
    _log_dashboard_filter_state(
        track=track,
        academic_roles_only=apply_academic_filter,
        stage="explorer_post_filter",
        count_before=explorer_before,
        count_after=len(df),
    )
    df = enrich_jobs_df(df, within_days=urgency_days)
    if hide_expired:
        before_expired = len(df)
        df = filter_expired_jobs_df(df, hide_expired=True)
        _log_dashboard_filter_state(
            track=track,
            academic_roles_only=apply_academic_filter,
            stage="explorer_hide_expired",
            count_before=before_expired,
            count_after=len(df),
        )

    _cache_store(_EXPLORER_DF_CACHE, cache_key, (df, raw_count), _EXPLORER_DF_CACHE_MAX)
    return cache_key, df, raw_count


def load_explorer_jobs_df(
    *,
    path_s: str,
    track: str,
    min_score: float,
    rogaland_only: bool,
    hide_applied: bool,
    hide_expired: bool,
    query_include_terms: tuple[str, ...],
    exclude_tuple: tuple[str, ...],
    source_filter: str,
    hide_phd_student: bool,
    apply_academic_filter: bool,
    dedupe_cross_source: bool,
    use_tech_allowlist: bool,
    include_tuple: tuple[str, ...],
    urgency_days: int,
    text_query: str,
    order_by: str = "score",
) -> tuple[pd.DataFrame, int]:
    """Load and filter explorer jobs (base cached; text search applied on top)."""
    sort_key = order_by if order_by in {"score", "published", "location"} else "score"
    base_key, base_df, raw_count = _load_explorer_base_df(
        path_s=path_s,
        track=track,
        min_score=min_score,
        rogaland_only=rogaland_only,
        hide_applied=hide_applied,
        hide_expired=hide_expired,
        query_include_terms=query_include_terms,
        exclude_tuple=exclude_tuple,
        source_filter=source_filter,
        hide_phd_student=hide_phd_student,
        apply_academic_filter=apply_academic_filter,
        dedupe_cross_source=dedupe_cross_source,
        use_tech_allowlist=use_tech_allowlist,
        include_tuple=include_tuple,
        urgency_days=urgency_days,
        sort_key=sort_key,
    )
    query = (text_query or "").strip()
    if not query:
        return base_df, raw_count

    search_key = (*base_key, query.casefold())
    cached = _EXPLORER_SEARCH_CACHE.get(search_key)
    if cached is not None:
        _mark_cache_exec("explorer_search_hit")
        return cached[0], cached[1]

    _mark_cache_exec("explorer_search_miss")
    filtered = apply_text_search_filter(base_df, text_query)
    _log_dashboard_filter_state(
        track=track,
        academic_roles_only=apply_academic_filter,
        stage="explorer_text_search",
        count_before=len(base_df),
        count_after=len(filtered),
    )
    _cache_store(_EXPLORER_SEARCH_CACHE, search_key, (filtered, raw_count), _EXPLORER_SEARCH_CACHE_MAX)
    return filtered, raw_count


