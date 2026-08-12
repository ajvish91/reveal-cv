#!/usr/bin/env python3
"""
Phase D: Streamlit dashboard — job explorer, scores, application tracking.

**Filtering:** primary mode is an **ICT/AI/CS allowlist** (finite curated terms in `job_filters.py`).
Optional **blocklist** for obvious non-tech roles.

  JOBS_DB=/path/to/jobs.sqlite .venv/bin/streamlit run job_search/dashboard.py

Uses job_search/data/jobs.sqlite by default.

Apply/ingest children prefer ``.venv/bin/python`` when present so deps (PyYAML,
etc.) resolve even if Streamlit was started with another interpreter.
"""
from __future__ import annotations

import html
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

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import pandas as pd
import streamlit as st

from cv_generation.apply_prompts import (
    APPLY_LANGUAGE_LABELS,
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
from job_search.dashboard_refresh import (
    AUTO_REFRESH_MINUTE_OPTIONS,
    format_auto_refresh_label,
    should_periodic_refresh,
)
from job_search.dashboard_styles import (
    dashboard_css,
    inject_scroll_manager,
    render_filter_chips,
    render_results_header,
)
from job_search.deadline_utils import apply_soon_badge, deadline_display, is_apply_soon, row_expires
from job_search.dashboard_debug import (
    debug_log,
    finish_rerun_trace,
    init_dashboard_debug,
    is_debug_enabled,
    log_state_diff,
    render_debug_sidebar,
    short_fingerprint,
    start_rerun_trace,
    timing_span,
)
from job_search.logging_config import configure_logging, get_logger, tail_log_file


def _import_module_resilient(module_name: str):
    """Import with one retry after clearing a half-loaded ``sys.modules`` entry.

    Streamlit run-on-save can leave a KeyError stub in ``sys.modules`` during
    concurrent reloads; popping and re-importing matches the ``job_dedup`` pattern.
    """
    import importlib
    import sys

    for attempt in range(2):
        try:
            return importlib.import_module(module_name)
        except KeyError:
            sys.modules.pop(module_name, None)
            if attempt == 1:
                raise
        except ModuleNotFoundError as exc:
            if "None in sys.modules" not in str(exc):
                raise
            sys.modules.pop(module_name, None)
            if attempt == 1:
                raise
    raise RuntimeError(f"failed to import {module_name}")


_job_db = _import_module_resilient("job_search.job_db")
DEFAULT_DB_PATH = _job_db.DEFAULT_DB_PATH
connect = _job_db.connect
delete_application = _job_db.delete_application
init_schema = _job_db.init_schema
upsert_application = _job_db.upsert_application
upsert_job = _job_db.upsert_job
utc_now_iso = _job_db.utc_now_iso
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

log = get_logger("job_search.dashboard")

STATUS_OPTIONS = [
    "interested",
    "drafted",
    "applied",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
]

DEFAULT_DRAFTS_STATUS_FILTER = ("drafted",)
DEFAULT_APPLIED_STATUS_FILTER = ("applied", "interested")
DRAFTS_STATUS_OPTIONS = ["drafted"]

# Streamlit column weights for compact rows (wide page layout).
# Action buttons need parent columns >= ~1.0 each; do not nest st.columns inside a narrow cell.
JOB_EXPLORER_ROW_COLUMNS = [5.0, 0.9, 1.0, 1.3]
APPLIED_ROLE_ROW_COLUMNS = [5.0, 1.1, 0.7, 1.3, 1.2]
# Drafted rows add a compact "Mark as applied" action between Modify and Delete.
APPLIED_ROLE_ROW_COLUMNS_DRAFTED = [4.6, 1.0, 0.6, 1.15, 1.4, 1.1]

MODIFY_STATUSES = frozenset(
    {"drafted", "applied", "interview", "offer", "rejected", "withdrawn"}
)
# Job explorer "hide applications": drafted CV runs and post-submit stages (not `interested`).
HIDE_APPLIED_STATUSES = MODIFY_STATUSES
# Explorer / sidebar checkbox defaults (also used by tests).
DEFAULT_HIDE_APPLIED = True
DEFAULT_DEDUPE_CROSS_SOURCE = True

PIPELINE_TOTAL_STEPS = 11
PIPELINE_LOG_MAX_LINES = 100
PIPELINE_POLL_SECONDS = 0.75
# Sequential apply queue: 1 running + up to 2 waiting (3 in flight max).
PIPELINE_MAX_WAITING = 2
PIPELINE_MAX_IN_FLIGHT = 1 + PIPELINE_MAX_WAITING

_USE_DIALOG = hasattr(st, "dialog")
LOG_DELETE_BUTTON_COLUMNS = [1.2, 8.8]

# Background apply workers must survive Streamlit script reruns *and* module reloads
# (file-watcher re-imports wipe normal module globals). Keep the registry on `sys`.
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
}

_CV_RUN_NOTES_RE = re.compile(r"CV run:\s*(.+?)(?:\s*\(Norwegian\))?\s*$")
_CACHE_EXEC_COUNTS: dict[str, int] = {}

