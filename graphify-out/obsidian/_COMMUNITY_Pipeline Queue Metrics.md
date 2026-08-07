---
type: community
members: 55
---

# Pipeline Queue Metrics

**Members:** 55 nodes

## Members
- [[Any_6]] - code
- [[Collapsible liverecent pipeline stdout under the status UI. Returns an…]] - rationale - job_search/dashboard.py
- [[Copy background-worker progress into Streamlit session state.]] - rationale - job_search/dashboard.py
- [[Dialog body form or live pipeline status for the active job key. No DB open…]] - rationale - job_search/dashboard.py
- [[Full-width success  warning  error summary after a pipeline finishes. Renders…]] - rationale - job_search/dashboard.py
- [[Launch apply work on a daemon thread so Streamlit reruns do not cancel it.]] - rationale - job_search/dashboard.py
- [[Load ``pipeline_metrics.json`` for a run basename, if present.]] - rationale - job_search/dashboard.py
- [[Lock]] - code
- [[Mark stuck UI state as error when no background worker is alive. Call only…]] - rationale - job_search/dashboard.py
- [[Path_13]] - code
- [[Pop the next waiting job. Returns ``(remaining_queue, item_or_none)``.]] - rationale - job_search/dashboard.py
- [[Prepare dialog state then rerun (non-callback callers).]] - rationale - job_search/dashboard.py
- [[Re-open popover after rerun when dialog API is unavailable.]] - rationale - job_search/dashboard.py
- [[Resolve a run basename to ``cv_generationcv_runsrun_id``.]] - rationale - cv_generation/pipeline_metrics.py
- [[Resolve stable result metadata so completed runs can be reopened later.]] - rationale - job_search/dashboard.py
- [[Short titles for status-bar captions.]] - rationale - job_search/dashboard.py
- [[Show live pipeline progress and completion inside the ApplyModify dialog.]] - rationale - job_search/dashboard.py
- [[Show live progress widgets and optionally schedule the next poll rerun.]] - rationale - job_search/dashboard.py
- [[Show the active pipeline panel below a job row or as a page fallback.]] - rationale - job_search/dashboard.py
- [[Snapshot the finished active pipeline so the banner can survive start-next.]] - rationale - job_search/dashboard.py
- [[Start or poll the background apply worker; never block the Streamlit script on…]] - rationale - job_search/dashboard.py
- [[Sync worker progress first, then only mark orphaned if nothing is alive.]] - rationale - job_search/dashboard.py
- [[Top-of-page summary for a background pipeline; returns True when polling should…]] - rationale - job_search/dashboard.py
- [[True when session state holds a pipeline for this job row key.]] - rationale - job_search/dashboard.py
- [[When the active job finished, park its notice and start the next queued job.…]] - rationale - job_search/dashboard.py
- [[_advance_pipeline_queue_after_finish()]] - code - job_search/dashboard.py
- [[_apply_modify_dialog_body()]] - code - job_search/dashboard.py
- [[_build_pipeline_result()]] - code - job_search/dashboard.py
- [[_launch_apply_modify_dialog()]] - code - job_search/dashboard.py
- [[_park_recent_pipeline_completion()]] - code - job_search/dashboard.py
- [[_pipeline_active_for_job()]] - code - job_search/dashboard.py
- [[_pipeline_job_title()]] - code - job_search/dashboard.py
- [[_pipeline_log_text()]] - code - job_search/dashboard.py
- [[_pipeline_worker_entry()]] - code - job_search/dashboard.py
- [[_pipeline_worker_registry()]] - code - job_search/dashboard.py
- [[_pipeline_worker_thread_alive()]] - code - job_search/dashboard.py
- [[_recover_orphaned_pipeline_if_needed()]] - code - job_search/dashboard.py
- [[_render_pipeline_log_expander()]] - code - job_search/dashboard.py
- [[_render_pipeline_status_bar()]] - code - job_search/dashboard.py
- [[_render_running_pipeline_progress()]] - code - job_search/dashboard.py
- [[_run_queued_pipeline()]] - code - job_search/dashboard.py
- [[_show_pipeline_result()]] - code - job_search/dashboard.py
- [[_start_pipeline_worker()]] - code - job_search/dashboard.py
- [[_sync_pipeline_worker_to_session()]] - code - job_search/dashboard.py
- [[_sync_then_recover_pipeline()]] - code - job_search/dashboard.py
- [[dequeue_pipeline_item()]] - code - job_search/dashboard.py
- [[fetch_job_posting()]] - code - job_search/dashboard.py
- [[load_pipeline_metrics()]] - code - cv_generation/pipeline_metrics.py
- [[pipeline_metrics_for_run_id()]] - code - job_search/dashboard.py
- [[pipeline_queue_display_titles()]] - code - job_search/dashboard.py
- [[pipeline_result_details()]] - code - job_search/dashboard.py
- [[render_apply_modify_popover_fallback()]] - code - job_search/dashboard.py
- [[render_pipeline_panel()]] - code - job_search/dashboard.py
- [[render_pipeline_status_in_dialog()]] - code - job_search/dashboard.py
- [[resolve_run_dir()]] - code - cv_generation/pipeline_metrics.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Pipeline_Queue_Metrics
SORT file.name ASC
```

## Connections to other communities
- 42 edges to [[_COMMUNITY_Dashboard Job Export]]
- 31 edges to [[_COMMUNITY_Apply Pipeline Options]]
- 8 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 7 edges to [[_COMMUNITY_Pipeline Metrics Format]]
- 5 edges to [[_COMMUNITY_Apply Dialog Fast Path]]
- 4 edges to [[_COMMUNITY_Dashboard]]
- 4 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 4 edges to [[_COMMUNITY_Ingest Cycle Dashboard]]
- 3 edges to [[_COMMUNITY_Apply Artifact Options]]
- 2 edges to [[_COMMUNITY_Dashboard_5]]
- 2 edges to [[_COMMUNITY_Dashboard_1]]
- 1 edge to [[_COMMUNITY_Job Filters]]
- 1 edge to [[_COMMUNITY_Dashboard DB Loaders]]
- 1 edge to [[_COMMUNITY_Applied Roles UI]]
- 1 edge to [[_COMMUNITY_Dashboard_2]]
- 1 edge to [[_COMMUNITY_Dashboard_3]]
- 1 edge to [[_COMMUNITY_Dashboard Debug Trace]]

## Top bridge nodes
- [[Any_6]] - degree 54, connects to 12 communities
- [[_render_pipeline_status_bar()]] - degree 10, connects to 5 communities
- [[_show_pipeline_result()]] - degree 12, connects to 4 communities
- [[pipeline_result_details()]] - degree 8, connects to 4 communities
- [[pipeline_queue_display_titles()]] - degree 7, connects to 4 communities