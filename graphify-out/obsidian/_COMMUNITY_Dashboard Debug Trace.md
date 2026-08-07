---
type: community
members: 34
---

# Dashboard Debug Trace

**Members:** 34 nodes

## Members
- [[Any_7]] - code
- [[Append one debug event to the in-session ring buffer and optional log file.]] - rationale - job_search/dashboard_debug.py
- [[Drop orphan ``apply_dialog_`` flags so an empty dialog never mounts.]] - rationale - job_search/dashboard.py
- [[Group recent records by rerun id for the debug sidebar timeline.]] - rationale - job_search/dashboard_debug.py
- [[Log one JS-side scroll event once, even across repeated fragment reruns.]] - rationale - job_search/dashboard_debug.py
- [[Log only state keys that changed since the previous completed rerun.]] - rationale - job_search/dashboard_debug.py
- [[Opt-in debug tracing for the Streamlit job search dashboard.]] - rationale - job_search/dashboard_debug.py
- [[Seed debug session keys (safe when Streamlit is unavailable).]] - rationale - job_search/dashboard_debug.py
- [[Sidebar toggle and trace expander (requires Streamlit).]] - rationale - job_search/dashboard_debug.py
- [[Snapshot a small, high-signal subset of session state for rerun diffs.]] - rationale - job_search/dashboard_debug.py
- [[Start a new rerun trace if needed, else reuse the active trace.]] - rationale - job_search/dashboard_debug.py
- [[True when ``JOB_SEARCH_DEBUG=1`` (or trueyes).]] - rationale - job_search/dashboard_debug.py
- [[_active_rerun_context()]] - code - job_search/dashboard_debug.py
- [[_append_file()]] - code - job_search/dashboard_debug.py
- [[_format_event()]] - code - job_search/dashboard_debug.py
- [[_generate_rerun_id()]] - code - job_search/dashboard_debug.py
- [[_normalize_state_value()]] - code - job_search/dashboard_debug.py
- [[_reconcile_apply_dialog_state()]] - code - job_search/dashboard.py
- [[_sanitize_kwargs()]] - code - job_search/dashboard_debug.py
- [[_sanitize_value()]] - code - job_search/dashboard_debug.py
- [[_utc_now()]] - code - job_search/dashboard_debug.py
- [[dashboard_debug.py]] - code - job_search/dashboard_debug.py
- [[debug_enabled_from_env()]] - code - job_search/dashboard_debug.py
- [[debug_log()]] - code - job_search/dashboard_debug.py
- [[init_dashboard_debug()]] - code - job_search/dashboard_debug.py
- [[is_debug_enabled()]] - code - job_search/dashboard_debug.py
- [[log_state_diff()]] - code - job_search/dashboard_debug.py
- [[note_js_scroll_event()]] - code - job_search/dashboard_debug.py
- [[recent_debug_events()]] - code - job_search/dashboard_debug.py
- [[recent_debug_records()]] - code - job_search/dashboard_debug.py
- [[render_debug_sidebar()]] - code - job_search/dashboard_debug.py
- [[snapshot_state_subset()]] - code - job_search/dashboard_debug.py
- [[start_rerun_trace()]] - code - job_search/dashboard_debug.py
- [[summarize_recent_reruns()]] - code - job_search/dashboard_debug.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard_Debug_Trace
SORT file.name ASC
```

## Connections to other communities
- 15 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 8 edges to [[_COMMUNITY_Dashboard Job Export]]
- 3 edges to [[_COMMUNITY_Apply Dialog Fast Path]]
- 3 edges to [[_COMMUNITY_Dashboard_4]]
- 3 edges to [[_COMMUNITY_Dashboard Debug]]
- 2 edges to [[_COMMUNITY_Dashboard_1]]
- 2 edges to [[_COMMUNITY_Apply Pipeline Options]]
- 1 edge to [[_COMMUNITY_Dashboard_2]]
- 1 edge to [[_COMMUNITY_Pipeline Queue Metrics]]
- 1 edge to [[_COMMUNITY_Dashboard Scroll Styles]]
- 1 edge to [[_COMMUNITY_Dashboard]]
- 1 edge to [[_COMMUNITY_Test Dashboard Debug]]

## Top bridge nodes
- [[debug_log()]] - degree 29, connects to 10 communities
- [[dashboard_debug.py]] - degree 27, connects to 4 communities
- [[start_rerun_trace()]] - degree 11, connects to 3 communities
- [[log_state_diff()]] - degree 9, connects to 3 communities
- [[_reconcile_apply_dialog_state()]] - degree 7, connects to 3 communities