CV_JOBS_DIR = _root / "cv_generation" / "jobs"
_SOURCE_PREFIX = {
    "finn_no": "finn",
    "nav_arbeidsplassen": "nav",
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
        ap.notes AS app_notes
"""


def title_slug(title: str, max_len: int = 48) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "_", (title or "").strip().lower()).strip("_")
    return (value[:max_len] if value else "role")


def _mark_cache_exec(name: str) -> None:
    _CACHE_EXEC_COUNTS[name] = int(_CACHE_EXEC_COUNTS.get(name) or 0) + 1


def _cache_exec_count(name: str) -> int:
    return int(_CACHE_EXEC_COUNTS.get(name) or 0)


def _log_cache_probe(
    loader: str,
    *,
    fingerprint: str,
    hit: bool | None = None,
    session_reuse: bool | None = None,
    rows: int | None = None,
    raw_rows: int | None = None,
    scope: str | None = None,
) -> None:
    debug_log(
        "cache_probe",
        session_state=st.session_state,
        scope=scope,
        loader=loader,
        cache_hit=hit,
        session_reuse=session_reuse,
        rows=rows,
        raw_rows=raw_rows,
        fingerprint=fingerprint,
    )


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
    return (source or "?")[:12]


def source_display(source: str, uuid: str) -> str:
    if source == "finn_no":
        return f"FINN.no (ad {uuid})"
    if source == "nav_arbeidsplassen":
        return "NAV Arbeidsplassen"
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


@st.cache_data(ttl=600, show_spinner=False)
def _cached_default_artifact_options(job_text: str, track: str) -> dict[str, bool]:
    """Cached JD scan for academic artifact checkboxes (plain industry skips the scan)."""
    return default_artifact_options(job_text, track=track)


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
        academic_defaults = _cached_default_artifact_options(job_text, "academic")
        artifact_defaults = {
            "generate_cover_letter": True,
            "generate_application_letter": academic_defaults["generate_application_letter"],
            "generate_research_proposal": academic_defaults["generate_research_proposal"],
        }
    else:
        artifact_defaults = _cached_default_artifact_options(job_text, track)

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


def _apply_dialog_snapshot() -> dict[str, Any]:
    return {
        "_use_dialog": _USE_DIALOG,
        "apply_dialog_open": st.session_state.get("apply_dialog_open"),
        "apply_dialog_key": st.session_state.get("apply_dialog_key"),
        "apply_dialog_context": st.session_state.get("apply_dialog_context"),
        "pipeline_job_key": st.session_state.get("pipeline_job_key"),
        "pipeline_phase": st.session_state.get("pipeline_phase"),
    }


def _reconcile_apply_dialog_state() -> None:
    """Drop orphan ``apply_dialog_*`` flags so an empty dialog never mounts."""
    updates = reconcile_apply_dialog_flags(_apply_dialog_snapshot())
    if updates and is_debug_enabled(st.session_state):
        debug_log(
            "dialog_state",
            session_state=st.session_state,
            transition="reconcile_clear",
            key=st.session_state.get("apply_dialog_key"),
        )
    for key, value in updates.items():
        st.session_state[key] = value


_FORCE_SCROLL_RESTORE_KEY = "_dashboard_force_scroll_restore"
_EXPLORER_JOBS_CACHE_KEY = "_explorer_jobs_cache_key"
_EXPLORER_JOBS_CACHE_DF = "_explorer_jobs_cache_df"


def _mark_dashboard_scroll_restore() -> None:
    """Request scroll restore on the next full dashboard render (e.g. after dialog dismiss)."""
    st.session_state[_FORCE_SCROLL_RESTORE_KEY] = True
    debug_log(
        "scroll_timeline",
        session_state=st.session_state,
        action="scroll_restore_scheduled",
        reason="dialog_dismiss",
    )


def _invalidate_dashboard_data_caches() -> None:
    """Clear Streamlit data cache and in-session explorer dataframe snapshot."""
    st.cache_data.clear()
    st.session_state.pop(_EXPLORER_JOBS_CACHE_KEY, None)
    st.session_state.pop(_EXPLORER_JOBS_CACHE_DF, None)


def _apply_dialog_fast_path_active() -> bool:
    """True when the Apply/Modify dialog should short-circuit the heavy dashboard page."""
    return apply_dialog_ready(
        use_dialog=_USE_DIALOG,
        apply_dialog_open=bool(st.session_state.get("apply_dialog_open")),
        apply_dialog_key=st.session_state.get("apply_dialog_key"),
        apply_dialog_context=st.session_state.get("apply_dialog_context"),
        pipeline_job_key=st.session_state.get("pipeline_job_key"),
        pipeline_phase=st.session_state.get("pipeline_phase"),
    )


def _pipeline_poll_fast_path_active() -> bool:
    """True when pipeline polling should skip job loads (dialog dismissed, worker running)."""
    if st.session_state.get("apply_dialog_open"):
        return False
    job_key = st.session_state.get("pipeline_job_key")
    if not job_key:
        return False
    return pipeline_fallback_eligible(
        apply_dialog_open=False,
        pipeline_job_key=str(job_key),
        pipeline_panel_rendered=bool(st.session_state.get("pipeline_panel_rendered")),
        pipeline_phase=st.session_state.get("pipeline_phase"),
    )


def _render_pipeline_poll_fast_path() -> None:
    """Minimal page while a background apply worker polls (no job dataframe loads)."""
    with timing_span(
        "render_timing",
        session_state=st.session_state,
        label="pipeline_poll_fast_path",
        scope="pipeline_poll_fast_path",
    ):
        _inject_dashboard_css()
        st.title("Job search")
        st.caption("Apply pipeline running — job lists are paused until it finishes or errors.")
        params = st.session_state.get("pipeline_params") or {}
        track = str(params.get("track") or st.session_state.get("cv_track") or "industry")
        db_path = get_db_path()
        if not db_path.is_file():
            st.warning(f"Database not found: **{db_path}**.")
            return
        conn = connect(db_path)
        init_schema(conn)
        try:
            render_pipeline_panel_fallback(conn, track=track)
        finally:
            conn.close()


def _dismiss_apply_modify_dialog(*, clear_pipeline: bool = False) -> None:
    """Clear dialog flags immediately; optionally drop completed pipeline UI state.

    Does not wait on or kill background workers. While a pipeline is still
    ``queued``/``running``, leave worker state so the page fallback can resume.
    """
    debug_log(
        "dialog_state",
        session_state=st.session_state,
        transition="dismiss",
        key=st.session_state.get("apply_dialog_key"),
        clear_pipeline=clear_pipeline,
    )
    st.session_state.apply_dialog_open = False
    st.session_state.apply_dialog_key = None
    st.session_state.apply_dialog_context = None
    if clear_pipeline:
        st.session_state.pipeline_notice_dismissed = None
        st.session_state.pipeline_phase = None
        st.session_state.pipeline_job_key = None
        st.session_state.pipeline_running = False
        st.session_state.pipeline_result = None
        st.session_state.pipeline_params = None
        st.session_state.pipeline_stage = None
        st.session_state.pipeline_elapsed = 0.0
        st.session_state.pipeline_log_lines = []
        st.session_state.pipeline_panel_rendered = False
        st.session_state.pipeline_queue = []
        st.session_state.pipeline_recent_completion = None
    _mark_dashboard_scroll_restore()


def _on_apply_dialog_dismiss() -> None:
    """st.dialog X / Esc: drop dialog flags only (pipeline keeps running)."""
    if not st.session_state.get("apply_dialog_open"):
        return
    _dismiss_apply_modify_dialog(clear_pipeline=False)


def _on_apply_dialog_cancel_click() -> None:
    """Cancel button on_click — clears flags before main() so fast path is skipped."""
    _dismiss_apply_modify_dialog(clear_pipeline=False)


def _on_apply_dialog_close_click() -> None:
    """Close result dialog but keep finished pipeline state reopenable from the page."""
    _dismiss_apply_modify_dialog(clear_pipeline=False)


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


def _pipeline_active_for_job(job_key: str) -> bool:
    """True when session state holds a pipeline for this job row key."""
    return pipeline_active_for_job_key(
        job_key,
        pipeline_job_key=st.session_state.get("pipeline_job_key"),
        pipeline_phase=st.session_state.get("pipeline_phase"),
    )


def _init_pipeline_session_state() -> None:
    """Default session keys for the active apply pipeline + waiting queue."""
    defaults: dict[str, Any] = {
        "pipeline_running": False,
        "pipeline_job_key": None,
        "pipeline_phase": None,
        "pipeline_stage": None,
        "pipeline_elapsed": 0.0,
        "pipeline_params": None,
        "pipeline_result": None,
        "pipeline_log_lines": [],
        "pipeline_panel_rendered": False,
        "pipeline_notice_dismissed": None,
        "pipeline_queue": [],
        "pipeline_recent_completion": None,
        "pipeline_queue_reject_reason": None,
        "apply_dialog_key": None,
        "apply_dialog_open": False,
        "apply_dialog_context": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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


def _restore_pipeline_dialog_context(job_key: str | None) -> None:
    """Rebuild enough dialog state to reopen pipeline progress/results from the page."""
    if not job_key:
        return
    params = st.session_state.get("pipeline_params") or {}
    row_dict = params.get("row_dict") if isinstance(params.get("row_dict"), dict) else {}
    track = str(params.get("track") or st.session_state.get("cv_track") or "industry")
    ctx = st.session_state.get("apply_dialog_context")
    if not isinstance(ctx, dict) or not ctx:
        st.session_state.apply_dialog_context = {
            "track": track,
            "row_dict": row_dict,
            "app_status": row_dict.get("app_status"),
        }
    else:
        ctx.setdefault("track", track)
        if row_dict:
            ctx.setdefault("row_dict", row_dict)
            ctx.setdefault("app_status", row_dict.get("app_status"))
        st.session_state.apply_dialog_context = ctx


def _open_pipeline_dialog(job_key: str | None = None) -> None:
    """Reopen the existing Apply/Modify dialog for the active pipeline."""
    resolved_job_key = str(job_key or st.session_state.get("pipeline_job_key") or "").strip()
    if not resolved_job_key:
        return
    _restore_pipeline_dialog_context(resolved_job_key)
    st.session_state.apply_dialog_key = resolved_job_key
    st.session_state.apply_dialog_open = True
    if not _USE_DIALOG:
        st.session_state[f"{resolved_job_key}_popover_open"] = True
    debug_log(
        "dialog_state",
        session_state=st.session_state,
        transition="reopen_pipeline",
        key=resolved_job_key,
    )


def _append_pipeline_log_line(line: str) -> list[str]:
    """Append one stdout line to session log; keep the last N lines."""
    text = (line or "").rstrip()
    if not text:
        return list(st.session_state.get("pipeline_log_lines") or [])
    lines = list(st.session_state.get("pipeline_log_lines") or [])
    lines.append(text)
    if len(lines) > PIPELINE_LOG_MAX_LINES:
        lines = lines[-PIPELINE_LOG_MAX_LINES:]
    st.session_state.pipeline_log_lines = lines
    return lines


def _pipeline_log_text() -> str:
    lines = st.session_state.get("pipeline_log_lines") or []
    return "\n".join(lines)


def _render_pipeline_log_expander(*, running: bool) -> Any | None:
    """Collapsible live/recent pipeline stdout under the status UI.

    Returns an ``st.empty`` placeholder when ``running`` so callers can refresh
    ``st.code`` as subprocess lines arrive.
    """
    lines = st.session_state.get("pipeline_log_lines") or []
    if not running and not lines:
        return None
    with st.expander("Pipeline log", expanded=running):
        if running:
            box = st.empty()
            box.code(_pipeline_log_text() or "(waiting for output…)", language="text")
            return box
        st.code(_pipeline_log_text(), language="text")
        return None


def _copy_text_to_clipboard(text: str) -> None:
    """Copy ``text`` via browser clipboard API (runs in the app document)."""
    payload = json.dumps(text)
    snippet = f"""<script>
(function() {{
  var t = {payload};
  function fallback() {{
    var ta = document.createElement("textarea");
    ta.value = t;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand("copy"); }} catch (e) {{}}
    document.body.removeChild(ta);
  }}
  if (navigator.clipboard && navigator.clipboard.writeText) {{
    navigator.clipboard.writeText(t).catch(fallback);
  }} else {{
    fallback();
  }}
}})();
</script>"""
    st.html(snippet, unsafe_allow_javascript=True)


def _render_copyable_bash_command(cmd: str, *, key: str) -> None:
    """Show a bash command with an adjacent Copy button."""
    col_cmd, col_btn = st.columns([5.5, 1], vertical_alignment="center")
    with col_cmd:
        st.code(cmd, language="bash")
    with col_btn:
        if st.button(
            "Copy",
            key=key,
            help="Copy command to clipboard",
            icon=":material/content_copy:",
            width="stretch",
        ):
            _copy_text_to_clipboard(cmd)
            st.toast("Copied to clipboard")


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


def _recover_orphaned_pipeline_if_needed() -> bool:
    """Mark stuck UI state as error when no background worker is alive.

    Call only *after* ``_sync_pipeline_worker_to_session`` so a just-finished
    worker is not mistaken for an interrupt.
    """
    if st.session_state.get("pipeline_phase") != "running":
        return False
    job_key = st.session_state.get("pipeline_job_key")
    if job_key and (
        _pipeline_worker_entry(str(job_key)) is not None
        or _pipeline_worker_thread_alive(str(job_key))
    ):
        return False
    st.session_state.pipeline_phase = "error"
    st.session_state.pipeline_running = False
    st.session_state.pipeline_result = _build_pipeline_result(
        None,
        [
            "Apply was interrupted by a page refresh or another dashboard action. "
            "Check cv_generation/cv_runs/ for a partial or completed run, then retry Apply/Modify."
        ],
    )
    return True


def _sync_pipeline_worker_to_session(job_key: str) -> None:
    """Copy background-worker progress into Streamlit session state."""
    store = _pipeline_worker_entry(job_key)
    if store is None:
        return
    with store["lock"]:
        st.session_state.pipeline_stage = store.get("stage")
        st.session_state.pipeline_elapsed = float(store.get("elapsed") or 0.0)
        st.session_state.pipeline_log_lines = list(store.get("log_lines") or [])
        phase = store.get("phase")
        result = store.get("result")
    if phase in ("complete", "error"):
        st.session_state.pipeline_phase = phase
        st.session_state.pipeline_result = result
        st.session_state.pipeline_running = False
        _invalidate_dashboard_data_caches()
        _touch_data_refresh_clock()
        lock, workers = _pipeline_worker_registry()
        with lock:
            workers.pop(job_key, None)
        _advance_pipeline_queue_after_finish()


def _sync_then_recover_pipeline(job_key: str | None = None) -> None:
    """Sync worker progress first, then only mark orphaned if nothing is alive."""
    key = job_key or st.session_state.get("pipeline_job_key")
    if key:
        _sync_pipeline_worker_to_session(str(key))
    recovered = _recover_orphaned_pipeline_if_needed()
    if recovered:
        _advance_pipeline_queue_after_finish()


def _park_recent_pipeline_completion() -> dict[str, Any] | None:
    """Snapshot the finished active pipeline so the banner can survive start-next."""
    phase = st.session_state.get("pipeline_phase")
    if phase not in ("complete", "error"):
        return None
    params = st.session_state.get("pipeline_params") or {}
    result = st.session_state.get("pipeline_result") or {}
    parked = {
        "job_key": st.session_state.get("pipeline_job_key"),
        "phase": phase,
        "result": result,
        "title": params.get("title"),
        "employer": params.get("employer"),
        "track": params.get("track"),
        "params": dict(params) if isinstance(params, dict) else {},
    }
    st.session_state.pipeline_recent_completion = parked
    st.session_state.pipeline_notice_dismissed = None
    return parked


def _activate_pipeline_from_item(item: dict[str, Any], *, open_dialog: bool = False) -> None:
    """Install waiting-queue item as the active (queued) pipeline — does not start the worker."""
    job_key = str(item.get("job_key") or "").strip()
    row_dict = item.get("row_dict") if isinstance(item.get("row_dict"), dict) else {}
    track = str(item.get("track") or "industry")
    language = normalize_apply_language(item.get("language"))
    options_raw = item.get("options") if isinstance(item.get("options"), dict) else {}
    st.session_state.pipeline_job_key = job_key
    st.session_state.pipeline_params = {
        "row_dict": dict(row_dict),
        "track": track,
        "language": language,
        "options": dict(options_raw),
        "title": str(item.get("title") or row_dict.get("title") or ""),
        "employer": str(item.get("employer") or row_dict.get("employer_name") or ""),
    }
    st.session_state.pipeline_phase = "queued"
    st.session_state.pipeline_result = None
    st.session_state.pipeline_stage = None
    st.session_state.pipeline_elapsed = 0.0
    st.session_state.pipeline_log_lines = []
    st.session_state.pipeline_panel_rendered = False
    st.session_state.pipeline_running = True
    if open_dialog:
        st.session_state.apply_dialog_open = True
        st.session_state.apply_dialog_key = job_key


def _advance_pipeline_queue_after_finish() -> bool:
    """When the active job finished, park its notice and start the next queued job.

    Returns True if a next job was activated (still sequential — worker starts on poll).
    """
    phase = st.session_state.get("pipeline_phase")
    if phase not in ("complete", "error"):
        return False
    queue = _pipeline_waiting_queue()
    if not queue:
        return False

    finished_key = str(st.session_state.get("pipeline_job_key") or "")
    dialog_was_on_finished = (
        bool(st.session_state.get("apply_dialog_open"))
        and str(st.session_state.get("apply_dialog_key") or "") == finished_key
    )
    parked = _park_recent_pipeline_completion()
    remaining, item = dequeue_pipeline_item(queue)
    st.session_state.pipeline_queue = remaining
    if item is None:
        return False

    debug_log(
        "pipeline_dequeue",
        session_state=st.session_state,
        job_key=item.get("job_key"),
        finished_job_key=finished_key,
        queue_len=len(remaining),
        finished_phase=(parked or {}).get("phase"),
    )
    _activate_pipeline_from_item(item, open_dialog=False)
    debug_log(
        "pipeline_start_next",
        session_state=st.session_state,
        job_key=item.get("job_key"),
        title=item.get("title"),
        queue_len=len(remaining),
    )
    # Start the worker immediately so the next job does not wait on dialog close.
    next_track = str(item.get("track") or "industry")
    _run_queued_pipeline(None, track=next_track)
    # Keep the finished job's result visible if the dialog was open on it.
    if dialog_was_on_finished and parked:
        params = parked.get("params") if isinstance(parked.get("params"), dict) else {}
        st.session_state.apply_dialog_open = True
        st.session_state.apply_dialog_key = finished_key
        st.session_state.apply_dialog_context = {
            "track": parked.get("track") or params.get("track") or "industry",
            "view_completion": True,
            "completion": parked,
            "row_dict": params.get("row_dict") if isinstance(params.get("row_dict"), dict) else {},
            "app_status": None,
        }
    return True


def _start_pipeline_worker(
    job_key: str,
    *,
    db_path: Path,
    row_dict: dict[str, Any],
    track: str,
    options: ApplyPipelineOptions | None,
) -> None:
    """Launch apply work on a daemon thread so Streamlit reruns do not cancel it."""
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


def _pipeline_job_title(params: Mapping[str, Any] | None = None) -> str:
    payload = params if isinstance(params, Mapping) else (st.session_state.get("pipeline_params") or {})
    return pipeline_job_display_title(payload.get("title"), payload.get("employer"))


def _pipeline_waiting_queue() -> list[dict[str, Any]]:
    raw = st.session_state.get("pipeline_queue") or []
    return [dict(item) for item in raw if isinstance(item, dict)]


def _pipeline_busy() -> bool:
    return pipeline_phase_is_busy(st.session_state.get("pipeline_phase"))


def _can_enqueue_current_job(job_key: str) -> tuple[bool, str]:
    return can_enqueue_pipeline(
        has_active=_pipeline_busy(),
        active_job_key=st.session_state.get("pipeline_job_key"),
        queue=_pipeline_waiting_queue(),
        job_key=job_key,
        ingest_running=bool(st.session_state.get("ingest_running")),
    )


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
        debug_log(
            "filter_change",
            session_state=st.session_state,
            track=track,
            academic_roles_only=academic_roles_only,
            stage=stage,
            count_before=count_before,
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
        debug_log(
            "filter_change",
            session_state=st.session_state,
            track=track,
            academic_roles_only=academic_roles_only,
            stage=stage,
            count_before=count_before,
            count_after=count_after,
            dropped=dropped,
        )


def effective_academic_roles_only(*, track: str, academic_roles_only: bool) -> bool:
    """Academic CV track always applies the strict research-role display filter."""
    return track == "academic" or academic_roles_only


@st.cache_data(ttl=120)
def count_research_roles_in_db(db_path_str: str) -> int:
    """Active jobs whose title matches postdoc/researcher/lecturer vocabulary."""
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
        return int(row[0]) if row else 0
    finally:
        conn.close()


@dataclass
class IngestCycleOptions:
    """User-selected ingest cycle options from the dashboard sidebar."""

    skip_nav: bool = False
    skip_finn: bool = False
    academic_queries_only: bool = False
    db_path: str | None = None


def build_ingest_cycle_command(
    *,
    skip_nav: bool = False,
    skip_finn: bool = False,
    academic_queries_only: bool = False,
    db_path: str | None = None,
    python_exe: str | None = None,
) -> list[str]:
    """Build ``scripts/run_job_search_cycle.py`` argv for dashboard ingest."""
    exe = resolve_project_python(python_exe)
    cmd = [exe, str(_root / "scripts" / "run_job_search_cycle.py")]
    if db_path:
        cmd.extend(["--db", db_path])
    if skip_nav and skip_finn:
        cmd.append("--skip-ingest")
    elif skip_nav:
        cmd.append("--skip-nav-ingest")
    elif skip_finn:
        cmd.append("--skip-finn-ingest")
    if academic_queries_only:
        # Values must use --finn-ingest-arg=ARG: bare "--search-track" is parsed as a flag, not a value.
        cmd.extend(["--finn-ingest-arg=--search-track", "--finn-ingest-arg=academic"])
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


def _init_ingest_session_state() -> None:
    """Default session keys for the dashboard ingest cycle."""
    defaults: dict[str, Any] = {
        "ingest_running": False,
        "ingest_phase": None,
        "ingest_elapsed": 0.0,
        "ingest_options": None,
        "ingest_result": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _init_refresh_session_state() -> None:
    """Default session keys for optional periodic cache refresh."""
    if "auto_refresh_minutes" not in st.session_state:
        st.session_state.auto_refresh_minutes = 0
    if "last_data_refresh_monotonic" not in st.session_state:
        st.session_state.last_data_refresh_monotonic = time.monotonic()


def _touch_data_refresh_clock() -> None:
    """Reset periodic refresh timer after an explicit cache reload."""
    st.session_state.last_data_refresh_monotonic = time.monotonic()


def _maybe_periodic_data_refresh(interval_minutes: int) -> None:
    """Clear cached queries and rerun when the sidebar auto-refresh interval elapses."""
    if interval_minutes <= 0:
        return
    if st.session_state.get("ingest_running") or st.session_state.get("pipeline_running"):
        return
    now = time.monotonic()
    last = float(st.session_state.get("last_data_refresh_monotonic") or now)
    if not should_periodic_refresh(
        interval_minutes=interval_minutes,
        last_refresh_monotonic=last,
        now_monotonic=now,
    ):
        return
    _touch_data_refresh_clock()
    _invalidate_dashboard_data_caches()
    st.rerun()


def _execute_ingest_cycle() -> None:
    """Run queued ingest + score subprocess and store parsed summary in session state."""
    opts_raw = st.session_state.get("ingest_options") or {}
    options = IngestCycleOptions(
        skip_nav=bool(opts_raw.get("skip_nav")),
        skip_finn=bool(opts_raw.get("skip_finn")),
        academic_queries_only=bool(opts_raw.get("academic_queries_only")),
        db_path=str(opts_raw.get("db_path") or "").strip() or None,
    )
    cmd = build_ingest_cycle_command(
        skip_nav=options.skip_nav,
        skip_finn=options.skip_finn,
        academic_queries_only=options.academic_queries_only,
        db_path=options.db_path,
    )
    log.info(
        "ingest cycle start command=%s skip_nav=%s skip_finn=%s academic_queries_only=%s db=%s",
        " ".join(cmd),
        options.skip_nav,
        options.skip_finn,
        options.academic_queries_only,
        options.db_path or get_db_path(),
    )
    st.session_state.ingest_phase = "running"
    started = time.monotonic()
    log_lines: list[str] = []

    def _on_line(line: str) -> None:
        log_lines.append(line)
        log.info("ingest stdout: %s", line)
        st.session_state.ingest_elapsed = time.monotonic() - started

    try:
        with st.status("Ingest & score running…", expanded=True) as ingest_status:
            ingest_status.write("Fetching NAV + FINN and re-scoring. This usually takes 1–5 minutes.")
            ingest_status.write(f"Command: `{' '.join(cmd)}`")
            code, stdout, stderr = run_ingest_cycle_subprocess(cmd, on_line=_on_line)
            elapsed = time.monotonic() - started
            st.session_state.ingest_elapsed = elapsed
            parsed = parse_ingest_cycle_output(stdout)
            summary = {
                "exit_code": code,
                "duration_seconds": round(elapsed, 1),
                "command": cmd,
                "steps": parsed.get("steps") or {},
                "stdout_tail": "\n".join(log_lines[-40:]) if log_lines else stdout,
                "stderr": stderr,
            }
            if code == 0:
                db_path = Path(options.db_path) if options.db_path else get_db_path()
                if db_path.is_file():
                    summary["active_counts"] = ingest_active_source_counts(db_path)
                if options.academic_queries_only:
                    st.session_state.cv_track = "academic"
                    st.session_state.show_academic_roles_only = True
                ingest_status.update(label=f"Ingest complete ({elapsed:.0f}s)", state="complete")
                st.session_state.ingest_phase = "complete"
                log.info(
                    "ingest cycle complete exit=0 duration_s=%.1f steps=%s",
                    elapsed,
                    list((parsed.get("steps") or {}).keys()),
                )
                _invalidate_dashboard_data_caches()
            else:
                ingest_status.update(label=f"Ingest failed (exit {code})", state="error")
                st.session_state.ingest_phase = "error"
                log.error(
                    "ingest cycle failed exit=%d duration_s=%.1f stderr=%s stdout_tail=%s",
                    code,
                    elapsed,
                    stderr,
                    "\n".join(log_lines[-20:]) if log_lines else stdout,
                )
            st.session_state.ingest_result = summary
    finally:
        st.session_state.ingest_running = False


def _show_ingest_result_panel() -> None:
    """Display ingest cycle summary JSON and post-run counts."""
    result = st.session_state.get("ingest_result") or {}
    phase = st.session_state.get("ingest_phase")
    if phase not in ("complete", "error") or not result:
        return

    if phase == "complete":
        st.success(
            f"Ingest & score finished in {result.get('duration_seconds', 0):.1f}s. "
            "Job lists refreshed."
        )
    else:
        st.error(f"Ingest failed (exit {result.get('exit_code', 1)}).")

    counts = result.get("active_counts") or {}
    if counts:
        nav_n = counts.get("nav_arbeidsplassen", 0)
        finn_n = counts.get("finn_no", 0)
        academic_n = counts.get("academic_track", 0)
        c1, c2, c3 = st.columns(3)
        c1.metric("NAV active", nav_n)
        c2.metric("FINN active", finn_n)
        c3.metric("Academic track", academic_n)

    steps = result.get("steps") or {}
    stored: list[str] = []
    for step_name, payload in steps.items():
        if isinstance(payload, dict) and "stored_rows" in payload:
            stored.append(f"{step_name}: {payload['stored_rows']} stored")
        elif isinstance(payload, dict) and step_name == "score":
            stored.append(f"score: {payload.get('score_rows', 0)} score rows")
    if stored:
        st.caption("Rows stored: " + "; ".join(stored))

    with st.expander("Ingest summary (JSON)", expanded=phase == "error"):
        st.json(
            {
                "duration_seconds": result.get("duration_seconds"),
                "exit_code": result.get("exit_code"),
                "steps": steps,
                "active_counts": counts,
            }
        )

    stderr = (result.get("stderr") or "").strip()
    stdout_tail = (result.get("stdout_tail") or "").strip()
    if phase == "error" and (stderr or stdout_tail):
        with st.expander("Error details", expanded=True):
            if stderr:
                st.code(stderr, language="text")
            if stdout_tail:
                st.code(stdout_tail, language="text")

    if st.button("Dismiss ingest status", key="ingest_dismiss"):
        st.session_state.ingest_phase = None
        st.session_state.ingest_result = None
        st.rerun()


def render_auto_refresh_sidebar_section() -> int:
    """Sidebar toggle for periodic cache refresh (does not run ingest)."""
    st.sidebar.header("Auto-refresh")
    options = list(AUTO_REFRESH_MINUTE_OPTIONS)
    current = int(st.session_state.get("auto_refresh_minutes") or 0)
    if current not in options:
        current = 0
    minutes = st.sidebar.selectbox(
        "Refresh cached data",
        options=options,
        index=options.index(current),
        format_func=format_auto_refresh_label,
        key="auto_refresh_minutes_select",
        help="Reload job lists from SQLite on an interval. Does not fetch NAV/FINN.",
    )
    st.session_state.auto_refresh_minutes = minutes
    if minutes > 0:
        st.sidebar.caption(f"Lists refresh every {minutes} minutes.")
    return minutes


def render_ingest_sidebar_section(db_path_s: str) -> None:
    """Sidebar controls to queue NAV + FINN ingest and scoring."""
    st.sidebar.header("Refresh jobs")
    st.sidebar.caption("Fetches NAV + FINN and re-scores (typically 1–5 minutes).")

    skip_nav = st.sidebar.checkbox("Skip NAV", value=False, key="ingest_skip_nav")
    skip_finn = st.sidebar.checkbox("Skip FINN", value=False, key="ingest_skip_finn")
    academic_queries_only = st.sidebar.checkbox(
        "FINN: academic queries only",
        value=False,
        key="ingest_academic_queries_only",
        help="FINN ingest uses academic search queries only (--search-track academic). NAV ingest is unchanged.",
    )
    if academic_queries_only and st.session_state.get("cv_track", "industry") == "industry":
        st.sidebar.caption(
            "Uses academic FINN queries. On success, **CV track** switches to **academic** "
            "and **Show academic roles only** is enabled under Filters."
        )

    busy = bool(st.session_state.get("ingest_running")) or bool(
        st.session_state.get("pipeline_running")
    )
    if st.sidebar.button(
        "Ingest & score",
        type="primary",
        key="ingest_score_btn",
        disabled=busy,
    ):
        log.info(
            "ingest button clicked skip_nav=%s skip_finn=%s academic_queries_only=%s db=%s",
            skip_nav,
            skip_finn,
            academic_queries_only,
            db_path_s,
        )
        st.session_state.ingest_options = {
            "skip_nav": skip_nav,
            "skip_finn": skip_finn,
            "academic_queries_only": academic_queries_only,
            "db_path": db_path_s,
        }
        st.session_state.ingest_phase = "queued"
        st.session_state.ingest_result = None
        st.session_state.ingest_elapsed = 0.0
        st.session_state.ingest_running = True
        st.rerun()

    phase = st.session_state.get("ingest_phase")
    if phase == "running":
        elapsed = float(st.session_state.get("ingest_elapsed") or 0.0)
        st.sidebar.info(f"Ingest running… {elapsed:.0f}s")
    elif phase == "queued":
        st.sidebar.info("Ingest queued…")

    with st.sidebar.expander("Recent log", expanded=False):
        recent = tail_log_file(lines=50)
        if recent:
            st.code(recent, language="text")
        else:
            st.caption("No log entries yet.")


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
    for col in ("application_url", "link"):
        val = row.get(col) if hasattr(row, "get") else getattr(row, col, None)
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            text = str(val).strip()
            if text:
                return text
    return ""


def apply_text_search_filter(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Free-text search over title, employer, and description (post-filter on dataframe)."""
    text = (query or "").strip()
    if not text or df.empty:
        return df
    tokens = [tok.casefold() for tok in re.split(r"\s+", text) if tok.strip()]
    if not tokens:
        return df
    keep_mask: list[bool] = []
    for _, row in df.iterrows():
        hay = haystack_for_filter(
            row.get("title"),
            row.get("jobtitle"),
            row.get("description_text"),
            row.get("employer_name"),
        )
        keep_mask.append(all(token in hay for token in tokens))
    return df.loc[keep_mask].reset_index(drop=True)


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
    text_query: str,
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
    if hide_applied:
        chips.append("Hide applications")
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
) -> tuple[Any, ...]:
    """Hashable key for the in-session explorer dataframe snapshot."""
    return (
        path_s,
        track,
        float(min_score),
        bool(rogaland_only),
        bool(hide_applied),
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
    )


