"""In-process ingest and apply-pipeline workers for the FastAPI UI."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from job_search.web.services import (
    PIPELINE_LOG_MAX_LINES,
    PIPELINE_MAX_IN_FLIGHT,
    PIPELINE_MAX_WAITING,
    ApplyPipelineOptions,
    IngestCycleOptions,
    _ingest_failure_headline,
    _pipeline_worker_entry,
    _start_pipeline_worker,
    apply_pipeline_options_from_mapping,
    build_ingest_cycle_command,
    build_pipeline_queue_item,
    can_enqueue_pipeline,
    dequeue_pipeline_item,
    enqueue_pipeline_item,
    get_db_path,
    ingest_active_source_counts,
    parse_ingest_cycle_output,
    pipeline_job_display_title,
    pipeline_phase_is_busy,
    pipeline_queue_display_titles,
    run_ingest_cycle_subprocess,
)

_INGEST_ATTR = "_job_search_web_ingest_v1"
_QUEUE_ATTR = "_job_search_web_pipeline_queue_v1"


def _ingest_registry() -> dict[str, Any]:
    import sys

    reg = getattr(sys, _INGEST_ATTR, None)
    if not isinstance(reg, dict) or "lock" not in reg:
        reg = {
            "lock": threading.RLock(),
            "phase": None,
            "elapsed": 0.0,
            "started_at": None,
            "log_lines": [],
            "result": None,
            "options": None,
            "thread_alive": False,
        }
        setattr(sys, _INGEST_ATTR, reg)
    return reg


def _queue_registry() -> dict[str, Any]:
    import sys

    reg = getattr(sys, _QUEUE_ATTR, None)
    if not isinstance(reg, dict) or "lock" not in reg:
        reg = {
            "lock": threading.RLock(),
            "queue": [],
            "active_key": None,
            "active_params": None,
        }
        setattr(sys, _QUEUE_ATTR, reg)
    return reg


def ingest_running() -> bool:
    store = _ingest_registry()
    with store["lock"]:
        return store.get("phase") in ("queued", "running")


def ingest_snapshot() -> dict[str, Any]:
    store = _ingest_registry()
    with store["lock"]:
        result = dict(store.get("result") or {}) if store.get("result") else None
        lines = list(store.get("log_lines") or [])
        phase = store.get("phase")
        started_at = store.get("started_at")
        elapsed = float(store.get("elapsed") or 0.0)
        if phase in ("queued", "running") and isinstance(started_at, (int, float)):
            elapsed = time.monotonic() - float(started_at)
            store["elapsed"] = elapsed
        options = dict(store.get("options") or {}) if store.get("options") else {}
    headline = None
    if phase == "error" and result:
        headline = _ingest_failure_headline(result)
    step = None
    for line in reversed(lines):
        if "[job-search]" in line:
            step = line.strip()
            break
    return {
        "phase": phase,
        "elapsed": round(elapsed, 1),
        "log_lines": lines[-80:],
        "result": result,
        "options": options,
        "headline": headline,
        "step": step,
        "running": phase in ("queued", "running"),
    }


def start_ingest(
    *,
    skip_nav: bool = False,
    skip_finn: bool = False,
    skip_jobbnorge: bool = False,
    academic_queries_only: bool = False,
    db_path: str | None = None,
) -> tuple[bool, str]:
    if ingest_running():
        return False, "Ingest is already running."
    if pipeline_busy():
        return False, "An Apply pipeline is running — wait until it finishes."
    options = IngestCycleOptions(
        skip_nav=skip_nav,
        skip_finn=skip_finn,
        skip_jobbnorge=skip_jobbnorge,
        academic_queries_only=academic_queries_only,
        db_path=(db_path or "").strip() or None,
    )
    store = _ingest_registry()
    with store["lock"]:
        store["phase"] = "running"
        store["elapsed"] = 0.0
        store["started_at"] = time.monotonic()
        store["log_lines"] = []
        store["result"] = None
        store["options"] = {
            "skip_nav": options.skip_nav,
            "skip_finn": options.skip_finn,
            "skip_jobbnorge": options.skip_jobbnorge,
            "academic_queries_only": options.academic_queries_only,
            "db_path": options.db_path,
        }
        store["thread_alive"] = True

    def _worker() -> None:
        cmd = build_ingest_cycle_command(
            skip_nav=options.skip_nav,
            skip_finn=options.skip_finn,
            skip_jobbnorge=options.skip_jobbnorge,
            academic_queries_only=options.academic_queries_only,
            db_path=options.db_path,
        )
        started = time.monotonic()
        log_lines: list[str] = []

        def _on_line(line: str) -> None:
            log_lines.append(line)
            with store["lock"]:
                store["log_lines"] = log_lines[-PIPELINE_LOG_MAX_LINES:]
                store["elapsed"] = time.monotonic() - started

        try:
            code, stdout, stderr = run_ingest_cycle_subprocess(cmd, on_line=_on_line)
            elapsed = time.monotonic() - started
            parsed = parse_ingest_cycle_output(stdout)
            summary: dict[str, Any] = {
                "exit_code": code,
                "duration_seconds": round(elapsed, 1),
                "command": cmd,
                "steps": parsed.get("steps") or {},
                "stdout_tail": "\n".join(log_lines[-40:]) if log_lines else stdout,
                "stderr": stderr,
            }
            if code == 0:
                from job_search.web.services import clear_explorer_jobs_cache

                clear_explorer_jobs_cache()
                db = Path(options.db_path) if options.db_path else get_db_path()
                if db.is_file():
                    summary["active_counts"] = ingest_active_source_counts(db)
                phase = "complete"
            else:
                phase = "error"
            with store["lock"]:
                store["elapsed"] = elapsed
                store["started_at"] = None
                store["result"] = summary
                store["phase"] = phase
                store["log_lines"] = log_lines[-PIPELINE_LOG_MAX_LINES:]
        except Exception as exc:  # noqa: BLE001
            with store["lock"]:
                store["phase"] = "error"
                store["started_at"] = None
                store["result"] = {
                    "exit_code": 1,
                    "duration_seconds": round(time.monotonic() - started, 1),
                    "command": [],
                    "steps": {},
                    "stdout_tail": "",
                    "stderr": str(exc),
                }
        finally:
            with store["lock"]:
                store["thread_alive"] = False
                store["started_at"] = None

    threading.Thread(target=_worker, name="job-search-ingest", daemon=True).start()
    return True, ""


def dismiss_ingest() -> None:
    store = _ingest_registry()
    with store["lock"]:
        if store.get("phase") in ("complete", "error"):
            store["phase"] = None
            store["result"] = None
            store["log_lines"] = []


def pipeline_busy() -> bool:
    snap = pipeline_snapshot()
    return bool(snap.get("running") or snap.get("queue"))


def _active_worker_snapshot(job_key: str | None) -> dict[str, Any] | None:
    if not job_key:
        return None
    store = _pipeline_worker_entry(job_key)
    if store is None:
        return None
    with store["lock"]:
        return {
            "phase": store.get("phase"),
            "stage": store.get("stage"),
            "elapsed": float(store.get("elapsed") or 0.0),
            "log_lines": list(store.get("log_lines") or []),
            "result": dict(store.get("result") or {}) if store.get("result") else None,
        }


def pipeline_snapshot() -> dict[str, Any]:
    _maybe_advance_queue()
    qreg = _queue_registry()
    with qreg["lock"]:
        queue = [dict(item) for item in qreg.get("queue") or []]
        active_key = qreg.get("active_key")
        params = dict(qreg.get("active_params") or {}) if qreg.get("active_params") else {}
    worker = _active_worker_snapshot(active_key)
    phase = (worker or {}).get("phase") if worker else None
    running = pipeline_phase_is_busy(phase) if phase else False
    title = pipeline_job_display_title(params.get("title"), params.get("employer")) if params else None
    return {
        "running": running,
        "phase": phase,
        "stage": (worker or {}).get("stage"),
        "elapsed": round(float((worker or {}).get("elapsed") or 0.0), 1),
        "job_key": active_key,
        "title": title,
        "log_lines": (worker or {}).get("log_lines") or [],
        "result": (worker or {}).get("result"),
        "queue": pipeline_queue_display_titles(queue),
        "queue_len": len(queue),
        "params": params,
        "ingest_running": ingest_running(),
    }


def _maybe_advance_queue() -> None:
    qreg = _queue_registry()
    with qreg["lock"]:
        active_key = qreg.get("active_key")
        worker = _active_worker_snapshot(str(active_key)) if active_key else None
        still_running = bool(active_key) and (
            worker is None or worker.get("phase") in ("queued", "running")
        )
        if still_running:
            return
        waiting, item = dequeue_pipeline_item(qreg.get("queue") or [])
        qreg["queue"] = waiting
        if item is None:
            return
        _activate_item(item)


def _activate_item(item: dict[str, Any]) -> None:
    qreg = _queue_registry()
    job_key = str(item.get("job_key") or "")
    row_dict = item.get("row_dict") if isinstance(item.get("row_dict"), dict) else {}
    track = str(item.get("track") or "industry")
    options = apply_pipeline_options_from_mapping(item.get("options"))
    db_path = get_db_path()
    qreg["active_key"] = job_key
    qreg["active_params"] = {
        "title": item.get("title"),
        "employer": item.get("employer"),
        "track": track,
        "job_key": job_key,
    }
    _start_pipeline_worker(
        job_key,
        db_path=db_path,
        row_dict=row_dict,
        track=track,
        options=options,
    )


def enqueue_or_start_apply(
    *,
    job_key: str,
    row_dict: dict[str, Any],
    track: str,
    options: ApplyPipelineOptions | dict[str, Any] | None,
) -> tuple[bool, str, bool]:
    """Start immediately or enqueue. Returns ``(ok, reason, started_now)``."""
    qreg = _queue_registry()
    with qreg["lock"]:
        queue = [dict(item) for item in qreg.get("queue") or []]
        active_key = qreg.get("active_key")
        worker = _active_worker_snapshot(str(active_key)) if active_key else None
        has_active = bool(active_key) and (
            worker is None or worker.get("phase") in ("queued", "running")
        )
        ok, reason = can_enqueue_pipeline(
            has_active=has_active,
            active_job_key=active_key,
            queue=queue,
            job_key=job_key,
            ingest_running=ingest_running(),
            max_in_flight=PIPELINE_MAX_IN_FLIGHT,
        )
        if not ok:
            return False, reason, False
        item = build_pipeline_queue_item(job_key, row_dict, track=track, options=options)
        if not has_active:
            _activate_item(item)
            return True, "", True
        waiting, queued, qreason = enqueue_pipeline_item(
            queue, item, max_waiting=PIPELINE_MAX_WAITING
        )
        if not queued:
            return False, qreason, False
        qreg["queue"] = waiting
        return True, "", False
