---
type: community
members: 64
---

# Dashboard Job Export

**Members:** 64 nodes

## Members
- [[dot-test_format_job_export_text_tolerates_nan()]] - code - job_search/tests/test_dashboard_safe_str.py
- [[dot-test_format_location_municipal_county()]] - code - job_search/tests/test_dashboard_safe_str.py
- [[dot-test_format_location_tolerates_nan_fields()]] - code - job_search/tests/test_dashboard_safe_str.py
- [[dot-test_safe_str_none_and_nan()]] - code - job_search/tests/test_dashboard_safe_str.py
- [[dot-test_safe_str_strips_text()]] - code - job_search/tests/test_dashboard_safe_str.py
- [[Append one stdout line to session log; keep the last N lines.]] - rationale - job_search/dashboard.py
- [[Card-style job listing title link, metadata, score badge, actions.]] - rationale - job_search/dashboard.py
- [[Clear Streamlit data cache and in-session explorer dataframe snapshot.]] - rationale - job_search/dashboard.py
- [[Clear cached queries and rerun when the sidebar auto-refresh interval elapses.]] - rationale - job_search/dashboard.py
- [[Coerce pandasDB cell values to stripped str; NoneNaN - ''.]] - rationale - job_search/dashboard.py
- [[Collapsible overview list with compact job rows.]] - rationale - job_search/dashboard.py
- [[Compact applied-role row title, status badge, score, Modify  Mark as applied…]] - rationale - job_search/dashboard.py
- [[Expanded details for an applied role status, meta, runs, deanonymize, links.]] - rationale - job_search/dashboard.py
- [[Expanded job details meta, links.]] - rationale - job_search/dashboard.py
- [[Extract expires field from a DB row or pandas Series.]] - rationale - job_search/deadline_utils.py
- [[Fetch FINN detail HTML when the DB row has no description_text.]] - rationale - job_search/dashboard.py
- [[Human-readable deadline label for tables; em dash when unknown or garbage.]] - rationale - job_search/deadline_utils.py
- [[Popover to delete an application row from SQLite (not cv_runs).]] - rationale - job_search/dashboard.py
- [[Remove one ``applications`` row; CV run folders on disk are unchanged.]] - rationale - job_search/dashboard.py
- [[Reset periodic refresh timer after an explicit cache reload.]] - rationale - job_search/dashboard.py
- [[SafeStrTests]] - code - job_search/tests/test_dashboard_safe_str.py
- [[Series]] - code
- [[Status select + save for one application row. Optional mark-as-applied shortcut…]] - rationale - job_search/dashboard.py
- [[Tests for NaN-safe string helpers used by the Streamlit dashboard.]] - rationale - job_search/tests/test_dashboard_safe_str.py
- [[Upsert application status, refresh caches, and rerun the dashboard.]] - rationale - job_search/dashboard.py
- [[_append_pipeline_log_line()]] - code - job_search/dashboard.py
- [[_handle_application_status_update()]] - code - job_search/dashboard.py
- [[_handle_delete_application()]] - code - job_search/dashboard.py
- [[_html_escape()]] - code - job_search/dashboard.py
- [[_invalidate_dashboard_data_caches()]] - code - job_search/dashboard.py
- [[_job_card_meta_html()]] - code - job_search/dashboard.py
- [[_job_card_title_html()]] - code - job_search/dashboard.py
- [[_job_meta_caption()]] - code - job_search/dashboard.py
- [[_job_score_badge_html()]] - code - job_search/dashboard.py
- [[_keyword_hits_text()]] - code - job_search/dashboard.py
- [[_maybe_periodic_data_refresh()]] - code - job_search/dashboard.py
- [[_safe_str()]] - code - job_search/dashboard.py
- [[_score_breakdown()]] - code - job_search/dashboard.py
- [[_score_display()]] - code - job_search/dashboard.py
- [[_status_badge_html()]] - code - job_search/dashboard.py
- [[_touch_data_refresh_clock()]] - code - job_search/dashboard.py
- [[best_job_url()]] - code - job_search/dashboard.py
- [[cv_job_filename()]] - code - job_search/dashboard.py
- [[dashboard.py]] - code - job_search/dashboard.py
- [[deadline_display()]] - code - job_search/deadline_utils.py
- [[enrich_jobs_df()]] - code - job_search/dashboard.py
- [[export_job_to_cv_file()]] - code - job_search/dashboard.py
- [[format_job_export_text()]] - code - job_search/dashboard.py
- [[format_location()]] - code - job_search/dashboard.py
- [[refresh_finn_job_description()]] - code - job_search/dashboard.py
- [[render_application_status_controls()]] - code - job_search/dashboard.py
- [[render_applied_role_details()]] - code - job_search/dashboard.py
- [[render_applied_role_row()]] - code - job_search/dashboard.py
- [[render_compact_job_row()]] - code - job_search/dashboard.py
- [[render_delete_application_popover()]] - code - job_search/dashboard.py
- [[render_job_details()]] - code - job_search/dashboard.py
- [[render_job_link()]] - code - job_search/dashboard.py
- [[render_overview_section()]] - code - job_search/dashboard.py
- [[row_expires()]] - code - job_search/deadline_utils.py
- [[source_display()]] - code - job_search/dashboard.py
- [[source_label_short()]] - code - job_search/dashboard.py
- [[status_badge_markdown()]] - code - job_search/dashboard.py
- [[test_dashboard_safe_str.py]] - code - job_search/tests/test_dashboard_safe_str.py
- [[title_slug()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard_Job_Export
SORT file.name ASC
```

## Connections to other communities
- 42 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 33 edges to [[_COMMUNITY_Apply Pipeline Options]]
- 28 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 16 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 12 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 12 edges to [[_COMMUNITY_Ingest Cycle Dashboard]]
- 11 edges to [[_COMMUNITY_Deadline Urgency Utils]]
- 10 edges to [[_COMMUNITY_Academic Job Filters]]
- 10 edges to [[_COMMUNITY_Applied Roles UI]]
- 8 edges to [[_COMMUNITY_Dashboard Debug Trace]]
- 8 edges to [[_COMMUNITY_Dashboard_4]]
- 7 edges to [[_COMMUNITY_FINN Search Queries]]
- 6 edges to [[_COMMUNITY_Dashboard_5]]
- 6 edges to [[_COMMUNITY_Apply Dialog Fast Path]]
- 6 edges to [[_COMMUNITY_Dashboard]]
- 6 edges to [[_COMMUNITY_Job Filters]]
- 5 edges to [[_COMMUNITY_Apply Artifact Options]]
- 5 edges to [[_COMMUNITY_Dashboard_1]]
- 5 edges to [[_COMMUNITY_Dashboard Scroll Styles]]
- 5 edges to [[_COMMUNITY_Dashboard Auto Refresh]]
- 4 edges to [[_COMMUNITY_NAV Job Ingest]]
- 3 edges to [[_COMMUNITY_Pipeline Metrics Format]]
- 2 edges to [[_COMMUNITY_Apply Prompts Config]]
- 2 edges to [[_COMMUNITY_Application Artifacts]]
- 2 edges to [[_COMMUNITY_Test Dashboard Ingest]]
- 2 edges to [[_COMMUNITY_Dashboard_3]]
- 2 edges to [[_COMMUNITY_Dashboard_2]]
- 2 edges to [[_COMMUNITY_FINN Job Client]]
- 1 edge to [[_COMMUNITY_Private CV Apply]]
- 1 edge to [[_COMMUNITY_Dashboard Debug]]
- 1 edge to [[_COMMUNITY_Test Job Filters Relevance]]

## Top bridge nodes
- [[dashboard.py]] - degree 240, connects to 31 communities
- [[refresh_finn_job_description()]] - degree 9, connects to 6 communities
- [[_invalidate_dashboard_data_caches()]] - degree 9, connects to 4 communities
- [[_safe_str()]] - degree 20, connects to 3 communities
- [[render_compact_job_row()]] - degree 15, connects to 3 communities