def _load_explorer_jobs_df(
    *,
    cache_key: tuple[Any, ...],
    path_s: str,
    track: str,
    min_score: float,
    rogaland_only: bool,
    hide_applied: bool,
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
) -> tuple[pd.DataFrame, int]:
    """Load and filter explorer jobs; reuse session snapshot when filters are unchanged."""
    stored_key = st.session_state.get(_EXPLORER_JOBS_CACHE_KEY)
    stored_df = st.session_state.get(_EXPLORER_JOBS_CACHE_DF)
    fingerprint = short_fingerprint(cache_key)
    if stored_key == cache_key and isinstance(stored_df, pd.DataFrame):
        raw_rows = int(st.session_state.get("_explorer_jobs_raw_count") or len(stored_df))
        _log_cache_probe(
            "explorer_jobs_session",
            fingerprint=fingerprint,
            hit=True,
            session_reuse=True,
            rows=len(stored_df),
            raw_rows=raw_rows,
            scope="explorer_fragment",
        )
        return stored_df, raw_rows

    before_calls = _cache_exec_count("load_jobs_df")
    with timing_span(
        "data_load_timing",
        session_state=st.session_state,
        label="explorer_jobs_df",
        scope="explorer_fragment",
        fingerprint=fingerprint,
    ):
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
            "score",
            None,
            academic_roles_only=apply_academic_filter,
        )
    streamlit_cache_hit = _cache_exec_count("load_jobs_df") == before_calls
    raw_count = len(df)
    _log_cache_probe(
        "explorer_jobs_session",
        fingerprint=fingerprint,
        hit=False,
        session_reuse=False,
        rows=len(df),
        raw_rows=raw_count,
        scope="explorer_fragment",
    )
    _log_cache_probe(
        "load_jobs_df",
        fingerprint=fingerprint,
        hit=streamlit_cache_hit,
        session_reuse=False,
        rows=len(df),
        raw_rows=raw_count,
        scope="explorer_fragment",
    )
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
    search_before = len(df)
    df = apply_text_search_filter(df, text_query)
    _log_dashboard_filter_state(
        track=track,
        academic_roles_only=apply_academic_filter,
        stage="explorer_post_filter",
        count_before=explorer_before,
        count_after=search_before,
    )
    if (text_query or "").strip():
        _log_dashboard_filter_state(
            track=track,
            academic_roles_only=apply_academic_filter,
            stage="explorer_text_search",
            count_before=search_before,
            count_after=len(df),
        )
    df = enrich_jobs_df(df, within_days=urgency_days)
    st.session_state[_EXPLORER_JOBS_CACHE_KEY] = cache_key
    st.session_state[_EXPLORER_JOBS_CACHE_DF] = df
    st.session_state["_explorer_jobs_raw_count"] = raw_count
    return df, raw_count


def render_job_explorer_search_bar() -> str:
    """Prominent free-text search at the top of Job explorer."""
    st.markdown('<div class="explorer-search-shell"></div>', unsafe_allow_html=True)
    return st.text_input(
        "Search jobs",
        placeholder="Søk i tittel, arbeidsgiver eller beskrivelse …",
        key="job_explorer_text_search",
        label_visibility="collapsed",
    )


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
        if hide_phd_student and matches_phd_student_opening(hay):
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
        keep_mask.append(not matches_phd_student_opening(hay))
    return df.loc[keep_mask].reset_index(drop=True)


def enrich_jobs_df(df: pd.DataFrame, *, within_days: int = 7) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    out["deadline"] = out.apply(lambda r: deadline_display(row_expires(r)), axis=1)
    out["urgency"] = out.apply(lambda r: apply_soon_badge(row_expires(r), within_days=within_days), axis=1)
    out["apply_soon"] = out["urgency"].astype(str).str.startswith("Apply soon")
    return out


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
    profile_sql = sql_require_profile_relevance() if require_profile_match else ""
    source_clause = ""
    source_params: tuple[str, ...] = ()
    if source_filter and source_filter != "all":
        source_clause = "AND j.source = ?"
        source_params = (source_filter,)
    hide_clause = ""
    if hide_applied:
        hide_statuses = ", ".join(f"'{s}'" for s in sorted(HIDE_APPLIED_STATUSES))
        hide_clause = f"""
        AND NOT EXISTS (
            SELECT 1 FROM applications a
            WHERE a.uuid = j.uuid AND a.source = j.source AND a.track = s.track
            AND a.status IN ({hide_statuses})
        )
        """
    include_sql, include_params = sql_require_any_include(include_terms)
    academic_sql, academic_params = (
        sql_require_academic_role_display() if academic_roles_only else ("", [])
    )
    noise_sql, noise_params = sql_exclude_fragments(exclude_terms)
    phd_sql = sql_phd_student_exclude() if hide_phd_student else ""
    phd_params = tuple(t.casefold() for t in ())  # keep terms applied in Python
    if hide_phd_student:
        from job_search.job_filters import DEFAULT_PHD_STUDENT_EXCLUDE_TERMS

        phd_params = tuple(t.casefold() for t in DEFAULT_PHD_STUDENT_EXCLUDE_TERMS)

    if order_by == "published":
        order_sql = "j.published DESC, s.score_total DESC, j.title"
    else:
        order_sql = "s.score_total DESC, s.score_base DESC, j.title"

    limit_sql = f"LIMIT {int(limit)}" if limit is not None else ""

    q = f"""
    SELECT
    {_JOB_SELECT_COLUMNS}
    FROM job_postings j
    INNER JOIN job_scores s ON s.uuid = j.uuid AND s.source = j.source
    LEFT JOIN applications ap
        ON ap.uuid = j.uuid AND ap.source = j.source AND ap.track = s.track
    WHERE s.track = ?
      AND (j.status IS NULL OR UPPER(j.status) = 'ACTIVE')
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
    )
    return q, params


def dedupe_jobs_df(df: pd.DataFrame) -> pd.DataFrame:
    """Lazy import so Streamlit hot-reload can purge ``sys.modules`` safely."""
    return _import_module_resilient("job_search.job_dedup").dedupe_jobs_df(df)


@st.cache_data(ttl=120)
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


@st.cache_data(ttl=120)
def load_overview_metrics(
    db_path_str: str,
    track: str,
    within_days: int,
) -> dict[str, Any]:
    _mark_cache_exec("load_overview_metrics")
    conn = connect(Path(db_path_str))
    init_schema(conn)
    try:
        source_active = pd.read_sql(
            """
            SELECT source, COUNT(*) AS n
            FROM job_postings
            WHERE status IS NULL OR UPPER(status) = 'ACTIVE'
            GROUP BY source
            ORDER BY source
            """,
            conn,
        )
        n_scored = int(
            pd.read_sql(
                """
                SELECT COUNT(DISTINCT s.uuid || s.source || s.track) AS n
                FROM job_scores s
                JOIN job_postings j ON j.uuid = s.uuid AND j.source = s.source
                WHERE j.status IS NULL OR UPPER(j.status) = 'ACTIVE'
                """,
                conn,
            )["n"].iloc[0]
        )
        n_rogaland = int(
            pd.read_sql(
                """
                SELECT COUNT(*) AS n FROM job_postings
                WHERE (status IS NULL OR UPPER(status) = 'ACTIVE')
                  AND (in_rogaland = 1 OR LOWER(COALESCE(location_label,'')) LIKE '%rogaland%'
                       OR LOWER(COALESCE(county,'')) LIKE '%rogaland%')
                """,
                conn,
            )["n"].iloc[0]
        )
        n_active = int(
            pd.read_sql(
                """
                SELECT COUNT(*) AS n FROM job_postings
                WHERE status IS NULL OR UPPER(status) = 'ACTIVE'
                """,
                conn,
            )["n"].iloc[0]
        )
        n_apps = int(pd.read_sql("SELECT COUNT(*) AS n FROM applications", conn)["n"].iloc[0])
        track_split = pd.read_sql(
            """
            SELECT s.track, COUNT(DISTINCT s.uuid || s.source) AS n
            FROM job_scores s
            JOIN job_postings j ON j.uuid = s.uuid AND j.source = s.source
            WHERE j.status IS NULL OR UPPER(j.status) = 'ACTIVE'
            GROUP BY s.track
            """,
            conn,
        )
        active_jobs = pd.read_sql(
            """
            SELECT uuid, source, expires FROM job_postings
            WHERE status IS NULL OR UPPER(status) = 'ACTIVE'
            """,
            conn,
        )
        apply_soon_count = sum(
            1 for _, row in active_jobs.iterrows() if is_apply_soon(row.get("expires"), within_days=within_days)
        )
        return {
            "source_active": source_active,
            "n_scored": n_scored,
            "n_rogaland": n_rogaland,
            "n_active": n_active,
            "n_apps": n_apps,
            "apply_soon_count": apply_soon_count,
            "track_split": track_split,
        }
    finally:
        conn.close()


@st.cache_data(ttl=120)
def load_overview_jobs_bundle(
    db_path_str: str,
    track: str,
    include_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...],
    source_filter: str,
    hide_phd_student: bool,
    academic_roles_only: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Three capped overview lists in one cache entry (one SQLite connection)."""
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
        frames: list[pd.DataFrame] = []
        for rogaland_section, order_by, limit, require_profile in (
            (False, "score", 30, True),
            (False, "published", 30, False),
            (True, "score", 30, True),
        ):
            q, params = _jobs_query_fragments(
                rogaland_section=rogaland_section,
                order_by=order_by,
                limit=limit,
                require_profile_match=require_profile,
                **common,
            )
            df = pd.read_sql_query(q, conn, params=params)
            frames.append(filter_phd_student_df(df, hide_phd_student))
        return frames[0], frames[1], frames[2]
    finally:
        conn.close()


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
ORDER BY COALESCE(a.applied_at, a.updated_at) DESC
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


@st.cache_data(ttl=45)
def load_applied_roles_df(path_str: str, track: str) -> pd.DataFrame:
    conn = connect(Path(path_str))
    init_schema(conn)
    try:
        return pd.read_sql_query(_APPLIED_ROLES_SQL, conn, params=(track,))
    finally:
        conn.close()


@st.cache_data(ttl=45)
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


def render_job_link(row: dict[str, Any], *, key_prefix: str) -> None:
    url = best_job_url(row)
    if url:
        st.markdown(f'<a href="{url}" target="_blank">Open job</a>', unsafe_allow_html=True)
        return
    desc = _safe_str(row.get("description_text"))
    with st.expander("View posting (offline)", expanded=False):
        if desc:
            st.markdown(desc[:8000])
        else:
            st.caption("No link or description stored for this posting.")


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
        if pipe_err:
            errors.append(pipe_err)
            _emit_log(pipe_err)
        if pipe_out:
            errors.append(pipe_out)
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
    if clear_streamlit_cache:
        _invalidate_dashboard_data_caches()
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


def _html_escape(text: str) -> str:
    return html.escape(text, quote=True)


def _job_card_title_html(row_dict: dict[str, Any], row: pd.Series) -> str:
    title = _html_escape(_safe_str(row.get("title"))[:80] or "—")
    url = best_job_url(row_dict)
    if url:
        return (
            f'<a class="job-card-title" href="{_html_escape(url)}" '
            f'target="_blank" rel="noopener noreferrer">{title}</a>'
        )
    return f'<span class="job-card-title job-card-title-plain">{title}</span>'


