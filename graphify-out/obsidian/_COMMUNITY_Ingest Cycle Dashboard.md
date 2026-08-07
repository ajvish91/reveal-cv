---
type: community
members: 24
---

# Ingest Cycle Dashboard

**Members:** 24 nodes

## Members
- [[dot-test_false_when_panel_already_rendered()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_skips_when_apply_dialog_open()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_true_when_dialog_closed_and_pipeline_queued()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Combined dashboard CSS (metrics, job cards, explorer).]] - rationale - job_search/dashboard_styles.py
- [[IngestCycleOptions]] - code - job_search/dashboard.py
- [[Minimal page while a background apply worker polls (no job dataframe loads).]] - rationale - job_search/dashboard.py
- [[Parse step labels and JSON summaries from ``run_job_search_cycle`` stdout.]] - rationale - job_search/dashboard.py
- [[Render the active pipeline at page level when its row is off-screen.]] - rationale - job_search/dashboard.py
- [[Run ingest cycle script, optionally invoking ``on_line`` for each stdout line.]] - rationale - job_search/dashboard.py
- [[Run queued ingest + score subprocess and store parsed summary in session state.]] - rationale - job_search/dashboard.py
- [[TestPipelineFallbackEligible]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[True when pipeline polling should skip job loads (dialog dismissed, worker…]] - rationale - job_search/dashboard.py
- [[True when the page-level fallback should render the active pipeline.]] - rationale - job_search/dashboard.py
- [[User-selected ingest cycle options from the dashboard sidebar.]] - rationale - job_search/dashboard.py
- [[_execute_ingest_cycle()]] - code - job_search/dashboard.py
- [[_inject_dashboard_css()]] - code - job_search/dashboard.py
- [[_pipeline_poll_fast_path_active()]] - code - job_search/dashboard.py
- [[_render_pipeline_poll_fast_path()]] - code - job_search/dashboard.py
- [[dashboard_css()]] - code - job_search/dashboard_styles.py
- [[get_db_path()]] - code - job_search/dashboard.py
- [[parse_ingest_cycle_output()]] - code - job_search/dashboard.py
- [[pipeline_fallback_eligible()]] - code - job_search/dashboard.py
- [[render_pipeline_panel_fallback()]] - code - job_search/dashboard.py
- [[run_ingest_cycle_subprocess()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Ingest_Cycle_Dashboard
SORT file.name ASC
```

## Connections to other communities
- 12 edges to [[_COMMUNITY_Dashboard Job Export]]
- 6 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 4 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 4 edges to [[_COMMUNITY_Apply Pipeline Options]]
- 3 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 3 edges to [[_COMMUNITY_Test Dashboard Ingest]]
- 2 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 1 edge to [[_COMMUNITY_FINN Job Client]]
- 1 edge to [[_COMMUNITY_Dashboard Scroll Styles]]

## Top bridge nodes
- [[_execute_ingest_cycle()]] - degree 11, connects to 5 communities
- [[get_db_path()]] - degree 6, connects to 4 communities
- [[_render_pipeline_poll_fast_path()]] - degree 8, connects to 3 communities
- [[parse_ingest_cycle_output()]] - degree 6, connects to 3 communities
- [[render_pipeline_panel_fallback()]] - degree 6, connects to 3 communities