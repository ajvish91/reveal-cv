---
type: community
members: 33
---

# Dashboard Search Cache

**Members:** 33 nodes

## Members
- [[Context manager that logs a timing event on exit.]] - rationale - job_search/dashboard_debug.py
- [[DataFrame]] - code
- [[Default session keys for optional periodic cache refresh.]] - rationale - job_search/dashboard.py
- [[Default session keys for the active apply pipeline + waiting queue.]] - rationale - job_search/dashboard.py
- [[Default session keys for the dashboard ingest cycle.]] - rationale - job_search/dashboard.py
- [[Display ingest cycle summary JSON and post-run counts.]] - rationale - job_search/dashboard.py
- [[Free-text search over title, employer, and description (post-filter on…]] - rationale - job_search/dashboard.py
- [[Import with one retry after clearing a half-loaded ``sys.modules`` entry.…]] - rationale - job_search/dashboard.py
- [[Lazy import so Streamlit hot-reload can purge ``sys.modules`` safely.]] - rationale - job_search/dashboard.py
- [[Load and filter explorer jobs; reuse session snapshot when filters are…]] - rationale - job_search/dashboard.py
- [[Mark the active rerun trace complete and retain a short sidebar summary.]] - rationale - job_search/dashboard_debug.py
- [[Open the ApplyModify dialog at most once per script run when context is valid.]] - rationale - job_search/dashboard.py
- [[Overview expanders isolated so in-section slider changes skip the job explorer.]] - rationale - job_search/dashboard.py
- [[Sidebar controls to queue NAV + FINN ingest and scoring.]] - rationale - job_search/dashboard.py
- [[_cache_exec_count()]] - code - job_search/dashboard.py
- [[_import_module_resilient()]] - code - job_search/dashboard.py
- [[_infer_page_rerun_reason()]] - code - job_search/dashboard.py
- [[_infer_page_scope()]] - code - job_search/dashboard.py
- [[_init_ingest_session_state()]] - code - job_search/dashboard.py
- [[_init_pipeline_session_state()]] - code - job_search/dashboard.py
- [[_init_refresh_session_state()]] - code - job_search/dashboard.py
- [[_load_explorer_jobs_df()]] - code - job_search/dashboard.py
- [[_log_cache_probe()]] - code - job_search/dashboard.py
- [[_log_dashboard_filter_state()]] - code - job_search/dashboard.py
- [[_render_overview_fragment()]] - code - job_search/dashboard.py
- [[_show_ingest_result_panel()]] - code - job_search/dashboard.py
- [[apply_text_search_filter()]] - code - job_search/dashboard.py
- [[dedupe_jobs_df()]] - code - job_search/dashboard.py
- [[finish_rerun_trace()]] - code - job_search/dashboard_debug.py
- [[main()_9]] - code - job_search/dashboard.py
- [[maybe_open_apply_modify_dialog()]] - code - job_search/dashboard.py
- [[render_ingest_sidebar_section()]] - code - job_search/dashboard.py
- [[timing_span()]] - code - job_search/dashboard_debug.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard_Search_Cache
SORT file.name ASC
```

## Connections to other communities
- 28 edges to [[_COMMUNITY_Dashboard Job Export]]
- 15 edges to [[_COMMUNITY_Dashboard Debug Trace]]
- 12 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 6 edges to [[_COMMUNITY_Ingest Cycle Dashboard]]
- 6 edges to [[_COMMUNITY_Academic Job Filters]]
- 6 edges to [[_COMMUNITY_Dashboard_4]]
- 5 edges to [[_COMMUNITY_Applied Roles UI]]
- 4 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 2 edges to [[_COMMUNITY_Apply Dialog Fast Path]]
- 2 edges to [[_COMMUNITY_NAV Job Ingest]]
- 2 edges to [[_COMMUNITY_Dashboard Debug]]
- 2 edges to [[_COMMUNITY_FINN Search Queries]]
- 1 edge to [[_COMMUNITY_Pipeline Metrics Format]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]
- 1 edge to [[_COMMUNITY_Dashboard Auto Refresh]]
- 1 edge to [[_COMMUNITY_Dashboard Scroll Styles]]
- 1 edge to [[_COMMUNITY_Dashboard]]

## Top bridge nodes
- [[main()_9]] - degree 52, connects to 16 communities
- [[_load_explorer_jobs_df()]] - degree 15, connects to 6 communities
- [[_render_overview_fragment()]] - degree 14, connects to 6 communities
- [[DataFrame]] - degree 18, connects to 5 communities
- [[timing_span()]] - degree 11, connects to 5 communities