def _job_card_meta_html(row: pd.Series, *, within_days: int) -> str:
    employer = _html_escape(_safe_str(row.get("employer_name")) or "—")
    loc = format_location(row.to_dict())
    loc_html = _html_escape(loc) if loc else "—"
    dl = deadline_display(row_expires(row))
    dl_html = _html_escape(dl) if dl else "—"
    urgency = apply_soon_badge(row_expires(row), within_days=within_days)
    src = source_label_short(_safe_str(row.get("sources")) or _safe_str(row.get("source")))

    parts: list[str] = [f'<span class="job-card-employer">{employer}</span>']
    if loc:
        parts.append(f'<span class="job-card-location">{loc_html}</span>')
    if dl:
        dl_class = "job-card-deadline job-card-deadline-urgent" if urgency else "job-card-deadline"
        parts.append(f'<span class="{dl_class}">Frist {dl_html}</span>')
    if src:
        parts.append(f'<span class="job-card-source">{_html_escape(src)}</span>')
    return " · ".join(parts)


def _job_score_badge_html(row: pd.Series) -> str:
    score = row.get("score_total")
    if score is None or pd.isna(score):
        return '<span class="job-score-badge job-score-none">—</span>'
    val = float(score)
    if val >= 75:
        tier = "high"
    elif val >= 30:
        tier = "mid"
    else:
        tier = "low"
    return f'<span class="job-score-badge job-score-{tier}">{_html_escape(f"{val:.0f}")}</span>'


def _status_badge_html(status: str | None) -> str:
    label = (status or "unknown").strip() or "unknown"
    css_class = f"job-status-{label}" if label in _STATUS_BADGE_COLOR else "job-status-unknown"
    return f'<span class="job-status-badge {css_class}">{_html_escape(label)}</span>'


def _job_page_state_key(session_key: str) -> str:
    return f"job_page_{session_key}"


def _job_page_scroll_prev_key(session_key: str) -> str:
    """Session key tracking prior page so pagination can trigger scroll-to-list."""
    return f"_scroll_prev_{_job_page_state_key(session_key)}"


def _job_explorer_page_changed(session_key: str) -> bool:
    """True when Job explorer page index changed since the last render.

    Compares ``job_page_{session_key}`` to a shadow prev key. First paint and
    track switches (new session_key) do not count as a change.
    """
    page_key = _job_page_state_key(session_key)
    prev_key = _job_page_scroll_prev_key(session_key)
    current = int(st.session_state.get(page_key, 1))
    prev = st.session_state.get(prev_key)
    changed = prev is not None and int(prev) != current
    st.session_state[prev_key] = current
    return changed


