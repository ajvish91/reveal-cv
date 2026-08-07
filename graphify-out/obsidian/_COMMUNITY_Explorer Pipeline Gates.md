---
type: community
members: 54
---

# Explorer Pipeline Gates

**Members:** 54 nodes

## Members
- [[dot-test_applied_role_row_uses_flat_action_columns()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_apply_dialog_ready_for_view_completion()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_can_enqueue_idle_starts_ok()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_can_enqueue_rejects_duplicate_active_and_waiting()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_can_enqueue_rejects_when_full_or_ingest()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_empty_notes()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_explorer_cache_fingerprint_includes_dedupe_and_hide_applied()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_explorer_defaults_hide_applied_and_dedupe()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_explorer_filter_chips_reflect_defaults()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_extracts_basename_from_full_path()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_extracts_multiple_runs()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_extracts_path_with_spaces()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_extracts_step_index()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_hide_applied_statuses_include_drafted_not_interested()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_job_explorer_apply_column_wide_enough()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_log_delete_button_column_wide_enough()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_max_in_flight_is_one_running_plus_two_waiting()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_phase_busy_only_queued_or_running()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_slots_and_full()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_stage_label_maps_wrote_lines()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_summary_from_metrics_file()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_summary_missing_metrics_returns_none()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_unknown_label_returns_zero()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Count of in-flight pipelines (active + waiting).]] - rationale - job_search/dashboard.py
- [[Extract the 1–11 step index from a pipeline stage label.]] - rationale - job_search/dashboard.py
- [[Hashable key for the in-session explorer dataframe snapshot.]] - rationale - job_search/dashboard.py
- [[How many more jobs can still be enqueued (or started if idle).]] - rationale - job_search/dashboard.py
- [[Human-readable labels for active explorer filters.]] - rationale - job_search/dashboard.py
- [[Map agent pipeline log lines to user-visible stage labels.]] - rationale - job_search/dashboard.py
- [[One-line impact summary from the latest CV run referenced in notes.]] - rationale - job_search/dashboard.py
- [[Return CV run folder basenames from application notes (``CV run …`` lines).]] - rationale - job_search/dashboard.py
- [[Return ``(ok, reason)`` for starting or enqueueing ``job_key``. When idle…]] - rationale - job_search/dashboard.py
- [[TestDashboardColumnLayouts]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[TestExtractRunIds]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[TestHideAppliedFilter]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[TestLoadAppliedRolesDf]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[TestPipelineMetricsDashboard]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[TestPipelineQueueHelpers]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[TestPipelineStageNumber]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Tests for dashboard Applied roles helpers (no Streamlit import).]] - rationale - job_search/tests/test_dashboard_applied_roles.py
- [[True when no more ApplyModify jobs can be started or enqueued.]] - rationale - job_search/dashboard.py
- [[True while a worker is queued or running (not finished).]] - rationale - job_search/dashboard.py
- [[_explorer_jobs_cache_fingerprint()]] - code - job_search/dashboard.py
- [[build_explorer_filter_chips()]] - code - job_search/dashboard.py
- [[can_enqueue_pipeline()]] - code - job_search/dashboard.py
- [[extract_run_ids_from_notes()]] - code - job_search/dashboard.py
- [[pipeline_metrics_summary_for_notes()]] - code - job_search/dashboard.py
- [[pipeline_phase_is_busy()]] - code - job_search/dashboard.py
- [[pipeline_queue_is_full()]] - code - job_search/dashboard.py
- [[pipeline_queue_remaining()]] - code - job_search/dashboard.py
- [[pipeline_queue_slots_used()]] - code - job_search/dashboard.py
- [[pipeline_stage_label()]] - code - job_search/dashboard.py
- [[pipeline_stage_number()]] - code - job_search/dashboard.py
- [[test_dashboard_applied_roles.py]] - code - job_search/tests/test_dashboard_applied_roles.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Explorer_Pipeline_Gates
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Apply Pipeline Options]]
- 16 edges to [[_COMMUNITY_Dashboard Job Export]]
- 11 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 8 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 6 edges to [[_COMMUNITY_Apply Dialog Fast Path]]
- 6 edges to [[_COMMUNITY_Applied Roles UI]]
- 5 edges to [[_COMMUNITY_Apply Artifact Options]]
- 4 edges to [[_COMMUNITY_Dashboard]]
- 2 edges to [[_COMMUNITY_Ingest Cycle Dashboard]]
- 2 edges to [[_COMMUNITY_Dashboard_4]]
- 2 edges to [[_COMMUNITY_Dashboard_5]]
- 1 edge to [[_COMMUNITY_Pipeline Metrics Format]]
- 1 edge to [[_COMMUNITY_Dashboard Scroll Styles]]
- 1 edge to [[_COMMUNITY_Test Dashboard Applied Roles]]

## Top bridge nodes
- [[test_dashboard_applied_roles.py]] - degree 65, connects to 12 communities
- [[extract_run_ids_from_notes()]] - degree 12, connects to 3 communities
- [[can_enqueue_pipeline()]] - degree 11, connects to 3 communities
- [[pipeline_metrics_summary_for_notes()]] - degree 9, connects to 3 communities
- [[_explorer_jobs_cache_fingerprint()]] - degree 6, connects to 3 communities