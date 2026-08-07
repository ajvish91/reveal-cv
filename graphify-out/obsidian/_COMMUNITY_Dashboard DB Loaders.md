---
type: community
members: 53
---

# Dashboard DB Loaders

**Members:** 53 nodes

## Members
- [[dot-test_delete_application_missing_row_is_no_op()]] - code - job_search/tests/test_job_db.py
- [[dot-test_delete_application_removes_matching_row()]] - code - job_search/tests/test_job_db.py
- [[dot-test_effective_if_modified_since_uses_saved_state_overlap()]] - code - job_search/tests/test_job_search_pipeline.py
- [[dot-test_empty_reingest_keeps_existing_description_and_detail()]] - code - job_search/tests/test_job_db.py
- [[dot-test_load_applied_roles_df_filters_by_track()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_load_jobs_df_hide_applied_excludes_drafted_and_applied()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_mark_stale_jobs_inactive_for_finn_no()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_mark_stale_jobs_inactive_marks_missing_rows()]] - code - job_search/tests/test_job_search_pipeline.py
- [[Active job counts per ingest source plus academic-track scored rows.]] - rationale - job_search/dashboard.py
- [[Active jobs whose title matches postdocresearcherlecturer vocabulary.]] - rationale - job_search/dashboard.py
- [[All applications across tracks (raw table).]] - rationale - job_search/dashboard.py
- [[Any_14]] - code
- [[Connection]] - code
- [[Map normalized company name - display name from CSV.]] - rationale - job_search/score_jobs.py
- [[Namespace_10]] - code
- [[Path_25]] - code
- [[Path_27]] - code
- [[SQLite persistence for job postings (Phase B+).]] - rationale - job_search/job_db.py
- [[TestDeleteApplication]] - code - job_search/tests/test_job_db.py
- [[TestUpsertJobPreservesDescription]] - code - job_search/tests/test_job_db.py
- [[Tests for job_search.job_db helpers.]] - rationale - job_search/tests/test_job_db.py
- [[Three capped overview lists in one cache entry (one SQLite connection).]] - rationale - job_search/dashboard.py
- [[_ensure_column()]] - code - job_search/job_db.py
- [[_mark_cache_exec()]] - code - job_search/dashboard.py
- [[cache_data]] - code
- [[connect()]] - code - job_search/job_db.py
- [[count_research_roles_in_db()]] - code - job_search/dashboard.py
- [[delete_application()]] - code - job_search/job_db.py
- [[filter_phd_student_df()]] - code - job_search/dashboard.py
- [[find_tek_match()]] - code - job_search/score_jobs.py
- [[get_state()]] - code - job_search/job_db.py
- [[haystack_for_job()]] - code - job_search/score_jobs.py
- [[ingest_active_source_counts()]] - code - job_search/dashboard.py
- [[init_schema()]] - code - job_search/job_db.py
- [[job_db.py]] - code - job_search/job_db.py
- [[load_applications_df()]] - code - job_search/dashboard.py
- [[load_applied_roles_df()]] - code - job_search/dashboard.py
- [[load_jobs_df()]] - code - job_search/dashboard.py
- [[load_overview_jobs_bundle()]] - code - job_search/dashboard.py
- [[load_overview_metrics()]] - code - job_search/dashboard.py
- [[load_tek_by_norm()]] - code - job_search/score_jobs.py
- [[main()_13]] - code - job_search/score_jobs.py
- [[norm_company()]] - code - job_search/score_jobs.py
- [[run()_2]] - code - job_search/score_jobs.py
- [[score_jobs.py]] - code - job_search/score_jobs.py
- [[score_profile()]] - code - job_search/score_jobs.py
- [[set_state()]] - code - job_search/job_db.py
- [[test_job_db.py]] - code - job_search/tests/test_job_db.py
- [[test_job_search_pipeline.py]] - code - job_search/tests/test_job_search_pipeline.py
- [[upsert_application()]] - code - job_search/job_db.py
- [[upsert_job()]] - code - job_search/job_db.py
- [[upsert_score()]] - code - job_search/job_db.py
- [[utc_now_iso()_1]] - code - job_search/job_db.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard_DB_Loaders
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_NAV Job Ingest]]
- 21 edges to [[_COMMUNITY_FINN Search Queries]]
- 14 edges to [[_COMMUNITY_Location Preferences]]
- 13 edges to [[_COMMUNITY_Academic Job Filters]]
- 12 edges to [[_COMMUNITY_Dashboard Job Export]]
- 12 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 11 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 8 edges to [[_COMMUNITY_Apply Pipeline Options]]
- 4 edges to [[_COMMUNITY_Ingest Keyword Collect]]
- 3 edges to [[_COMMUNITY_Ingest Cycle Dashboard]]
- 2 edges to [[_COMMUNITY_Job Filters]]
- 2 edges to [[_COMMUNITY_TEK Rogaland Fetch]]
- 2 edges to [[_COMMUNITY_NAV Feed Client]]
- 1 edge to [[_COMMUNITY_Pipeline Queue Metrics]]
- 1 edge to [[_COMMUNITY_Apply Artifact Options]]
- 1 edge to [[_COMMUNITY_Deadline Urgency Utils]]
- 1 edge to [[_COMMUNITY_Applied Roles UI]]
- 1 edge to [[_COMMUNITY_FINN Job Client]]

## Top bridge nodes
- [[test_job_search_pipeline.py]] - degree 22, connects to 6 communities
- [[connect()]] - degree 30, connects to 5 communities
- [[init_schema()]] - degree 30, connects to 5 communities
- [[score_jobs.py]] - degree 29, connects to 5 communities
- [[load_jobs_df()]] - degree 12, connects to 5 communities