def render_job_list_pagination(
    total_items: int,
    *,
    page_size: int = 20,
    max_items: int | None = 200,
    session_key: str,
    position: str = "top",
) -> tuple[int, int, int]:
    """Render pagination controls; return (page, start_idx, end_idx_exclusive)."""
    cap = min(total_items, max_items) if max_items else total_items
    total_pages = max(1, (cap + page_size - 1) // page_size)
    page_key = _job_page_state_key(session_key)
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    page = int(st.session_state[page_key])
    page = max(1, min(page, total_pages))
    st.session_state[page_key] = page

    start = (page - 1) * page_size
    end = min(start + page_size, cap)
    show_from = start + 1 if cap else 0
    show_to = end

    st.markdown('<div class="pagination-bar"></div>', unsafe_allow_html=True)
    info_col, prev_col, page_col, next_col, _ = st.columns([3.8, 0.7, 1.4, 0.7, 3.4])
    with info_col:
        if cap:
            st.markdown(
                f'<p class="pagination-info">Viser <strong>{show_from}–{show_to}</strong> '
                f"av <strong>{cap}</strong></p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<p class="pagination-info">Ingen treff</p>', unsafe_allow_html=True)
    with prev_col:
        if st.button(
            "←",
            key=f"{session_key}_prev_{position}",
            disabled=page <= 1,
            help="Forrige side",
            width="stretch",
        ):
            st.session_state[page_key] = page - 1
            debug_log(
                "pagination_change",
                session_state=st.session_state,
                session_key=session_key,
                page=page - 1,
            )
            st.rerun()
    with page_col:
        st.markdown(
            f'<p class="pagination-page">Side {page} av {total_pages}</p>',
            unsafe_allow_html=True,
        )
    with next_col:
        if st.button(
            "→",
            key=f"{session_key}_next_{position}",
            disabled=page >= total_pages,
            help="Neste side",
            width="stretch",
        ):
            st.session_state[page_key] = page + 1
            debug_log(
                "pagination_change",
                session_state=st.session_state,
                session_key=session_key,
                page=page + 1,
            )
            st.rerun()
    return page, start, end


def paginate_jobs_df(
    df: pd.DataFrame,
    *,
    page_size: int = 20,
    max_items: int | None = 200,
    session_key: str,
) -> tuple[pd.DataFrame, int]:
    """Slice ``df`` for the current page (pagination controls rendered separately)."""
    total = len(df)
    cap = min(total, max_items) if max_items else total
    total_pages = max(1, (cap + page_size - 1) // page_size)
    page_key = _job_page_state_key(session_key)
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    page = int(st.session_state[page_key])
    page = max(1, min(page, total_pages))
    st.session_state[page_key] = page
    start = (page - 1) * page_size
    end = min(start + page_size, cap)
    return df.iloc[start:end], start


def _inject_dashboard_css() -> None:
    st.markdown(dashboard_css(), unsafe_allow_html=True)


def _finalize_dashboard_scroll(*, scroll_to_list: bool = False) -> None:
    """Inject unified scroll manager once per rerun, after page content exists."""
    force_restore = bool(st.session_state.pop(_FORCE_SCROLL_RESTORE_KEY, False))
    if force_restore:
        debug_log(
            "scroll_timeline",
            session_state=st.session_state,
            action="scroll_restore_applied",
            restore_mode="force_restore",
            anchor="job_explorer_list",
        )
    elif scroll_to_list:
        debug_log(
            "scroll_timeline",
            session_state=st.session_state,
            action="scroll_restore_applied",
            restore_mode="pagination_to_list",
            anchor="job_explorer_list",
        )
    else:
        debug_log(
            "scroll_timeline",
            session_state=st.session_state,
            action="scroll_restore_skipped",
            reason="no_restore_requested",
        )
    inject_scroll_manager(
        scroll_to_list=scroll_to_list,
        force_restore=force_restore and not scroll_to_list,
    )


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
    boost_r = row.get("boost_rogaland")
    boost_t = row.get("boost_tek")
    try:
        base_f = float(base) if base is not None and not pd.isna(base) else 0.0
        boost_r_f = float(boost_r) if boost_r is not None and not pd.isna(boost_r) else 0.0
        boost_t_f = float(boost_t) if boost_t is not None and not pd.isna(boost_t) else 0.0
        if base_f <= 0 and boost_r_f > 0 and boost_t_f <= 0:
            return f"{float(score):.0f} (location only — no CV keyword match)"
        if base_f > 0 and (boost_r_f > 0 or boost_t_f > 0):
            parts = [f"base {base_f:.0f}"]
            if boost_r_f > 0:
                parts.append(f"+loc {boost_r_f:.0f}")
            if boost_t_f > 0:
                parts.append(f"+TEK {boost_t_f:.0f}")
            return f"{float(score):.0f} ({', '.join(parts)})"
    except (TypeError, ValueError):
        pass
    return f"{float(score):.0f}"


def _score_breakdown(row: pd.Series) -> str:
    return _format_score_caption(row, empty="No score")


def _keyword_hits_text(row: pd.Series) -> str:
    parts: list[str] = []
    kw = row.get("matched_keywords")
    if kw is not None and not pd.isna(kw) and str(kw).strip():
        parts.append(f"Keywords: {kw}")
    sk = row.get("matched_skills")
    if sk is not None and not pd.isna(sk) and str(sk).strip():
        parts.append(f"Skills: {sk}")
    tek = row.get("tek_match_name")
    if tek is not None and not pd.isna(tek) and str(tek).strip():
        parts.append(f"TEK: {tek}")
    return " · ".join(parts) if parts else "No keyword hits recorded"


def _job_meta_caption(row: pd.Series, *, within_days: int) -> str:
    _ = within_days  # reserved for urgency-aware meta captions
    score_txt = _format_score_caption(row, empty="—")
    loc = format_location(row.to_dict())
    src = source_label_short(_safe_str(row.get("sources")) or _safe_str(row.get("source")))
    dl = deadline_display(row_expires(row))
    return f"{loc} · score {score_txt} · deadline {dl} · {src}"


def _show_pipeline_result(
    run_name: str | None,
    errs: list[str],
    *,
    copy_key: str = "pipeline_result",
    result: dict[str, Any] | None = None,
) -> None:
    """Full-width success / warning / error summary after a pipeline finishes.

    Renders the Pipeline log expander once here — callers must not render it again.
    """
    result = result or {}
    if run_name and not errs:
        st.success(f"Draft ready: `{run_name}`")
        impact = None
        run_dir_text = result.get("run_dir")
        artifact_paths = list(result.get("artifact_paths") or [])
        deanonymize_cmd = str(result.get("deanonymize_cmd") or f"~/private/cv/cv apply {run_name}")
        run_dir = Path(run_dir_text) if run_dir_text else resolve_run_dir(run_name, repo_root=_root)
        if run_dir is not None:
            impact = format_pipeline_metrics_summary(load_pipeline_metrics(run_dir))
        if impact:
            st.caption(impact)
        if run_dir_text:
            st.caption(f"Run folder: `{run_dir_text}`")
        if artifact_paths:
            st.caption("Generated files")
            st.code("\n".join(artifact_paths), language="text")
        _render_copyable_bash_command(
            deanonymize_cmd,
            key=f"{copy_key}_deanonymize_copy",
        )
        _render_pipeline_log_expander(running=False)
        return

    if run_name:
        st.warning(f"Pipeline incomplete; run folder: `{run_name}`")
    elif errs:
        st.error("Pipeline failed.")

    run_dir_text = str(result.get("run_dir") or "").strip()
    artifact_paths = list(result.get("artifact_paths") or [])
    deanonymize_cmd = str(result.get("deanonymize_cmd") or "").strip()
    if run_dir_text:
        st.caption(f"Run folder: `{run_dir_text}`")
    if artifact_paths:
        st.caption("Generated files")
        st.code("\n".join(artifact_paths), language="text")

    for err in errs:
        st.error(err)

    long_errs = [err for err in errs if len(err) > 120 or "\n" in err]
    if long_errs:
        with st.expander("Error details", expanded=False):
            st.code("\n\n".join(long_errs))

    if deanonymize_cmd and run_name:
        _render_copyable_bash_command(
            deanonymize_cmd,
            key=f"{copy_key}_deanonymize_copy",
        )
    _render_pipeline_log_expander(running=False)


def _render_pipeline_status_bar(*, track: str) -> bool:
    """Top-of-page summary for a background pipeline; returns True when polling should continue."""
    job_key = st.session_state.get("pipeline_job_key")
    if not job_key or st.session_state.get("apply_dialog_open"):
        return False

    _sync_then_recover_pipeline(str(job_key))
    phase = st.session_state.get("pipeline_phase")
    if phase not in ("queued", "running"):
        return False

    if phase == "queued":
        _run_queued_pipeline(None, track=track)
        phase = st.session_state.get("pipeline_phase")
        if phase not in ("queued", "running"):
            return False

    stage = str(st.session_state.get("pipeline_stage") or "Starting…")
    elapsed = float(st.session_state.get("pipeline_elapsed") or 0.0)
    step = pipeline_stage_number(stage)
    frac = min(step / float(PIPELINE_TOTAL_STEPS), 1.0) if step else 0.03
    waiting = _pipeline_waiting_queue()
    waiting_titles = pipeline_queue_display_titles(waiting)

    st.markdown('<div class="pipeline-status-shell">', unsafe_allow_html=True)
    with st.container(border=True):
        c1, c2 = st.columns([5.6, 1.4], vertical_alignment="center")
        with c1:
            st.markdown(
                f"**Pipeline running**  \n<span class='pipeline-status-job'>{_pipeline_job_title()}</span>",
                unsafe_allow_html=True,
            )
            st.progress(frac, text=f"{stage} ({elapsed:.0f}s)")
            meta = f"Stage: {stage} · Elapsed: {elapsed:.0f}s · Track: {track}"
            if waiting_titles:
                next_list = "; ".join(waiting_titles)
                meta += (
                    f" · Queue: {len(waiting)}/{PIPELINE_MAX_WAITING} waiting"
                    f" — next: {html.escape(next_list)}"
                )
            else:
                meta += f" · Queue: 0/{PIPELINE_MAX_WAITING} waiting"
            st.markdown(
                f"<div class='pipeline-status-meta'>{meta}</div>",
                unsafe_allow_html=True,
            )
        with c2:
            st.button(
                "Open progress",
                key=f"{job_key}_pipeline_status_open",
                width="stretch",
                on_click=_open_pipeline_dialog,
                args=(str(job_key),),
            )
    st.markdown("</div>", unsafe_allow_html=True)
    return st.session_state.get("pipeline_phase") == "running"


def _completion_notice_payload() -> dict[str, Any] | None:
    """Prefer a parked completion (queue advanced); else the idle finished pipeline."""
    recent = st.session_state.get("pipeline_recent_completion")
    if isinstance(recent, dict) and recent.get("job_key"):
        return recent
    phase = st.session_state.get("pipeline_phase")
    if phase not in ("complete", "error"):
        return None
    params = st.session_state.get("pipeline_params") or {}
    return {
        "job_key": st.session_state.get("pipeline_job_key"),
        "phase": phase,
        "result": st.session_state.get("pipeline_result") or {},
        "title": params.get("title"),
        "employer": params.get("employer"),
        "track": params.get("track"),
        "params": params,
    }


def _dismiss_pipeline_notice() -> None:
    payload = _completion_notice_payload() or {}
    st.session_state.pipeline_notice_dismissed = pipeline_notice_id(
        job_key=payload.get("job_key"),
        phase=payload.get("phase"),
        run_name=(payload.get("result") or {}).get("run_name"),
    )
    # Drop parked notice once dismissed so a later finish can show again.
    if st.session_state.get("pipeline_recent_completion") is not None:
        st.session_state.pipeline_recent_completion = None


def _open_completion_notice_dialog() -> None:
    """Reopen result UI for a finished job (including after queue advanced)."""
    payload = _completion_notice_payload()
    if not payload:
        return
    job_key = str(payload.get("job_key") or "").strip()
    if not job_key:
        return
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    st.session_state.apply_dialog_open = True
    st.session_state.apply_dialog_key = job_key
    st.session_state.apply_dialog_context = {
        "track": payload.get("track") or params.get("track") or "industry",
        "view_completion": True,
        "completion": payload,
        "row_dict": params.get("row_dict") if isinstance(params.get("row_dict"), dict) else {},
        "app_status": None,
    }
    debug_log(
        "dialog_state",
        session_state=st.session_state,
        transition="reopen_completion",
        key=job_key,
    )


def _render_pipeline_completion_notice() -> None:
    """Top-of-page success/error banner for a finished pipeline when dialog is closed."""
    if st.session_state.get("apply_dialog_open"):
        return
    payload = _completion_notice_payload()
    if not payload:
        return
    phase = payload.get("phase")
    if phase not in ("complete", "error"):
        return
    result = payload.get("result") or {}
    notice_id = pipeline_notice_id(
        job_key=payload.get("job_key"),
        phase=phase,
        run_name=result.get("run_name"),
    )
    if st.session_state.get("pipeline_notice_dismissed") == notice_id:
        return

    job_title = pipeline_job_display_title(payload.get("title"), payload.get("employer"))
    banner = st.success if phase == "complete" else st.error
    if phase == "complete":
        message = f"Apply pipeline finished for {job_title}."
    else:
        message = f"Apply pipeline failed for {job_title}."
    banner(message)

    c1, c2, c3 = st.columns([1.5, 1.1, 5.4], vertical_alignment="center")
    with c1:
        st.button(
            "Open result",
            key=f"{notice_id}_pipeline_notice_open",
            width="stretch",
            on_click=_open_completion_notice_dialog,
        )
    with c2:
        st.button(
            "Dismiss",
            key=f"{notice_id}_pipeline_notice_dismiss",
            width="stretch",
            on_click=_dismiss_pipeline_notice,
        )
    with c3:
        run_dir = result.get("run_dir")
        if run_dir:
            st.caption(f"Run folder: `{run_dir}`")


def _queue_apply_pipeline(
    job_key: str,
    row_dict: dict[str, Any],
    *,
    track: str,
    options: ApplyPipelineOptions,
) -> None:
    """Start immediately if idle, otherwise enqueue behind the active pipeline."""
    if st.session_state.get("ingest_running"):
        return

    item = build_pipeline_queue_item(job_key, row_dict, track=track, options=options)
    busy = _pipeline_busy()
    ok, reason = can_enqueue_pipeline(
        has_active=busy,
        active_job_key=st.session_state.get("pipeline_job_key"),
        queue=_pipeline_waiting_queue(),
        job_key=job_key,
        ingest_running=False,
    )
    if not ok:
        st.session_state.pipeline_queue_reject_reason = reason
        debug_log(
            "pipeline_enqueue_rejected",
            session_state=st.session_state,
            job_key=job_key,
            reason=reason,
        )
        return

    st.session_state.pipeline_queue_reject_reason = None

    if not busy:
        # Fresh start — clear any parked completion from a prior run.
        st.session_state.pipeline_recent_completion = None
        st.session_state.pipeline_notice_dismissed = None
        _activate_pipeline_from_item(item, open_dialog=True)
        debug_log(
            "pipeline_enqueue",
            session_state=st.session_state,
            job_key=job_key,
            mode="start",
            queue_len=len(_pipeline_waiting_queue()),
        )
        st.rerun()
        return

    waiting, enqueued, enqueue_reason = enqueue_pipeline_item(
        _pipeline_waiting_queue(),
        item,
        max_waiting=PIPELINE_MAX_WAITING,
    )
    if not enqueued:
        st.session_state.pipeline_queue_reject_reason = enqueue_reason
        debug_log(
            "pipeline_enqueue_rejected",
            session_state=st.session_state,
            job_key=job_key,
            reason=enqueue_reason,
        )
        return

    st.session_state.pipeline_queue = waiting
    debug_log(
        "pipeline_enqueue",
        session_state=st.session_state,
        job_key=job_key,
        mode="queue",
        queue_len=len(waiting),
        title=item.get("title"),
    )
    # Close the configure dialog; status bar shows the waiting queue.
    st.session_state.apply_dialog_open = False
    st.session_state.apply_dialog_key = None
    st.session_state.apply_dialog_context = None
    st.rerun()


def _run_queued_pipeline(conn, *, track: str) -> None:
    """Start or poll the background apply worker; never block the Streamlit script on LLM calls."""
    del conn  # Worker opens its own DB connection.
    params = st.session_state.get("pipeline_params") or {}
    row_dict = params.get("row_dict")
    job_key = st.session_state.get("pipeline_job_key")
    if not row_dict or not job_key:
        st.session_state.pipeline_phase = "error"
        st.session_state.pipeline_result = _build_pipeline_result(None, ["Missing pipeline parameters."])
        st.session_state.pipeline_running = False
        _advance_pipeline_queue_after_finish()
        return

    phase = st.session_state.get("pipeline_phase")
    if phase == "queued":
        options = apply_pipeline_options_from_mapping(
            params.get("options"),
            language=params.get("language"),
        )
        st.session_state.pipeline_phase = "running"
        st.session_state.pipeline_stage = "Starting…"
        st.session_state.pipeline_elapsed = 0.0
        st.session_state.pipeline_log_lines = []
        _start_pipeline_worker(
            str(job_key),
            db_path=get_db_path(),
            row_dict=dict(row_dict),
            track=str(params.get("track") or track),
            options=options,
        )

    _sync_pipeline_worker_to_session(str(job_key))


def _render_running_pipeline_progress(*, poll: bool = True) -> None:
    """Show live progress widgets and optionally schedule the next poll rerun."""
    job_title = _pipeline_job_title()
    st.markdown(f"**Running apply pipeline** — {job_title}")
    stage = st.session_state.get("pipeline_stage") or "Starting…"
    elapsed = float(st.session_state.get("pipeline_elapsed") or 0.0)
    step = pipeline_stage_number(stage)
    frac = min(step / float(PIPELINE_TOTAL_STEPS), 1.0) if step else 0.0
    st.progress(frac, text=f"{stage} ({elapsed:.0f}s)")
    st.caption(f"**Stage:** {stage}")
    st.caption(f"Elapsed: {elapsed:.0f}s")
    _render_pipeline_log_expander(running=True)
    if poll and st.session_state.get("pipeline_phase") == "running":
        time.sleep(PIPELINE_POLL_SECONDS)
        st.rerun()


def render_pipeline_status_in_dialog(
    conn,
    *,
    track: str,
    job_key: str,
) -> None:
    """Show live pipeline progress and completion inside the Apply/Modify dialog."""
    if not _pipeline_active_for_job(job_key):
        return

    st.session_state.pipeline_panel_rendered = True
    _sync_then_recover_pipeline(job_key)
    phase = st.session_state.get("pipeline_phase")

    if phase in ("queued", "running"):
        _run_queued_pipeline(conn, track=track)
        phase = st.session_state.get("pipeline_phase")

    if phase == "running":
        _render_running_pipeline_progress(poll=True)
        return

    if phase in ("complete", "error"):
        result = st.session_state.get("pipeline_result") or {}
        _show_pipeline_result(
            result.get("run_name"),
            result.get("errs") or [],
            copy_key=f"{job_key}_dialog",
            result=result,
        )


def render_pipeline_panel(
    conn,
    *,
    track: str,
    job_key: str,
    fallback: bool = False,
) -> None:
    """Show the active pipeline panel below a job row or as a page fallback."""
    if not _pipeline_active_for_job(job_key):
        return

    st.session_state.pipeline_panel_rendered = True
    st.markdown('<div class="pipeline-panel"></div>', unsafe_allow_html=True)

    if fallback:
        st.caption(f"Active pipeline: **{_pipeline_job_title()}**")

    _sync_then_recover_pipeline(job_key)
    phase = st.session_state.get("pipeline_phase")
    if phase in ("queued", "running"):
        _run_queued_pipeline(conn, track=track)
        phase = st.session_state.get("pipeline_phase")

    if phase == "running":
        _render_running_pipeline_progress(poll=True)
        return

    if phase in ("complete", "error"):
        result = st.session_state.get("pipeline_result") or {}
        _show_pipeline_result(
            result.get("run_name"),
            result.get("errs") or [],
            copy_key=f"{job_key}_panel",
            result=result,
        )

def render_pipeline_panel_fallback(conn, *, track: str) -> None:
    """Render the active pipeline at page level when its row is off-screen."""
    if _USE_DIALOG:
        return
    job_key = st.session_state.get("pipeline_job_key")
    if not pipeline_fallback_eligible(
        apply_dialog_open=bool(st.session_state.get("apply_dialog_open")),
        pipeline_job_key=job_key,
        pipeline_panel_rendered=bool(st.session_state.get("pipeline_panel_rendered")),
        pipeline_phase=st.session_state.get("pipeline_phase"),
    ):
        return
    render_pipeline_panel(conn, track=track, job_key=job_key, fallback=True)


def _render_apply_form(
    conn,
    row_dict: dict[str, Any],
    *,
    track: str,
    key_prefix: str,
    app_status: str | None,
) -> None:
    """Apply / Modify form inside the dialog or popover."""
    del conn  # Form uses session context / row_dict only; pipeline worker opens its own DB.
    modify = is_modify_mode(app_status)
    default_prompts = str(st.session_state.get("default_apply_prompts") or "")
    # Prefer precomputed bundle from dialog launch (avoids JD scan + FS checks on every rerun).
    ctx = st.session_state.get("apply_dialog_context") or {}
    bundle = ctx.get("artifacts") if isinstance(ctx.get("artifacts"), dict) else None
    if bundle:
        artifact_defaults = bundle.get("artifact_defaults") or {}
        existing_flags = bundle.get("existing_flags") or {}
        existing_run_name = bundle.get("existing_run_name")
        existing_run = (
            resolve_modify_run_dir(None, run_id=str(existing_run_name))
            if existing_run_name
            else None
        )
        if "show_academic_docs" in bundle:
            show_academic_docs = bool(bundle.get("show_academic_docs"))
        else:
            show_academic_docs = track == "academic" or row_suggests_academic_documents(row_dict)
            if existing_flags.get("application_letter.md") or existing_flags.get(
                "research_proposal.md"
            ):
                show_academic_docs = True
    else:
        computed = _dialog_artifact_bundle(row_dict, track=track, modify=modify)
        artifact_defaults = computed["artifact_defaults"]
        show_academic_docs = bool(computed.get("show_academic_docs"))
        existing_run = resolve_modify_run_dir(row_dict.get("app_notes")) if modify else None
        existing_flags = existing_artifact_flags(existing_run) if modify else {}

    st.caption(f"**{row_dict.get('title') or 'Role'}** — {row_dict.get('employer_name') or '—'}")
    render_job_link(row_dict, key_prefix=f"{key_prefix}_dialog_link")
    if modify and existing_run is not None:
        st.caption(f"Existing run: `{existing_run.name}`")

    language_key = apply_dialog_language_key(key_prefix)
    st.radio(
        "Application language",
        options=("en", "no"),
        format_func=lambda code: APPLY_LANGUAGE_LABELS[code],
        key=language_key,
        horizontal=True,
    )
    custom_prompts = st.text_area(
        "Custom prompts",
        value="",
        height=100,
        placeholder="e.g. emphasize RAG experience; mention Rogaland relocation",
        key=f"{key_prefix}_dialog_prompts",
        help="Merged with sidebar default tailoring instructions when present.",
    )
    if default_prompts.strip():
        st.caption("Sidebar default instructions are included automatically.")

    st.markdown("**Documents**")
    # Cover letter: always on industry; optional on academic (manual opt-in / JD default).
    generate_cover_letter = st.checkbox(
        "Cover letter (`cover_letter.md`)"
        if (track == "academic" or show_academic_docs)
        else "Generate cover letter",
        value=bool(artifact_defaults.get("generate_cover_letter", track == "industry")),
        key=f"{key_prefix}_gen_cover",
    )

    generate_application_letter = False
    generate_research_proposal = False
    if track == "academic" or show_academic_docs:
        generate_application_letter = st.checkbox(
            "Application letter (`application_letter.md`)",
            value=bool(artifact_defaults.get("generate_application_letter", track == "academic")),
            key=f"{key_prefix}_gen_app_letter",
        )
        generate_research_proposal = st.checkbox(
            "Research proposal (`research_proposal.md`)",
            value=bool(artifact_defaults.get("generate_research_proposal", False)),
            key=f"{key_prefix}_gen_proposal",
        )

    overwrite_cover_letter = False
    overwrite_application_letter = False
    overwrite_research_proposal = False
    if modify:
        if existing_flags.get("cover_letter.md"):
            overwrite_cover_letter = st.checkbox(
                "Overwrite existing cover letter",
                value=False,
                key=f"{key_prefix}_ow_cover",
            )
        if existing_flags.get("application_letter.md"):
            overwrite_application_letter = st.checkbox(
                "Overwrite existing application letter",
                value=False,
                key=f"{key_prefix}_ow_app_letter",
            )
        if existing_flags.get("research_proposal.md"):
            overwrite_research_proposal = st.checkbox(
                "Overwrite existing research proposal",
                value=False,
                key=f"{key_prefix}_ow_proposal",
            )

    overwrite_cv = False
    if modify and existing_flags.get(CV_MARKDOWN):
        overwrite_cv = st.checkbox(
            f"Overwrite existing CV (`{CV_MARKDOWN}`)",
            value=False,
            key=f"{key_prefix}_ow_cv",
        )

    notes_key = f"{key_prefix}_dialog_notes"
    if modify or row_dict.get("app_notes"):
        st.text_area(
            "Application notes",
            value=str(row_dict.get("app_notes") or ""),
            height=80,
            key=notes_key,
            help="Stored on the application row when the pipeline completes.",
        )

    pipeline_busy = _pipeline_busy()
    ingest_busy = bool(st.session_state.get("ingest_running"))
    can_start, start_block_reason = can_enqueue_pipeline(
        has_active=pipeline_busy,
        active_job_key=st.session_state.get("pipeline_job_key"),
        queue=_pipeline_waiting_queue(),
        job_key=key_prefix,
        ingest_running=ingest_busy,
    )
    if pipeline_busy and can_start:
        confirm_label = "Queue modify" if modify else "Queue apply"
    else:
        confirm_label = "Modify" if modify else "Start"

    reject = st.session_state.get("pipeline_queue_reject_reason")
    if reject:
        st.warning(str(reject))
    elif pipeline_busy and can_start:
        waiting_n = len(_pipeline_waiting_queue())
        st.caption(
            f"Another pipeline is running. This role will wait in the queue "
            f"({waiting_n}/{PIPELINE_MAX_WAITING} waiting)."
        )
    elif not can_start and start_block_reason:
        st.caption(start_block_reason)

    col_start, col_cancel = st.columns(2)
    with col_start:
        start_clicked = st.button(
            confirm_label,
            key=f"{key_prefix}_dialog_start",
            type="primary",
            width="stretch",
            disabled=not can_start,
        )
    with col_cancel:
        # on_click clears flags before main(); this run skips the dialog fast path.
        st.button(
            "Cancel",
            key=f"{key_prefix}_dialog_cancel",
            width="stretch",
            on_click=_on_apply_dialog_cancel_click,
        )

    if start_clicked:
        selected_language = normalize_apply_language(st.session_state.get(language_key))
        merged_prompts = merge_apply_prompts(default_prompts, custom_prompts)
        row_for_pipeline = dict(row_dict)
        dialog_notes = st.session_state.get(notes_key)
        if dialog_notes is not None:
            row_for_pipeline["app_notes"] = str(dialog_notes).strip() or None
        # Resolve run dir from (possibly edited) notes at Start — not on every dialog paint.
        run_for_options = (
            resolve_modify_run_dir(row_for_pipeline.get("app_notes")) if modify else None
        )
        options = ApplyPipelineOptions(
            language=selected_language,
            apply_prompts=merged_prompts or None,
            generate_cover_letter=generate_cover_letter,
            generate_application_letter=generate_application_letter,
            generate_research_proposal=generate_research_proposal,
            overwrite_cv=overwrite_cv,
            overwrite_cover_letter=overwrite_cover_letter,
            overwrite_application_letter=overwrite_application_letter,
            overwrite_research_proposal=overwrite_research_proposal,
            modify_mode=modify,
            existing_run_id=run_for_options.name if run_for_options is not None else None,
        )
        _queue_apply_pipeline(key_prefix, row_for_pipeline, track=track, options=options)


def _apply_modify_dialog_body() -> None:
    """Dialog body: form or live pipeline status for the active job key.

    No DB open here — form uses session context; the pipeline worker opens its own connection.
    """
    key_prefix = st.session_state.get("apply_dialog_key")
    if not key_prefix:
        return
    key_prefix = str(key_prefix)

    ctx = st.session_state.get("apply_dialog_context") or {}
    if isinstance(ctx, dict) and ctx.get("view_completion"):
        completion = ctx.get("completion") if isinstance(ctx.get("completion"), dict) else {}
        result = completion.get("result") or {}
        # Keep the sequential queue moving while this result dialog stays open.
        active_key = st.session_state.get("pipeline_job_key")
        if active_key and str(active_key) != key_prefix:
            _sync_then_recover_pipeline(str(active_key))
            if st.session_state.get("pipeline_phase") == "queued":
                next_track = str(
                    (st.session_state.get("pipeline_params") or {}).get("track")
                    or ctx.get("track")
                    or "industry"
                )
                _run_queued_pipeline(None, track=next_track)
            if _pipeline_busy():
                st.caption(f"Next in queue running: **{_pipeline_job_title()}**")
        _show_pipeline_result(
            result.get("run_name"),
            result.get("errs") or [],
            copy_key=f"{key_prefix}_completion_dialog",
            result=result,
        )
        st.button(
            "Close",
            key=f"{key_prefix}_completion_dialog_close",
            on_click=_on_apply_dialog_close_click,
        )
        if active_key and str(active_key) != key_prefix and _pipeline_busy():
            time.sleep(PIPELINE_POLL_SECONDS)
            st.rerun()
        return

    if _pipeline_active_for_job(key_prefix):
        params = st.session_state.get("pipeline_params") or {}
        track = str(
            ctx.get("track")
            or params.get("track")
            or st.session_state.get("cv_track")
            or "industry"
        )
        render_pipeline_status_in_dialog(None, track=track, job_key=key_prefix)
        phase = st.session_state.get("pipeline_phase")
        if phase in ("complete", "error"):
            st.button(
                "Close",
                key=f"{key_prefix}_dialog_close",
                on_click=_on_apply_dialog_close_click,
            )
        return

    row_dict = ctx.get("row_dict") if isinstance(ctx.get("row_dict"), dict) else {}
    if not row_dict:
        _dismiss_apply_modify_dialog(clear_pipeline=False)
        return

    track = str(ctx.get("track") or "industry")
    app_status = ctx.get("app_status")
    _render_apply_form(
        None,
        row_dict,
        track=track,
        key_prefix=key_prefix,
        app_status=app_status,
    )


if _USE_DIALOG:
    _open_apply_modify_dialog = st.dialog(
        "Apply / Modify",
        width="large",
        on_dismiss=_on_apply_dialog_dismiss,
    )(_apply_modify_dialog_body)
else:
    _open_apply_modify_dialog = None


def _yield_to_apply_modify_dialog(*, source: str) -> bool:
    """Open Apply/Modify when session flags are ready; return True to skip caller body."""
    snapshot = _apply_dialog_snapshot()
    ready = yield_to_apply_modify_dialog(snapshot)
    debug_log(
        "dialog_ready_check",
        session_state=st.session_state,
        source=source,
        ready=ready,
        apply_dialog_open=bool(snapshot.get("apply_dialog_open")),
        apply_dialog_key=snapshot.get("apply_dialog_key"),
        has_row_context=bool((snapshot.get("apply_dialog_context") or {}).get("row_dict")),
        fast_path=ready,
    )
    if not ready or _open_apply_modify_dialog is None:
        return False
    with timing_span(
        "render_timing",
        session_state=st.session_state,
        label="dialog_open_path",
        scope="dialog_fast_path" if source == "main_fast_path" else source,
        source=source,
        key=snapshot.get("apply_dialog_key"),
    ):
        debug_log(
            "dialog_open",
            session_state=st.session_state,
            source=source,
            key=snapshot.get("apply_dialog_key"),
        )
        _open_apply_modify_dialog()
    return True


def maybe_open_apply_modify_dialog() -> None:
    """Open the Apply/Modify dialog at most once per script run when context is valid."""
    _yield_to_apply_modify_dialog(source="main")


def _prepare_apply_modify_dialog(
    row_dict: dict[str, Any],
    track: str,
    key_prefix: str,
    app_status: str | None,
    db_path_s: str,
) -> None:
    """Set dialog session state only (no rerun).

    Used as ``st.button(..., on_click=...)`` so flags are set *before* ``main()``
    body runs — the next lines hit the dialog fast path and skip job loads.
    """
    modify = is_modify_mode(app_status)
    debug_log(
        "apply_modify_click",
        session_state=st.session_state,
        job_uuid=row_dict.get("uuid"),
        title=str(row_dict.get("title") or "")[:80],
        key_prefix=key_prefix,
        track=track,
    )
    st.session_state.apply_dialog_key = key_prefix
    st.session_state.apply_dialog_context = {
        "db_path_s": db_path_s,
        "track": track,
        "row_dict": row_dict,
        "app_status": app_status,
        # Precompute once at open — not on every widget rerun inside the dialog.
        "artifacts": _dialog_artifact_bundle(row_dict, track=track, modify=modify),
    }
    # Fresh dialog: sync language radio to sidebar default (avoids stale per-job widget state).
    st.session_state[apply_dialog_language_key(key_prefix)] = normalize_apply_language(
        st.session_state.get("default_apply_language")
    )
    st.session_state.apply_dialog_open = True
    debug_log(
        "dialog_state",
        session_state=st.session_state,
        transition="open",
        key_prefix=key_prefix,
    )
    if not _USE_DIALOG:
        st.session_state[f"{key_prefix}_popover_open"] = True


def _launch_apply_modify_dialog(
    conn,
    row_dict: dict[str, Any],
    *,
    track: str,
    key_prefix: str,
    app_status: str | None,
    db_path_s: str,
) -> None:
    """Prepare dialog state then rerun (non-callback callers)."""
    del conn  # Dialog / worker open their own connections when needed.
    _prepare_apply_modify_dialog(row_dict, track, key_prefix, app_status, db_path_s)
    st.rerun()


def render_apply_modify_button(
    conn,
    row_dict: dict[str, Any],
    *,
    track: str,
    key_prefix: str,
    app_status: str | None = None,
    db_path_s: str = "",
) -> None:
    """Single Apply or Modify button that opens the configuration dialog."""
    label = apply_button_label(app_status)
    ingest_busy = bool(st.session_state.get("ingest_running"))
    pipeline_busy = _pipeline_busy()
    waiting = _pipeline_waiting_queue()
    is_active = str(st.session_state.get("pipeline_job_key") or "") == str(key_prefix)
    queue_full = pipeline_queue_is_full(has_active=pipeline_busy, queue_len=len(waiting))
    # Allow opening Apply on other roles while a pipeline runs (to enqueue).
    # Disable only when ingest is busy, or the waiting queue is full (except the active job).
    disabled = ingest_busy or (queue_full and not is_active)
    help_text = None
    if ingest_busy:
        help_text = "Ingest is running — wait until it finishes."
    elif queue_full and not is_active:
        help_text = (
            f"Queue full (max {PIPELINE_MAX_WAITING} waiting). "
            "Wait for a slot before starting another Apply."
        )
    elif pipeline_busy and not is_active:
        help_text = "Pipeline running — open to configure and queue this role."
        label = f"Queue {label.lower()}" if label in ("Apply", "Modify") else label

    # on_click runs before main() body → fast path opens dialog without DF loads.
    st.button(
        label,
        key=f"{key_prefix}_apply_modify",
        type="primary",
        width="stretch",
        disabled=disabled,
        help=help_text,
        on_click=_prepare_apply_modify_dialog,
        args=(row_dict, track, key_prefix, app_status, db_path_s),
    )

    if not _USE_DIALOG and st.session_state.get(f"{key_prefix}_popover_open"):
        with st.popover(label, width="stretch"):
            if _pipeline_active_for_job(key_prefix):
                render_pipeline_panel(conn, track=track, job_key=key_prefix)
            else:
                _render_apply_form(
                    conn,
                    row_dict,
                    track=track,
                    key_prefix=key_prefix,
                    app_status=app_status,
                )


def render_apply_modify_popover_fallback(conn, *, track: str) -> None:
    """Re-open popover after rerun when dialog API is unavailable."""
    if _USE_DIALOG:
        return
    key_prefix = st.session_state.get("apply_dialog_key")
    if not key_prefix or not st.session_state.get("apply_dialog_open"):
        return
    ctx = st.session_state.get("apply_dialog_context") or {}
    row_dict = ctx.get("row_dict") or {}
    app_status = ctx.get("app_status")
    with st.popover(apply_button_label(app_status), width="stretch"):
        if _pipeline_active_for_job(key_prefix):
            render_pipeline_panel(conn, track=track, job_key=key_prefix)
        else:
            _render_apply_form(
                conn,
                row_dict,
                track=track,
                key_prefix=key_prefix,
                app_status=app_status,
            )


def render_job_details(
    conn,
    row: pd.Series,
    *,
    track: str,
    key_prefix: str,
    within_days: int,
) -> None:
    """Expanded job details: meta, links."""
    row_dict = row.to_dict()
    loc = format_location(row_dict)
    src = source_label_short(_safe_str(row.get("sources")) or _safe_str(row.get("source")))
    dl = deadline_display(row_expires(row))
    st.caption(f"{loc} · deadline {dl} · {src}")
    st.caption(f"Score: {_score_breakdown(row)}")
    st.caption(_keyword_hits_text(row))
    if row.get("app_status"):
        st.caption(f"Application status: {status_badge_markdown(str(row['app_status']))}")
    render_job_link(row_dict, key_prefix=f"{key_prefix}_link")


def render_compact_job_row(
    conn,
    row: pd.Series,
    *,
    track: str,
    key_prefix: str,
    within_days: int,
    db_path_s: str = "",
) -> None:
    """Card-style job listing: title link, metadata, score badge, actions."""
    row_dict = row.to_dict()
    app_status = _safe_str(row.get("app_status")) or None
    urgency = apply_soon_badge(row_expires(row), within_days=within_days)

    with st.container(border=True):
        st.markdown('<div class="job-card-marker"></div>', unsafe_allow_html=True)
        header_left, header_right = st.columns([5.6, 1.1], gap="small", vertical_alignment="top")
        with header_left:
            urgency_html = ""
            if urgency:
                urgency_html = f'<span class="job-card-urgency">{_html_escape(urgency)}</span>'
            st.markdown(
                f'<div class="job-card-header">{urgency_html}{_job_card_title_html(row_dict, row)}</div>'
                f'<div class="job-card-meta">{_job_card_meta_html(row, within_days=within_days)}</div>',
                unsafe_allow_html=True,
            )
        with header_right:
            st.markdown(_job_score_badge_html(row), unsafe_allow_html=True)
            if app_status:
                st.markdown(_status_badge_html(app_status), unsafe_allow_html=True)

        st.markdown('<div class="job-card-actions"></div>', unsafe_allow_html=True)
        act_apply, act_details, _ = st.columns([1.35, 1.15, 4.5], gap="small")
        with act_apply:
            render_apply_modify_button(
                conn,
                row_dict,
                track=track,
                key_prefix=key_prefix,
                app_status=app_status,
                db_path_s=db_path_s,
            )
        with act_details:
            with st.expander("Details", expanded=False):
                render_job_details(
                    conn,
                    row,
                    track=track,
                    key_prefix=key_prefix,
                    within_days=within_days,
                )


def _sql_optional_text(value: Any) -> str | None:
    """Normalize DB/pandas cell values to optional stripped text."""
    return _safe_str(value) or None


def application_status_upsert_row(
    row: Mapping[str, Any] | pd.Series,
    new_status: str,
    *,
    now: str | None = None,
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
    }


def _handle_application_status_update(
    conn,
    row: Mapping[str, Any] | pd.Series,
    new_status: str,
) -> None:
    """Upsert application status, refresh caches, and rerun the dashboard."""
    payload = application_status_upsert_row(row, new_status)
    if not payload["uuid"] or not payload["track"]:
        st.error("Missing job uuid or track; cannot update status.")
        return
    upsert_application(conn, payload)
    conn.commit()
    _invalidate_dashboard_data_caches()
    st.success(f"Status updated to `{payload['status']}`.")
    st.rerun()


def _handle_delete_application(
    conn,
    *,
    uuid: str,
    source: str,
    track: str,
) -> None:
    """Remove one ``applications`` row; CV run folders on disk are unchanged."""
    delete_application(
        conn,
        uuid.strip(),
        source.strip() or "nav_arbeidsplassen",
        track,
    )
    conn.commit()
    _invalidate_dashboard_data_caches()
    st.success("Application record deleted. CV run folders were not removed.")
    st.rerun()


def render_delete_application_popover(
    conn,
    *,
    uuid: str,
    source: str,
    track: str,
    key_prefix: str,
    subtitle: str | None = None,
) -> None:
    """Popover to delete an application row from SQLite (not cv_runs)."""
    if not (uuid or "").strip():
        st.button(
            "Delete",
            key=f"{key_prefix}_delete_disabled",
            disabled=True,
            width="stretch",
        )
        return
    with st.popover("Delete", width="stretch"):
        st.markdown("**Delete application**")
        st.caption(
            "This removes tracking only from the database. "
            "Folders under `cv_generation/cv_runs/` are **not** deleted."
        )
        if subtitle:
            st.caption(subtitle)
        st.caption(f"`{uuid.strip()}` · {source_label_short(source)} · {track}")
        if st.button(
            "Delete application",
            key=f"{key_prefix}_delete_confirm",
            width="stretch",
        ):
            _handle_delete_application(
                conn,
                uuid=uuid,
                source=source,
                track=track,
            )


def render_application_status_controls(
    conn,
    row: Mapping[str, Any] | pd.Series,
    *,
    key_prefix: str,
    show_mark_applied: bool = False,
) -> None:
    """Status select + save for one application row.

    Optional mark-as-applied shortcut is for callers that do not already place
    that control on the compact action row (Drafts uses the row button instead).
    """
    current = _safe_str(row.get("status"))
    if show_mark_applied and current == "drafted":
        if st.button(
            "Mark as applied",
            key=f"{key_prefix}_mark_applied",
            type="secondary",
        ):
            _handle_application_status_update(conn, row, "applied")

    status_index = STATUS_OPTIONS.index(current) if current in STATUS_OPTIONS else 0
    new_status = st.selectbox(
        "Application status",
        STATUS_OPTIONS,
        index=status_index,
        key=f"{key_prefix}_status_select",
    )
    if st.button("Update status", key=f"{key_prefix}_status_save", width="stretch"):
        if new_status == current:
            st.caption("Status unchanged.")
        else:
            _handle_application_status_update(conn, row, new_status)


def render_applied_role_details(
    conn,
    row: pd.Series,
    *,
    track: str,
    key_prefix: str,
) -> None:
    """Expanded details for an applied role: status, meta, runs, deanonymize, links."""
    row_dict = row.to_dict()
    # Mark-as-applied lives on the compact drafted row; Details keeps select + save.
    render_application_status_controls(
        conn,
        row,
        key_prefix=f"{key_prefix}_details",
        show_mark_applied=False,
    )
    loc = format_location(row_dict)
    src = source_label_short(_safe_str(row.get("source")))
    st.caption(f"{loc} · {src}")
    if row.get("applied_at"):
        st.caption(f"Applied at: {row['applied_at']}")
    if row.get("updated_at"):
        st.caption(f"Updated: {row['updated_at']}")
    st.caption(f"Score: {_score_breakdown(row)}")

    run_ids = extract_run_ids_from_notes(row.get("notes"))
    if run_ids:
        latest = run_ids[-1]
        st.caption(f"CV run: `{latest}`")
        impact = pipeline_metrics_summary_for_notes(row.get("notes"))
        if impact:
            st.caption(impact)
        st.code(f"~/private/cv/cv apply {latest}", language="bash")
        if len(run_ids) > 1:
            earlier = ", ".join("`" + rid + "`" for rid in run_ids[:-1])
            st.caption("Earlier runs: " + earlier)
    notes = _safe_str(row.get("notes"))
    if notes:
        with st.expander("Application notes", expanded=False):
            st.text(notes)
    cover = _safe_str(row.get("cover_letter_path"))
    if cover:
        st.caption(f"Cover letter path: `{cover}`")

    render_job_link(row_dict, key_prefix=f"{key_prefix}_link")


def render_applied_role_row(
    conn,
    row: pd.Series,
    *,
    track: str,
    key_prefix: str,
    db_path_s: str = "",
) -> None:
    """Compact applied-role row: title, status badge, score, Modify / Mark as applied / Delete."""
    row_dict = row_dict_for_apply_from_app(row)
    status = str(row.get("status") or "")
    title = str(row.get("title") or "")[:65]
    employer = str(row.get("employer_name") or "—")
    score_txt = _score_display(row)
    badge = status_badge_markdown(status)

    with st.container(border=False):
        st.markdown('<div class="job-compact-row"></div>', unsafe_allow_html=True)
        if status == "drafted":
            c_title, c_status, c_score, c_modify, c_mark, c_del = st.columns(
                APPLIED_ROLE_ROW_COLUMNS_DRAFTED,
                gap="small",
            )
        else:
            c_title, c_status, c_score, c_modify, c_del = st.columns(
                APPLIED_ROLE_ROW_COLUMNS,
                gap="small",
            )
            c_mark = None
        with c_title:
            st.markdown(f"**{title}** — {employer}")
        with c_status:
            st.markdown(badge)
        with c_score:
            st.markdown(f"**{score_txt}**")
        with c_modify:
            render_apply_modify_button(
                conn,
                row_dict,
                track=track,
                key_prefix=key_prefix,
                app_status=status,
                db_path_s=db_path_s,
            )
        if c_mark is not None:
            with c_mark:
                if st.button(
                    "Mark as applied",
                    key=f"{key_prefix}_mark_applied",
                    type="secondary",
                    width="stretch",
                ):
                    _handle_application_status_update(conn, row, "applied")
        with c_del:
            render_delete_application_popover(
                conn,
                uuid=str(row.get("uuid") or ""),
                source=str(row.get("source") or "nav_arbeidsplassen"),
                track=str(row.get("track") or track),
                key_prefix=key_prefix,
                subtitle=f"{title} — {employer}",
            )
        with st.expander("Details", expanded=False):
            render_applied_role_details(
                conn,
                row,
                track=track,
                key_prefix=key_prefix,
            )


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


def _render_applied_roles_subsection(
    conn,
    *,
    apps_all: pd.DataFrame,
    path_s: str,
    track: str,
    section_title: str,
    section_count: int,
    key_prefix: str,
    row_key_prefix: str,
    default_status_filter: tuple[str, ...],
    status_options: list[str],
    show_bulk_deanonymize: bool = False,
) -> None:
    """Collapsible applied-roles list with status filter and compact rows."""
    count_all = len(apps_all)

    with st.expander(f"{section_title} ({section_count})", expanded=False):
        show_all = st.checkbox(
            "Show all applications",
            value=False,
            key=f"{key_prefix}_show_all",
            help="Ignore status filter and list every application for this track.",
        )
        if show_all:
            status_filter = tuple(STATUS_OPTIONS)
        else:
            status_filter = tuple(
                st.multiselect(
                    "Status filter",
                    options=status_options,
                    default=list(default_status_filter),
                    key=f"{key_prefix}_status_filter",
                )
            )

        apps = filter_applied_roles_df(apps_all, status_filter=status_filter)
        if apps.empty:
            st.caption("No applications match the current filter.")
            if count_all > 0:
                st.caption(f"{count_all} total for **{track}** track (change filter above).")
            return

        st.caption(
            f"Showing {len(apps)} of {count_all} for **{track}** track "
            "(sorted by applied_at, then updated_at)."
        )

        if show_bulk_deanonymize:
            bulk_cmd = bulk_deanonymize_command(apps)
            if bulk_cmd:
                st.caption("Bulk deanonymize drafted runs:")
                st.code(bulk_cmd, language="bash")

        for idx, (_, row) in enumerate(apps.iterrows()):
            render_applied_role_row(
                conn,
                row,
                track=track,
                key_prefix=f"{row_key_prefix}_{idx}",
                db_path_s=path_s,
            )

        with st.expander("All rows (table)", expanded=False):
            st.dataframe(
                apps,
                column_config={
                    "source": st.column_config.TextColumn("Source"),
                    "link": st.column_config.LinkColumn("Job link"),
                    "score_total": st.column_config.NumberColumn(format="%.1f"),
                },
                hide_index=True,
            )


def render_applied_roles_section(
    conn,
    *,
    path_s: str,
    track: str,
) -> None:
    """Drafts and applied-role lists for the current CV track."""
    apps_all = load_applied_roles_df(path_s, track)
    drafted_statuses = frozenset({"drafted"})
    non_draft_statuses = frozenset(s for s in STATUS_OPTIONS if s != "drafted")

    _render_applied_roles_subsection(
        conn,
        apps_all=apps_all,
        path_s=path_s,
        track=track,
        section_title="Drafts",
        section_count=_count_applied_roles(apps_all, statuses=drafted_statuses),
        key_prefix="drafts_roles",
        row_key_prefix="draft",
        default_status_filter=DEFAULT_DRAFTS_STATUS_FILTER,
        status_options=DRAFTS_STATUS_OPTIONS,
        show_bulk_deanonymize=True,
    )
    _render_applied_roles_subsection(
        conn,
        apps_all=apps_all,
        path_s=path_s,
        track=track,
        section_title="Applied roles",
        section_count=_count_applied_roles(apps_all, statuses=non_draft_statuses),
        key_prefix="applied_roles",
        row_key_prefix="app",
        default_status_filter=DEFAULT_APPLIED_STATUS_FILTER,
        status_options=list(STATUS_OPTIONS),
        show_bulk_deanonymize=False,
    )


def render_overview_section(
    conn,
    label: str,
    df: pd.DataFrame,
    *,
    track: str,
    section_key: str,
    within_days: int,
    db_path_s: str = "",
    preview_limit: int = 5,
    default_expanded: bool = False,
    extra_caption: str | None = None,
    extra_controls: Any | None = None,
) -> None:
    """Collapsible overview list with compact job rows."""
    count = len(df)
    with st.expander(f"{label} ({count})", expanded=default_expanded):
        if extra_caption:
            st.caption(extra_caption)
        if extra_controls is not None:
            extra_controls()
        if df.empty:
            st.caption("No matching rows.")
            return
        preview = enrich_jobs_df(df.head(preview_limit), within_days=within_days)
        st.markdown('<div class="job-card-list"></div>', unsafe_allow_html=True)
        for idx, (_, row) in enumerate(preview.iterrows()):
            render_compact_job_row(
                conn,
                row,
                track=track,
                key_prefix=f"{section_key}_{idx}",
                within_days=within_days,
                db_path_s=db_path_s,
            )
        if count > preview_limit:
            st.caption(
                f"Showing top {preview_limit} of {count}. "
                "Open **Job explorer** below for the full ranked list."
            )


@st.fragment
def _render_overview_fragment(
    conn,
    *,
    track: str,
    within_days: int,
    path_s: str,
    apply_academic_filter: bool,
    relevant_raw: pd.DataFrame,
    newest_raw: pd.DataFrame,
    rogaland_raw: pd.DataFrame,
    profile_filter_kwargs: dict[str, Any],
) -> None:
    """Overview expanders isolated so in-section slider changes skip the job explorer."""
    start_rerun_trace(st.session_state, scope="overview_fragment", trigger="fragment_render")
    try:
        if _yield_to_apply_modify_dialog(source="overview_fragment"):
            return

        with timing_span(
            "render_timing",
            session_state=st.session_state,
            label="overview_render",
            scope="overview_fragment",
            track=track,
        ):
            def _relevant_score_slider() -> None:
                min_score_key = f"overview_min_score_{track}"
                default_min = 0.0 if track == "academic" else 15.0
                if min_score_key not in st.session_state:
                    st.session_state[min_score_key] = default_min
                st.slider(
                    "Minimum score (relevant section only)",
                    0.0,
                    150.0,
                    key=min_score_key,
                    step=1.0,
                )

            overview_min_score = st.session_state.get(
                f"overview_min_score_{track}",
                0.0 if track == "academic" else 15.0,
            )
            relevant_before = len(relevant_raw)
            relevant_filtered = apply_dashboard_filters(
                relevant_raw,
                min_score=overview_min_score,
                **profile_filter_kwargs,
            )
            _log_dashboard_filter_state(
                track=track,
                academic_roles_only=apply_academic_filter,
                stage="overview_relevant_post_filter",
                count_before=relevant_before,
                count_after=len(relevant_filtered),
            )

            st.markdown("### Overview")
            overview_caption = (
                "Relevant and Rogaland sections require CV keyword/skill overlap "
                "(location-only +5 or TEK-only +25 without profile match are hidden). "
                "Expand a section to preview top matches."
            )
            if apply_academic_filter:
                research_n = count_research_roles_in_db(path_s)
                overview_caption += (
                    f" Academic filter on ({research_n} postdoc/researcher/lecturer titles in DB)."
                )
            st.caption(overview_caption)

            render_overview_section(
                conn,
                "Relevant positions",
                relevant_filtered,
                track=track,
                section_key="rel",
                within_days=within_days,
                db_path_s=path_s,
                default_expanded=False,
                extra_caption=(
                    f"Top scored for **{track}** track; minimum score **{overview_min_score:.0f}**. "
                    "Requires CV keyword overlap or score above the location-only boost."
                ),
                extra_controls=_relevant_score_slider,
            )
            render_overview_section(
                conn,
                "Newest positions",
                newest_raw.head(10),
                track=track,
                section_key="new",
                within_days=within_days,
                db_path_s=path_s,
                default_expanded=False,
            )
            render_overview_section(
                conn,
                "Rogaland + profile match",
                rogaland_raw.head(10),
                track=track,
                section_key="rog",
                within_days=within_days,
                db_path_s=path_s,
                default_expanded=False,
            )
    finally:
        active_scope = (st.session_state.get("_dashboard_debug_rerun_context") or {}).get("scope")
        if active_scope == "overview_fragment":
            log_state_diff(st.session_state)
            finish_rerun_trace(st.session_state, note="overview_fragment")


@st.fragment
def _render_job_explorer_fragment(
    conn,
    *,
    path_s: str,
    track: str,
    query_include_terms: tuple[str, ...],
    exclude_tuple: tuple[str, ...],
    source_filter: str,
    hide_phd_student: bool,
    apply_academic_filter: bool,
    dedupe_cross_source: bool,
    use_tech_allowlist: bool,
    include_tuple: tuple[str, ...],
    urgency_days: int,
) -> bool:
    """Job explorer isolated so in-section control changes skip overview / applied rows."""
    start_rerun_trace(st.session_state, scope="explorer_fragment", trigger="fragment_render")
    try:
        if _yield_to_apply_modify_dialog(source="explorer_fragment"):
            return False

        with timing_span(
            "render_timing",
            session_state=st.session_state,
            label="explorer_render",
            scope="explorer_fragment",
            track=track,
        ):
            st.header("Job explorer")
            text_query = render_job_explorer_search_bar()

            st.markdown('<div class="explorer-secondary-filters"></div>', unsafe_allow_html=True)
            fc1, fc2, fc3 = st.columns(3)
            with fc1:
                min_score = st.slider("Minimum score_total", 0.0, 150.0, 0.0, 1.0)
            with fc2:
                rogaland_only = st.checkbox(
                    "Preferred locations only",
                    value=False,
                    help="Uses `locations_preferred` from the loaded CV profiles.",
                )
            with fc3:
                hide_applied = st.checkbox(
                    "Hide jobs with an application (drafted, applied, or later)",
                    value=DEFAULT_HIDE_APPLIED,
                    help=(
                        "Hides jobs with a drafted CV run or an application at applied stage "
                        "or beyond. Jobs marked interested only still appear."
                    ),
                )

            cache_key = _explorer_jobs_cache_fingerprint(
                path_s=path_s,
                track=track,
                min_score=min_score,
                rogaland_only=rogaland_only,
                hide_applied=hide_applied,
                query_include_terms=query_include_terms,
                exclude_tuple=exclude_tuple,
                source_filter=source_filter,
                hide_phd_student=hide_phd_student,
                apply_academic_filter=apply_academic_filter,
                dedupe_cross_source=dedupe_cross_source,
                use_tech_allowlist=use_tech_allowlist,
                include_tuple=include_tuple,
                urgency_days=urgency_days,
                text_query=text_query,
            )
            df, raw_count = _load_explorer_jobs_df(
                cache_key=cache_key,
                path_s=path_s,
                track=track,
                min_score=min_score,
                rogaland_only=rogaland_only,
                hide_applied=hide_applied,
                query_include_terms=query_include_terms,
                exclude_tuple=exclude_tuple,
                source_filter=source_filter,
                hide_phd_student=hide_phd_student,
                apply_academic_filter=apply_academic_filter,
                dedupe_cross_source=dedupe_cross_source,
                use_tech_allowlist=use_tech_allowlist,
                include_tuple=include_tuple,
                urgency_days=urgency_days,
                text_query=text_query,
            )

            explorer_chips = build_explorer_filter_chips(
                track=track,
                source_filter=source_filter,
                apply_academic_filter=apply_academic_filter,
                use_tech_allowlist=use_tech_allowlist,
                include_tuple=include_tuple,
                exclude_tuple=exclude_tuple,
                hide_phd_student=hide_phd_student,
                dedupe_cross_source=dedupe_cross_source,
                min_score=min_score,
                rogaland_only=rogaland_only,
                hide_applied=hide_applied,
                text_query=text_query,
            )
            render_filter_chips(explorer_chips)

            dedup_note = ""
            if dedupe_cross_source and raw_count > len(df):
                dedup_note = f"{raw_count} rader før kryss-kilde-dedup"
            soon_n = int(df["apply_soon"].sum()) if not df.empty and "apply_soon" in df.columns else 0
            render_results_header(
                n_results=len(df),
                text_query=text_query,
                soon_n=soon_n,
                urgency_days=urgency_days,
                dedup_note=dedup_note,
            )

            scroll_explorer_to_list = False
            if df.empty:
                st.info("Ingen treff. Prøv et annet søkeord, senk score-filteret, eller kjør `score_jobs.py`.")
            else:
                page_size = 20
                max_items = 200
                pagination_key = f"explorer_{track}"
                render_job_list_pagination(
                    len(df),
                    page_size=page_size,
                    max_items=max_items,
                    session_key=pagination_key,
                    position="top",
                )
                page_df, start = paginate_jobs_df(
                    df,
                    page_size=page_size,
                    max_items=max_items,
                    session_key=pagination_key,
                )
                scroll_explorer_to_list = _job_explorer_page_changed(pagination_key)

                st.markdown('<div class="job-card-list"></div>', unsafe_allow_html=True)
                for idx, (_, row) in enumerate(page_df.iterrows()):
                    render_compact_job_row(
                        conn,
                        row,
                        track=track,
                        key_prefix=f"exp_{start + idx}",
                        within_days=urgency_days,
                        db_path_s=path_s,
                    )

                if len(df) > page_size:
                    render_job_list_pagination(
                        len(df),
                        page_size=page_size,
                        max_items=max_items,
                        session_key=pagination_key,
                        position="bottom",
                    )

                with st.expander("Full data table (top 500)", expanded=False):
                    show = df.head(500).copy()
                    if "sources" in show.columns:
                        show = show.rename(columns={"sources": "Sources"})
                    elif "source" in show.columns:
                        show = show.rename(columns={"source": "Source"})
                    display_cols = [c for c in show.columns if c not in ("description_text", "apply_soon")]
                    st.dataframe(
                        show[display_cols],
                        column_config={
                            "Sources": st.column_config.TextColumn("Sources", width="small"),
                            "Source": st.column_config.TextColumn("Source", width="small"),
                            "duplicate_note": st.column_config.TextColumn("Also listed at", width="medium"),
                            "link": st.column_config.LinkColumn("Job link"),
                            "application_url": st.column_config.LinkColumn("Apply URL"),
                            "score_total": st.column_config.NumberColumn(format="%.1f"),
                            "score_base": st.column_config.NumberColumn(format="%.1f"),
                            "urgency": st.column_config.TextColumn("Urgency"),
                            "deadline": st.column_config.TextColumn("Deadline"),
                        },
                        hide_index=True,
                    )
            return scroll_explorer_to_list
    finally:
        active_scope = (st.session_state.get("_dashboard_debug_rerun_context") or {}).get("scope")
        if active_scope == "explorer_fragment":
            log_state_diff(st.session_state)
            finish_rerun_trace(st.session_state, note="explorer_fragment")


def _infer_page_rerun_reason() -> str:
    if st.session_state.get("apply_dialog_open") and _apply_dialog_fast_path_active():
        return "dialog_open"
    if _pipeline_poll_fast_path_active():
        return "pipeline_poll"
    if st.session_state.get("ingest_phase") == "queued":
        return "ingest"
    return "full_render"


def _infer_page_scope() -> str:
    reason = _infer_page_rerun_reason()
    if reason == "dialog_open":
        return "dialog_fast_path"
    if reason == "pipeline_poll":
        return "pipeline_poll_fast_path"
    return "main"


def main() -> None:
    st.set_page_config(page_title="Job search", layout="wide")
    configure_logging(console=False)
    init_dashboard_debug(st.session_state)
    rerun_reason = _infer_page_rerun_reason()
    rerun_scope = _infer_page_scope()
    start_rerun_trace(st.session_state, scope=rerun_scope, trigger=rerun_reason, force_new=True)
    _init_pipeline_session_state()
    _init_ingest_session_state()
    _init_refresh_session_state()
    st.session_state.pipeline_panel_rendered = False
    if "default_apply_prompts" not in st.session_state:
        st.session_state.default_apply_prompts = ""
    if "default_apply_language" not in st.session_state:
        st.session_state.default_apply_language = "en"

    _reconcile_apply_dialog_state()
    debug_log(
        "page_rerun",
        session_state=st.session_state,
        scope=rerun_scope,
        reason=rerun_reason,
    )

    conn = None
    try:
        with timing_span(
            "render_timing",
            session_state=st.session_state,
            label="main_render",
            scope=rerun_scope,
            trigger=rerun_reason,
        ):
            if _yield_to_apply_modify_dialog(source="main_fast_path"):
                render_debug_sidebar(st.session_state)
                return

            scroll_explorer_to_list = False
            _inject_dashboard_css()
            st.title("Job search")

            db_path = get_db_path()
            sidebar_path = st.sidebar.text_input("SQLite database", value=str(db_path))
            db_path = Path(sidebar_path).expanduser()
            path_s = str(db_path)

            render_ingest_sidebar_section(path_s)
            auto_refresh_minutes = render_auto_refresh_sidebar_section()
            render_debug_sidebar(st.session_state)

            if st.session_state.get("ingest_phase") == "queued":
                _execute_ingest_cycle()
            _show_ingest_result_panel()

            if not db_path.is_file():
                st.warning(f"Database not found: **{db_path}**. Run **Ingest & score** in the sidebar first.")
                st.code(".venv/bin/python scripts/run_job_search_cycle.py", language="bash")
                return

            conn = connect(db_path)
            init_schema(conn)

            st.sidebar.header("Track")
            if "cv_track" not in st.session_state:
                st.session_state.cv_track = "industry"
            track = st.sidebar.selectbox(
                "CV track",
                ["industry", "academic"],
                index=0 if st.session_state.cv_track == "industry" else 1,
                key="cv_track",
            )
            poll_pipeline_after_render = _render_pipeline_status_bar(track=track)
            _render_pipeline_completion_notice()
            prev_track = st.session_state.get("_dashboard_prev_cv_track")
            if prev_track != track:
                if track == "academic":
                    st.session_state.show_academic_roles_only = True
                st.session_state._dashboard_prev_cv_track = track

            with st.sidebar.expander("Filters", expanded=True):
                st.caption("Job explorer below has text search and a filter summary. Adjust defaults here.")
                if "show_academic_roles_only" not in st.session_state:
                    st.session_state.show_academic_roles_only = track == "academic"
                academic_roles_only = st.checkbox(
                    "Show academic roles only",
                    key="show_academic_roles_only",
                    help=(
                        "Display filter: postdoc, førstelektor, researcher, and similar titles. "
                        "Always on for **academic** CV track. Separate from **FINN: academic queries only** "
                        "under Refresh jobs (controls ingest)."
                    ),
                )
                apply_academic_filter = effective_academic_roles_only(
                    track=track,
                    academic_roles_only=academic_roles_only,
                )
                source_filter = st.selectbox(
                    "Source",
                    ["all", "nav_arbeidsplassen", "finn_no"],
                    index=0,
                    help="Filter jobs by ingest source (before cross-source deduplication).",
                )
                dedupe_cross_source = st.checkbox(
                    "Deduplicate cross-source listings",
                    value=DEFAULT_DEDUPE_CROSS_SOURCE,
                    help="Collapse NAV + FINN rows with the same employer and title; prefer NAV apply URL.",
                )
                hide_phd_student = st.checkbox(
                    "Hide PhD student openings",
                    value=True,
                    help="Filter out PhD fellowship / stipendiat ads; keeps postdoc and researcher roles.",
                )
                urgency_days = st.slider("Apply-soon window (days)", 1, 30, 7)
                st.markdown("**ICT / tech filter (allowlist)**")
                use_tech_allowlist = st.checkbox(
                    "Only show ads matching ICT / AI / CS vocabulary",
                    value=True,
                    help="Requires ≥1 hit from `job_filters.DEFAULT_TECH_INCLUDE_TERMS` (+ your extras). "
                    "Finite list — turn off to see everything.",
                )
                use_tech_defaults = st.checkbox(
                    "Use built-in tech term set",
                    value=True,
                    disabled=not use_tech_allowlist,
                )
                extra_include = st.text_area(
                    "Extra required terms (comma or newline)",
                    height=60,
                    placeholder="kotlin, MLOps, offshore wind IT",
                    disabled=not use_tech_allowlist,
                )
                st.markdown("**Optional noise filter**")
                use_noise_defaults = st.checkbox(
                    "Also hide typical non-tech roles (chef, nurse, kundeservice, ...)",
                    value=True,
                    help="Secondary blocklist after the allowlist (retail, medicine, finance controller, ...).",
                )
                extra_exclude = st.text_area(
                    "Extra words to hide (comma or newline)",
                    height=50,
                    placeholder="assistent, truck, forklift",
                )

            with st.sidebar.expander("Apply defaults", expanded=False):
                st.radio(
                    "Application language",
                    options=("en", "no"),
                    format_func=lambda code: APPLY_LANGUAGE_LABELS[code],
                    key="default_apply_language",
                    help="Pre-fills the Apply / Modify dialog. Norwegian adds final_cv_no.md and cover_letter_no.md.",
                )
                st.text_area(
                    "Default tailoring instructions (optional)",
                    height=80,
                    key="default_apply_prompts",
                    placeholder="e.g. mention Rogaland relocation; keep cloud mentions moderate",
                    help="Pre-fills the Apply / Modify dialog and is merged with per-role custom prompts.",
                )

            include_tuple: tuple[str, ...] = ()
            if use_tech_allowlist:
                include_tuple = merge_include_terms(use_tech_defaults, extra_include)
                if include_tuple:
                    st.sidebar.caption(f"{len(include_tuple)} allowlist tokens active.")
                else:
                    st.sidebar.warning("Allowlist on but no terms — showing all jobs.")
            exclude_tuple = merge_exclude_terms(use_noise_defaults, extra_exclude)
            if exclude_tuple:
                st.sidebar.caption(f"{len(exclude_tuple)} blocklist terms active.")
            query_include_terms = () if apply_academic_filter else include_tuple

            overview_metrics_fingerprint = short_fingerprint(
                {"db": path_s, "track": track, "urgency_days": urgency_days}
            )
            before_metrics_calls = _cache_exec_count("load_overview_metrics")
            with timing_span(
                "data_load_timing",
                session_state=st.session_state,
                label="overview_metrics",
                scope="main",
                fingerprint=overview_metrics_fingerprint,
            ):
                metrics = load_overview_metrics(path_s, track, urgency_days)
            _log_cache_probe(
                "load_overview_metrics",
                fingerprint=overview_metrics_fingerprint,
                hit=_cache_exec_count("load_overview_metrics") == before_metrics_calls,
                rows=int(metrics.get("n_active") or 0),
                scope="main",
            )

            n_apps = int(metrics["n_apps"])
            n_active = int(metrics["n_active"])
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Active jobs", n_active)
            m2.metric("Apply soon", metrics["apply_soon_count"])
            m3.metric("Rogaland matches", metrics["n_rogaland"])
            m4.metric("Applications", n_apps)

            with st.expander("More stats", expanded=False):
                n_jobs = int(pd.read_sql("SELECT COUNT(*) AS n FROM job_postings", conn)["n"].iloc[0])
                s1, s2, s3 = st.columns(3)
                s1.metric("Score rows (active)", metrics["n_scored"])
                s2.metric("All DB rows", n_jobs)
                s3.metric("Apply-soon window", f"{urgency_days}d")
                source_active = metrics["source_active"]
                if not source_active.empty:
                    st.caption(
                        "Active by source: "
                        + ", ".join(f"{row['source']} {int(row['n'])}" for _, row in source_active.iterrows())
                    )
                track_split = metrics["track_split"]
                if not track_split.empty:
                    split_txt = ", ".join(f"{row['track']} {int(row['n'])}" for _, row in track_split.iterrows())
                    st.caption(f"Scored active jobs by track: {split_txt}")

            overview_bundle_fingerprint = short_fingerprint(
                {
                    "db": path_s,
                    "track": track,
                    "query_include_terms": query_include_terms,
                    "exclude_tuple": exclude_tuple,
                    "source_filter": source_filter,
                    "hide_phd_student": hide_phd_student,
                    "apply_academic_filter": apply_academic_filter,
                }
            )
            before_bundle_calls = _cache_exec_count("load_overview_jobs_bundle")
            with timing_span(
                "data_load_timing",
                session_state=st.session_state,
                label="overview_jobs_bundle",
                scope="main",
                fingerprint=overview_bundle_fingerprint,
            ):
                relevant_raw, newest_raw, rogaland_raw = load_overview_jobs_bundle(
                    path_s,
                    track,
                    query_include_terms,
                    exclude_tuple,
                    source_filter,
                    hide_phd_student,
                    apply_academic_filter,
                )
            _log_cache_probe(
                "load_overview_jobs_bundle",
                fingerprint=overview_bundle_fingerprint,
                hit=_cache_exec_count("load_overview_jobs_bundle") == before_bundle_calls,
                rows=len(relevant_raw) + len(newest_raw) + len(rogaland_raw),
                raw_rows=len(relevant_raw) + len(newest_raw) + len(rogaland_raw),
                scope="main",
            )

            if dedupe_cross_source:
                relevant_raw = dedupe_jobs_df(relevant_raw)
                newest_raw = dedupe_jobs_df(newest_raw)
                rogaland_raw = dedupe_jobs_df(rogaland_raw)

            filter_kwargs = dict(
                use_tech_allowlist=use_tech_allowlist and not apply_academic_filter,
                include_terms=include_tuple,
                exclude_terms=exclude_tuple,
                hide_phd_student=hide_phd_student,
                academic_roles_only=apply_academic_filter,
            )
            profile_filter_kwargs = {**filter_kwargs, "require_profile_match": True}
            newest_raw = apply_dashboard_filters(newest_raw, require_profile_match=False, **filter_kwargs)
            rogaland_raw = apply_dashboard_filters(
                rogaland_raw,
                rogaland_only=True,
                **profile_filter_kwargs,
            )

            _log_dashboard_filter_state(
                track=track,
                academic_roles_only=apply_academic_filter,
                stage="overview_relevant_sql",
                count_before=len(relevant_raw),
            )
            _render_overview_fragment(
                conn,
                track=track,
                within_days=urgency_days,
                path_s=path_s,
                apply_academic_filter=apply_academic_filter,
                relevant_raw=relevant_raw,
                newest_raw=newest_raw,
                rogaland_raw=rogaland_raw,
                profile_filter_kwargs=profile_filter_kwargs,
            )

            render_applied_roles_section(conn, path_s=path_s, track=track)

            with st.expander("Charts", expanded=False):
                oc1, oc2 = st.columns(2)
                with oc1:
                    dist = pd.read_sql(
                        """
                        SELECT CASE WHEN location_matched = 1 THEN 'Preferred location' ELSE 'Other / unknown' END AS region, COUNT(*) AS n
                        FROM job_postings WHERE status IS NULL OR UPPER(status) = 'ACTIVE'
                        GROUP BY 1
                        """,
                        conn,
                    )
                    if not dist.empty:
                        st.subheader("Active jobs by preferred-location flag")
                        st.bar_chart(dist.set_index("region"))

                with oc2:
                    st.subheader("Applications by status")
                    ac = pd.read_sql(
                        "SELECT status, COUNT(*) AS n FROM applications GROUP BY status ORDER BY n DESC",
                        conn,
                    )
                    if not ac.empty:
                        st.bar_chart(ac.set_index("status"))
                    else:
                        st.caption("No rows in `applications` yet.")

                score_band = pd.read_sql(
                    """
                    SELECT CASE
                        WHEN s.score_total < 15 THEN '0-14'
                        WHEN s.score_total < 30 THEN '15-29'
                        WHEN s.score_total < 50 THEN '30-49'
                        WHEN s.score_total < 75 THEN '50-74'
                        ELSE '75+'
                    END AS band, COUNT(*) AS n
                    FROM job_scores s
                    JOIN job_postings j ON j.uuid = s.uuid AND j.source = s.source
                    WHERE s.track = ? AND (j.status IS NULL OR UPPER(j.status) = 'ACTIVE')
                    GROUP BY band
                    ORDER BY band
                    """,
                    conn,
                    params=(track,),
                )
                if not score_band.empty:
                    st.subheader(f"Score_total bands ({track})")
                    st.bar_chart(score_band.set_index("band"))

            st.divider()
            scroll_explorer_to_list = _render_job_explorer_fragment(
                conn,
                path_s=path_s,
                track=track,
                query_include_terms=query_include_terms,
                exclude_tuple=exclude_tuple,
                source_filter=source_filter,
                hide_phd_student=hide_phd_student,
                apply_academic_filter=apply_academic_filter,
                dedupe_cross_source=dedupe_cross_source,
                use_tech_allowlist=use_tech_allowlist,
                include_tuple=include_tuple,
                urgency_days=urgency_days,
            )
            explorer_df = st.session_state.get(_EXPLORER_JOBS_CACHE_DF)
            if not isinstance(explorer_df, pd.DataFrame):
                explorer_df = pd.DataFrame()

            st.divider()
            with st.expander("Log / update application", expanded=False):
                st.caption("Creates or updates `applications` for one job UUID and track.")

                if not explorer_df.empty:
                    options = explorer_df.head(200)
                    labels = [
                        f"{row['score_total']:.0f} | [{source_label_short(_safe_str(row.get('sources')) or _safe_str(row.get('source')))}] "
                        f"{row['title'][:55]} — {row['employer_name'] or '—'}"[:140]
                        for _, row in options.iterrows()
                    ]
                    pick = st.selectbox(
                        "Pick from current explorer list (top 200)",
                        range(len(labels)),
                        format_func=lambda i: labels[i],
                    )
                    row = options.iloc[pick]
                    default_uuid = str(row["uuid"])
                    default_source = str(row["source"])
                    default_track = track
                else:
                    default_uuid = ""
                    default_source = "nav_arbeidsplassen"
                    default_track = track

                with st.form("app_form"):
                    col_a, col_b = st.columns(2)
                    uuid_in = col_a.text_input("Job uuid", value=default_uuid)
                    source_in = col_b.text_input("Source", value=default_source)
                    track_in = st.selectbox(
                        "Track",
                        ["industry", "academic"],
                        index=0 if default_track == "industry" else 1,
                    )
                    status_in = st.selectbox("Status", STATUS_OPTIONS, index=STATUS_OPTIONS.index("interested"))
                    notes_in = st.text_area("Notes", height=80)
                    cover_in = st.text_input("Cover letter file path (optional)", "")
                    applied_in = st.text_input("Applied at (ISO date optional, e.g. 2026-04-08)", "")
                    follow_in = st.text_input("Follow-up reminder (ISO date optional)", "")
                    submitted = st.form_submit_button("Save application row")

                if submitted:
                    if not uuid_in.strip():
                        st.error("UUID required.")
                    else:
                        now = utc_now_iso()
                        upsert_application(
                            conn,
                            {
                                "uuid": uuid_in.strip(),
                                "source": (source_in.strip() or "nav_arbeidsplassen"),
                                "track": track_in,
                                "status": status_in,
                                "notes": notes_in.strip() or None,
                                "cover_letter_path": cover_in.strip() or None,
                                "applied_at": applied_in.strip() or None,
                                "follow_up_at": follow_in.strip() or None,
                                "updated_at": now,
                            },
                        )
                        conn.commit()
                        _invalidate_dashboard_data_caches()
                        conn.close()
                        conn = None
                        st.success("Saved.")
                        st.rerun()

                st.divider()
                st.caption("Remove application tracking (SQLite row only; CV run folders stay on disk).")
                del_uuid = st.text_input("Delete — job uuid", value=default_uuid, key="delete_app_uuid")
                del_col_a, del_col_b = st.columns(2)
                del_source = del_col_a.text_input(
                    "Delete — source",
                    value=default_source,
                    key="delete_app_source",
                )
                del_track = del_col_b.selectbox(
                    "Delete — track",
                    ["industry", "academic"],
                    index=0 if default_track == "industry" else 1,
                    key="delete_app_track",
                )
                del_btn_col, _ = st.columns(LOG_DELETE_BUTTON_COLUMNS)
                with del_btn_col:
                    render_delete_application_popover(
                        conn,
                        uuid=del_uuid,
                        source=del_source,
                        track=del_track,
                        key_prefix="log_delete_app",
                    )

            render_pipeline_panel_fallback(conn, track=track)
            render_apply_modify_popover_fallback(conn, track=track)
            maybe_open_apply_modify_dialog()
            _maybe_periodic_data_refresh(auto_refresh_minutes)
            _finalize_dashboard_scroll(scroll_to_list=scroll_explorer_to_list)
            if poll_pipeline_after_render and not st.session_state.get("apply_dialog_open"):
                time.sleep(PIPELINE_POLL_SECONDS)
                st.rerun()
    finally:
        if conn is not None:
            conn.close()
        log_state_diff(st.session_state)
        finish_rerun_trace(st.session_state, note=rerun_scope)


if __name__ == "__main__":
    main()
