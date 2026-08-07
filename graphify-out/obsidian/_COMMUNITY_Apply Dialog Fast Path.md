---
type: community
members: 21
---

# Apply Dialog Fast Path

**Members:** 21 nodes

## Members
- [[dot-test_not_ready_without_context_or_pipeline()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_pipeline_active_for_job_key()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_ready_with_active_pipeline_even_without_context()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_ready_with_row_context()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_reconcile_clears_stale_open_flags()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_reconcile_keeps_valid_context()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_yield_after_prepare_snapshot_opens_from_fragment()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Fragment reruns skip main(); flags set in on_click must still be dialog-ready.]] - rationale - job_search/tests/test_dashboard_applied_roles.py
- [[Open ApplyModify when session flags are ready; return True to skip caller body.]] - rationale - job_search/dashboard.py
- [[Return session-state patches that clear stale dialog flags (no Streamlit).]] - rationale - job_search/dashboard.py
- [[TestApplyDialogReady]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[True when ApplyModify dialog flags are ready (pure helper for tests +…]] - rationale - job_search/dashboard.py
- [[True when ApplyModify may open valid row context or active pipeline for the…]] - rationale - job_search/dashboard.py
- [[True when session holds an active pipeline for ``job_key`` (no Streamlit).]] - rationale - job_search/dashboard.py
- [[True when the ApplyModify dialog should short-circuit the heavy dashboard page.]] - rationale - job_search/dashboard.py
- [[_apply_dialog_fast_path_active()]] - code - job_search/dashboard.py
- [[_apply_dialog_snapshot()]] - code - job_search/dashboard.py
- [[apply_dialog_ready()]] - code - job_search/dashboard.py
- [[pipeline_active_for_job_key()]] - code - job_search/dashboard.py
- [[reconcile_apply_dialog_flags()]] - code - job_search/dashboard.py
- [[yield_to_apply_modify_dialog()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Apply_Dialog_Fast_Path
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Dashboard Job Export]]
- 6 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 5 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 3 edges to [[_COMMUNITY_Dashboard Debug Trace]]
- 2 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]

## Top bridge nodes
- [[yield_to_apply_modify_dialog()]] - degree 10, connects to 5 communities
- [[reconcile_apply_dialog_flags()]] - degree 8, connects to 4 communities
- [[apply_dialog_ready()]] - degree 12, connects to 3 communities
- [[pipeline_active_for_job_key()]] - degree 6, connects to 3 communities
- [[_apply_dialog_snapshot()]] - degree 4, connects to 3 communities