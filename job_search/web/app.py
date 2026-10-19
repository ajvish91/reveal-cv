"""FastAPI app for the Bootstrap job-search UI."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cv_generation.apply_prompts import APPLY_LANGUAGE_LABELS, merge_apply_prompts
from job_search.job_db import connect, delete_application, init_schema, upsert_application, utc_now_iso
from job_search.job_filters import merge_exclude_terms, merge_include_terms
from job_search.logging_config import configure_logging, tail_log_file
from job_search.web import cv_sources, runtime
from job_search.web.services import (
    DEFAULT_APPLIED_STATUS_FILTER,
    DEFAULT_DEDUPE_CROSS_SOURCE,
    DEFAULT_HIDE_APPLIED,
    DEFAULT_HIDE_EXPIRED,
    QUICK_JOB_ACTIONS,
    STATUS_OPTIONS,
    ApplyPipelineOptions,
    _dialog_artifact_bundle,
    apply_job_quick_action,
    apply_pipeline_options_from_mapping,
    best_job_url,
    build_explorer_filter_chips,
    bulk_deanonymize_command,
    clear_explorer_jobs_cache,
    count_research_roles_in_db,
    effective_academic_roles_only,
    existing_artifact_flags,
    extract_run_ids_from_notes,
    fetch_job_posting,
    filter_applied_roles_df,
    format_job_export_text,
    get_db_path,
    is_modify_mode,
    job_row_payload,
    json_ready,
    load_applied_roles_df,
    load_explorer_jobs_df,
    load_overview_frames,
    load_overview_metrics,
    pipeline_metrics_summary_for_notes,
    resolve_modify_run_dir,
    row_dict_for_apply_from_app,
    source_label_short,
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
PAGE_SIZE_DEFAULT = 25
OVERVIEW_PREVIEW = 5

configure_logging(console=False)
app = FastAPI(title="Job search", version="0.2.0")


@app.middleware("http")
async def ignore_stale_streamlit_probes(request: Request, call_next):
    """Old Streamlit tabs keep polling ``/_stcore/*`` on whatever used to be :8501."""
    if "/_stcore/" in request.url.path:
        return Response(status_code=204)
    return await call_next(request)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class IngestRequest(BaseModel):
    skip_nav: bool = False
    skip_finn: bool = False
    skip_jobbnorge: bool = False
    academic_queries_only: bool = False


class ApplyRequest(BaseModel):
    uuid: str
    source: str
    track: str = "industry"
    language: str = "en"
    apply_prompts: str | None = None
    generate_cover_letter: bool = True
    generate_application_letter: bool = False
    generate_research_proposal: bool = False
    overwrite_cv: bool = False
    overwrite_cover_letter: bool = False
    overwrite_application_letter: bool = False
    overwrite_research_proposal: bool = False
    default_apply_prompts: str | None = None


class ApplicationPatch(BaseModel):
    track: str
    status: str | None = None
    notes: str | None = Field(default=None)
    pinned: bool | None = None


class JobQuickActionRequest(BaseModel):
    track: str = "industry"
    action: str


class CvSaveRequest(BaseModel):
    source_id: str | None = None
    slug: str | None = None
    identity: dict[str, Any] = Field(default_factory=dict)
    industry: dict[str, Any] | None = None
    academic: dict[str, Any] | None = None
    activate: dict[str, bool] | None = None


class CvActivateRequest(BaseModel):
    track: str
    source_id: str | None = None


class CvPreviewRequest(BaseModel):
    identity: dict[str, Any] = Field(default_factory=dict)
    industry: dict[str, Any] | None = None
    academic: dict[str, Any] | None = None


class CvSaveMappingRequest(BaseModel):
    mapping: dict[str, Any] = Field(default_factory=dict)


def _bool_query(value: bool | None, default: bool) -> bool:
    return default if value is None else bool(value)


def _db_path() -> Path:
    return get_db_path()


def _require_db() -> Path:
    path = _db_path()
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Database not found: {path}. Run Ingest & score first.",
        )
    return path


def _resolved_filters(
    *,
    track: str,
    academic_roles_only: bool | None,
    extra_include: str,
    extra_exclude: str,
    use_tech_allowlist: bool,
    use_tech_defaults: bool,
    use_noise_defaults: bool,
) -> dict[str, Any]:
    track = track if track in ("industry", "academic") else "industry"
    apply_academic = effective_academic_roles_only(
        track=track,
        academic_roles_only=_bool_query(academic_roles_only, track == "academic"),
    )
    include_tuple: tuple[str, ...] = ()
    if use_tech_allowlist:
        include_tuple = merge_include_terms(use_tech_defaults, extra_include)
    exclude_tuple = merge_exclude_terms(use_noise_defaults, extra_exclude)
    query_include = () if apply_academic else include_tuple
    return {
        "track": track,
        "apply_academic_filter": apply_academic,
        "include_tuple": include_tuple,
        "exclude_tuple": exclude_tuple,
        "query_include_terms": query_include,
        "use_tech_allowlist": use_tech_allowlist,
    }


def _job_key(source: str, uuid: str) -> str:
    return f"{source}:{uuid}"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/cv")
def cv_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "cv.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    path = _db_path()
    return {"ok": True, "db": str(path), "db_exists": path.is_file()}


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    return {
        "tracks": ["industry", "academic"],
        "status_options": STATUS_OPTIONS,
        "quick_actions": list(QUICK_JOB_ACTIONS),
        "language_labels": APPLY_LANGUAGE_LABELS,
        "defaults": {
            "hide_applied": DEFAULT_HIDE_APPLIED,
            "hide_expired": DEFAULT_HIDE_EXPIRED,
            "dedupe_cross_source": DEFAULT_DEDUPE_CROSS_SOURCE,
            "hide_phd_student": True,
            "use_tech_allowlist": True,
            "use_tech_defaults": True,
            "use_noise_defaults": True,
            "page_size": PAGE_SIZE_DEFAULT,
        },
        "db": str(_db_path()),
        "db_exists": _db_path().is_file(),
    }


@app.get("/api/overview")
def overview(
    track: str = Query("industry"),
    source: str = Query("all"),
    academic_roles_only: bool | None = Query(None),
    hide_phd_student: bool = Query(True),
    dedupe_cross_source: bool = Query(DEFAULT_DEDUPE_CROSS_SOURCE),
    use_tech_allowlist: bool = Query(True),
    use_tech_defaults: bool = Query(True),
    extra_include: str = Query(""),
    use_noise_defaults: bool = Query(True),
    extra_exclude: str = Query(""),
    urgency_days: int = Query(7, ge=1, le=30),
    min_score: float | None = Query(None),
) -> dict[str, Any]:
    path = _require_db()
    resolved = _resolved_filters(
        track=track,
        academic_roles_only=academic_roles_only,
        extra_include=extra_include,
        extra_exclude=extra_exclude,
        use_tech_allowlist=use_tech_allowlist,
        use_tech_defaults=use_tech_defaults,
        use_noise_defaults=use_noise_defaults,
    )
    metrics = load_overview_metrics(str(path), resolved["track"], urgency_days)
    overview_min = min_score
    if overview_min is None:
        overview_min = 0.0 if resolved["track"] == "academic" else 15.0
    relevant, newest = load_overview_frames(
        path_s=str(path),
        track=resolved["track"],
        source_filter=source,
        hide_phd_student=hide_phd_student,
        dedupe_cross_source=dedupe_cross_source,
        use_tech_allowlist=resolved["use_tech_allowlist"],
        include_tuple=resolved["include_tuple"],
        exclude_tuple=resolved["exclude_tuple"],
        apply_academic_filter=resolved["apply_academic_filter"],
        query_include_terms=resolved["query_include_terms"],
        urgency_days=urgency_days,
        min_score=float(overview_min),
    )
    research_n = (
        count_research_roles_in_db(str(path)) if resolved["apply_academic_filter"] else 0
    )
    source_active = json_ready(metrics.get("source_active"))
    track_split = json_ready(metrics.get("track_split"))
    return {
        "metrics": {
            "n_active": int(metrics["n_active"]),
            "apply_soon_count": int(metrics["apply_soon_count"]),
            "n_apps": int(metrics["n_apps"]),
            "n_scored": int(metrics["n_scored"]),
            "source_active": source_active,
            "track_split": track_split,
            "research_roles": research_n,
        },
        "relevant": [job_row_payload(row, within_days=urgency_days) for _, row in relevant.head(OVERVIEW_PREVIEW).iterrows()],
        "relevant_count": len(relevant),
        "newest": [job_row_payload(row, within_days=urgency_days) for _, row in newest.head(OVERVIEW_PREVIEW).iterrows()],
        "newest_count": len(newest),
        "min_score": float(overview_min),
        "track": resolved["track"],
        "academic_roles_only": resolved["apply_academic_filter"],
    }


@app.get("/api/jobs")
def list_jobs(
    track: str = Query("industry"),
    q: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(PAGE_SIZE_DEFAULT, ge=1, le=100),
    min_score: float = Query(0.0),
    source: str = Query("all"),
    hide_applied: bool = Query(DEFAULT_HIDE_APPLIED),
    hide_expired: bool = Query(DEFAULT_HIDE_EXPIRED),
    academic_roles_only: bool | None = Query(None),
    rogaland_only: bool = Query(False),
    hide_phd_student: bool = Query(True),
    dedupe_cross_source: bool = Query(DEFAULT_DEDUPE_CROSS_SOURCE),
    use_tech_allowlist: bool = Query(True),
    use_tech_defaults: bool = Query(True),
    extra_include: str = Query(""),
    use_noise_defaults: bool = Query(True),
    extra_exclude: str = Query(""),
    urgency_days: int = Query(7, ge=1, le=30),
    order_by: str = Query("score", pattern="^(score|published|location)$"),
) -> dict[str, Any]:
    path = _require_db()
    resolved = _resolved_filters(
        track=track,
        academic_roles_only=academic_roles_only,
        extra_include=extra_include,
        extra_exclude=extra_exclude,
        use_tech_allowlist=use_tech_allowlist,
        use_tech_defaults=use_tech_defaults,
        use_noise_defaults=use_noise_defaults,
    )
    df, raw_count = load_explorer_jobs_df(
        path_s=str(path),
        track=resolved["track"],
        min_score=min_score,
        rogaland_only=rogaland_only,
        hide_applied=hide_applied,
        hide_expired=hide_expired,
        query_include_terms=resolved["query_include_terms"],
        exclude_tuple=resolved["exclude_tuple"],
        source_filter=source,
        hide_phd_student=hide_phd_student,
        apply_academic_filter=resolved["apply_academic_filter"],
        dedupe_cross_source=dedupe_cross_source,
        use_tech_allowlist=resolved["use_tech_allowlist"],
        include_tuple=resolved["include_tuple"],
        urgency_days=urgency_days,
        text_query=q,
        order_by=order_by,
    )
    total = len(df)
    start = (page - 1) * page_size
    page_df = df.iloc[start : start + page_size]
    chips = build_explorer_filter_chips(
        track=resolved["track"],
        source_filter=source,
        apply_academic_filter=resolved["apply_academic_filter"],
        use_tech_allowlist=resolved["use_tech_allowlist"],
        include_tuple=resolved["include_tuple"],
        exclude_tuple=resolved["exclude_tuple"],
        hide_phd_student=hide_phd_student,
        dedupe_cross_source=dedupe_cross_source,
        min_score=min_score,
        rogaland_only=rogaland_only,
        hide_applied=hide_applied,
        hide_expired=hide_expired,
        text_query=q,
        order_by=order_by,
    )
    return {
        "total": total,
        "raw_count": raw_count,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size) if total else 1,
        "chips": chips,
        "jobs": [job_row_payload(row, within_days=urgency_days) for _, row in page_df.iterrows()],
    }


@app.get("/api/jobs/{source}/{uuid}")
def job_detail(source: str, uuid: str, track: str = Query("industry"), urgency_days: int = Query(7)) -> dict[str, Any]:
    path = _require_db()
    conn = connect(path)
    init_schema(conn)
    try:
        row = fetch_job_posting(conn, uuid, source)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found.")
        score = conn.execute(
            """
            SELECT score_total, score_base, boost_rogaland, boost_tek,
                   matched_keywords, matched_skills, tek_match_name
            FROM job_scores WHERE uuid = ? AND source = ? AND track = ?
            """,
            (uuid, source, track),
        ).fetchone()
        app_row = conn.execute(
            """
            SELECT status, notes, cover_letter_path, applied_at, updated_at, COALESCE(pinned, 0) AS pinned
            FROM applications WHERE uuid = ? AND source = ? AND track = ?
            """,
            (uuid, source, track),
        ).fetchone()
        merged = dict(row)
        if score:
            merged.update(dict(score))
        if app_row:
            merged["app_status"] = app_row["status"]
            merged["app_notes"] = app_row["notes"]
            merged["cover_letter_path"] = app_row["cover_letter_path"]
            merged["pinned"] = app_row["pinned"]
        payload = job_row_payload(merged, within_days=urgency_days)
        payload["description_text"] = row.get("description_text") or ""
        payload["export_text"] = format_job_export_text(merged)
        payload["job_url"] = best_job_url(merged)
        # Do not auto-fetch FINN detail pages here — bulk/on-open scraping gets throttled.
        payload["deadline_unknown"] = source == "finn_no" and not (
            str(merged.get("expires") or "").strip()
        )
        return payload
    finally:
        conn.close()


@app.get("/api/jobs/{source}/{uuid}/apply-defaults")
def apply_defaults(source: str, uuid: str, track: str = Query("industry")) -> dict[str, Any]:
    path = _require_db()
    conn = connect(path)
    init_schema(conn)
    try:
        row = fetch_job_posting(conn, uuid, source)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found.")
        app_row = conn.execute(
            "SELECT status, notes FROM applications WHERE uuid = ? AND source = ? AND track = ?",
            (uuid, source, track),
        ).fetchone()
        merged = dict(row)
        app_status = app_row["status"] if app_row else None
        merged["app_status"] = app_status
        merged["app_notes"] = app_row["notes"] if app_row else None
        modify = is_modify_mode(app_status)
        bundle = _dialog_artifact_bundle(merged, track=track, modify=modify)
        existing_run = resolve_modify_run_dir(merged.get("app_notes")) if modify else None
        return {
            "modify_mode": modify,
            "app_status": app_status,
            "apply_label": "Modify" if modify else "Apply",
            "title": row.get("title"),
            "employer_name": row.get("employer_name"),
            "job_url": best_job_url(row),
            "existing_run_name": bundle.get("existing_run_name"),
            "existing_flags": bundle.get("existing_flags") or existing_artifact_flags(existing_run),
            "artifact_defaults": bundle.get("artifact_defaults"),
            "show_academic_docs": bool(bundle.get("show_academic_docs")),
            "notes": merged.get("app_notes"),
        }
    finally:
        conn.close()


@app.get("/api/applications")
def list_applications(
    track: str = Query("industry"),
    status: str = Query(",".join(DEFAULT_APPLIED_STATUS_FILTER + ("drafted",))),
    urgency_days: int = Query(7),
) -> dict[str, Any]:
    path = _require_db()
    df = load_applied_roles_df(str(path), track)
    wanted = tuple(s.strip() for s in status.split(",") if s.strip()) or tuple(STATUS_OPTIONS)
    filtered = filter_applied_roles_df(df, status_filter=wanted)
    bulk = bulk_deanonymize_command(df)
    rows = []
    for _, row in filtered.iterrows():
        payload = job_row_payload(row, within_days=urgency_days)
        payload["status"] = row.get("status")
        payload["notes"] = row.get("notes")
        payload["run_ids"] = extract_run_ids_from_notes(row.get("notes"))
        payload["metrics_summary"] = pipeline_metrics_summary_for_notes(row.get("notes"))
        payload["deanonymize_cmd"] = (
            f"~/private/cv/cv apply {payload['run_ids'][-1]}" if payload["run_ids"] else None
        )
        rows.append(payload)
    return {
        "total": len(filtered),
        "all_count": len(df),
        "applications": rows,
        "bulk_deanonymize": bulk,
    }


@app.patch("/api/applications/{source}/{uuid}")
def patch_application(source: str, uuid: str, body: ApplicationPatch) -> dict[str, Any]:
    if body.status and body.status not in STATUS_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Unknown status {body.status!r}")
    path = _require_db()
    conn = connect(path)
    init_schema(conn)
    try:
        existing = conn.execute(
            "SELECT * FROM applications WHERE uuid = ? AND source = ? AND track = ?",
            (uuid, source, body.track),
        ).fetchone()
        if existing is None and body.status is None and body.pinned is None and body.notes is None:
            raise HTTPException(status_code=404, detail="Application not found.")
        from job_search.web.services import application_status_upsert_row

        row = dict(existing) if existing else {
            "uuid": uuid,
            "source": source,
            "track": body.track,
            "status": "interested",
            "notes": None,
            "cover_letter_path": None,
            "applied_at": None,
            "follow_up_at": None,
            "pinned": 0,
        }
        if body.notes is not None:
            row["notes"] = body.notes
        status = body.status or row.get("status") or "interested"
        payload = application_status_upsert_row(row, status, pinned=body.pinned)
        upsert_application(conn, payload)
        conn.commit()
        clear_explorer_jobs_cache()
        return {"ok": True, "application": json_ready(payload)}
    finally:
        conn.close()


@app.post("/api/jobs/{source}/{uuid}/action")
def job_quick_action(source: str, uuid: str, body: JobQuickActionRequest) -> dict[str, Any]:
    action = (body.action or "").strip().casefold()
    if action not in QUICK_JOB_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown action {body.action!r}. Expected one of: {', '.join(QUICK_JOB_ACTIONS)}",
        )
    path = _require_db()
    conn = connect(path)
    init_schema(conn)
    try:
        try:
            result = apply_job_quick_action(
                conn,
                uuid=uuid,
                source=source,
                track=body.track,
                action=action,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        conn.commit()
        return json_ready(result)
    finally:
        conn.close()


@app.delete("/api/applications/{source}/{uuid}")
def remove_application(source: str, uuid: str, track: str = Query("industry")) -> dict[str, Any]:
    path = _require_db()
    conn = connect(path)
    init_schema(conn)
    try:
        delete_application(conn, uuid, source, track)
        conn.commit()
        clear_explorer_jobs_cache()
        return {"ok": True}
    finally:
        conn.close()


@app.post("/api/ingest")
def post_ingest(body: IngestRequest) -> dict[str, Any]:
    ok, reason = runtime.start_ingest(
        skip_nav=body.skip_nav,
        skip_finn=body.skip_finn,
        skip_jobbnorge=body.skip_jobbnorge,
        academic_queries_only=body.academic_queries_only,
        db_path=str(_db_path()),
    )
    if not ok:
        raise HTTPException(status_code=409, detail=reason)
    return {"ok": True, "status": runtime.ingest_snapshot()}


@app.get("/api/ingest")
def get_ingest() -> dict[str, Any]:
    return runtime.ingest_snapshot()


@app.post("/api/ingest/dismiss")
def ingest_dismiss() -> dict[str, Any]:
    runtime.dismiss_ingest()
    return {"ok": True}


@app.get("/api/ingest/stream")
async def ingest_stream() -> StreamingResponse:
    async def events():
        while True:
            snap = runtime.ingest_snapshot()
            yield f"data: {json.dumps(snap, default=str)}\n\n"
            if snap.get("phase") in ("complete", "error", None) and not snap.get("running"):
                break
            await asyncio.sleep(0.6)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/apply")
def post_apply(body: ApplyRequest) -> dict[str, Any]:
    path = _require_db()
    conn = connect(path)
    init_schema(conn)
    try:
        row = fetch_job_posting(conn, body.uuid, body.source)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found.")
        app_row = conn.execute(
            "SELECT status, notes FROM applications WHERE uuid = ? AND source = ? AND track = ?",
            (body.uuid, body.source, body.track),
        ).fetchone()
        merged = dict(row)
        merged["app_status"] = app_row["status"] if app_row else None
        merged["app_notes"] = app_row["notes"] if app_row else None
        prompts = merge_apply_prompts(body.default_apply_prompts, body.apply_prompts)
        existing_run = None
        if is_modify_mode(merged.get("app_status")):
            existing_run = resolve_modify_run_dir(merged.get("app_notes"))
        options = apply_pipeline_options_from_mapping(
            {
                "language": body.language,
                "apply_prompts": prompts,
                "generate_cover_letter": body.generate_cover_letter,
                "generate_application_letter": body.generate_application_letter,
                "generate_research_proposal": body.generate_research_proposal,
                "overwrite_cv": body.overwrite_cv,
                "overwrite_cover_letter": body.overwrite_cover_letter,
                "overwrite_application_letter": body.overwrite_application_letter,
                "overwrite_research_proposal": body.overwrite_research_proposal,
                "modify_mode": is_modify_mode(merged.get("app_status")),
                "existing_run_id": existing_run.name if existing_run is not None else None,
            }
        )
        job_key = _job_key(body.source, body.uuid)
        ok, reason, started = runtime.enqueue_or_start_apply(
            job_key=job_key,
            row_dict=row_dict_for_apply_from_app(merged),
            track=body.track,
            options=options,
        )
        if not ok:
            raise HTTPException(status_code=409, detail=reason)
        return {"ok": True, "started": started, "job_key": job_key, "pipeline": runtime.pipeline_snapshot()}
    finally:
        conn.close()


@app.get("/api/pipeline")
def get_pipeline() -> dict[str, Any]:
    return json_ready(runtime.pipeline_snapshot())


@app.get("/api/pipeline/stream")
async def pipeline_stream() -> StreamingResponse:
    async def events():
        idle_ticks = 0
        while True:
            snap = json_ready(runtime.pipeline_snapshot())
            yield f"data: {json.dumps(snap, default=str)}\n\n"
            if snap.get("running"):
                idle_ticks = 0
            elif snap.get("phase") in ("complete", "error"):
                idle_ticks += 1
                if idle_ticks >= 2:
                    break
            else:
                break
            await asyncio.sleep(0.6)

    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/log")
def recent_log(lines: int = Query(50, ge=1, le=200)) -> dict[str, Any]:
    return {"text": tail_log_file(lines=lines) or ""}


@app.get("/api/deanonymize-link")
def deanonymize_hint(run_id: str = Query(...)) -> dict[str, str]:
    safe = quote(run_id, safe="._-")
    return {"command": f"~/private/cv/cv apply {safe}"}


@app.get("/api/cv/sources")
def cv_sources_list() -> dict[str, Any]:
    return cv_sources.sources_payload()


@app.get("/api/cv/blank")
def cv_blank() -> dict[str, Any]:
    return cv_sources.blank_payload()


@app.get("/api/cv/document")
def cv_document(source_id: str = Query(...)) -> dict[str, Any]:
    try:
        return cv_sources.document_payload(source_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post("/api/cv/preview")
def cv_preview(body: CvPreviewRequest) -> dict[str, Any]:
    markdown = cv_sources.preview_markdown(body.identity, body.industry, body.academic)
    return {"markdown": markdown}


@app.post("/api/cv")
def cv_save(body: CvSaveRequest) -> dict[str, Any]:
    try:
        return cv_sources.save_fake_cv(
            source_id=body.source_id,
            slug=body.slug,
            identity=body.identity,
            industry=body.industry,
            academic=body.academic,
            activate=body.activate,
        )
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post("/api/cv/activate")
def cv_activate(body: CvActivateRequest) -> dict[str, Any]:
    try:
        return cv_sources.activate_source(body.track, body.source_id)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except FileNotFoundError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err


@app.post("/api/cv/save-mapping")
def cv_save_mapping(body: CvSaveMappingRequest) -> dict[str, Any]:
    try:
        return cv_sources.save_mapping_outside_repo(body.mapping)
    except ValueError as err:
        raise HTTPException(status_code=400, detail=str(err)) from err
    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Could not write the mapping file. Run private_cv setup, or download the JSON instead.",
        ) from None
