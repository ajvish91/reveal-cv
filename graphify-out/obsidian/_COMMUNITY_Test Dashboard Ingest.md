---
type: community
members: 14
---

# Test Dashboard Ingest

**Members:** 14 nodes

## Members
- [[dot-test_academic_queries_only()]] - code - job_search/tests/test_dashboard_ingest.py
- [[dot-test_academic_queries_only_argparse_accepts()]] - code - job_search/tests/test_dashboard_ingest.py
- [[dot-test_db_path_forwarded()]] - code - job_search/tests/test_dashboard_ingest.py
- [[dot-test_default_daily_cycle()]] - code - job_search/tests/test_dashboard_ingest.py
- [[dot-test_parses_step_json_blocks()]] - code - job_search/tests/test_dashboard_ingest.py
- [[dot-test_skip_both_runs_score_only()]] - code - job_search/tests/test_dashboard_ingest.py
- [[dot-test_skip_finn_only()]] - code - job_search/tests/test_dashboard_ingest.py
- [[dot-test_skip_nav_only()]] - code - job_search/tests/test_dashboard_ingest.py
- [[Build ``scriptsrun_job_search_cycle.py`` argv for dashboard ingest.]] - rationale - job_search/dashboard.py
- [[TestBuildIngestCycleCommand]] - code - job_search/tests/test_dashboard_ingest.py
- [[TestParseIngestCycleOutput]] - code - job_search/tests/test_dashboard_ingest.py
- [[Tests for dashboard ingest-cycle helpers (no Streamlit runtime).]] - rationale - job_search/tests/test_dashboard_ingest.py
- [[build_ingest_cycle_command()]] - code - job_search/dashboard.py
- [[test_dashboard_ingest.py]] - code - job_search/tests/test_dashboard_ingest.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Test_Dashboard_Ingest
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Ingest Cycle Dashboard]]
- 2 edges to [[_COMMUNITY_Dashboard Job Export]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]

## Top bridge nodes
- [[build_ingest_cycle_command()]] - degree 12, connects to 3 communities
- [[test_dashboard_ingest.py]] - degree 6, connects to 2 communities
- [[dot-test_parses_step_json_blocks()]] - degree 2, connects to 1 community