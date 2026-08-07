---
type: community
members: 10
---

# Test Dashboard Debug

**Members:** 10 nodes

## Members
- [[dot-test_debug_log_appends_to_session_ring_buffer()]] - code - job_search/tests/test_dashboard_debug.py
- [[dot-test_debug_log_redacts_sensitive_fields()]] - code - job_search/tests/test_dashboard_debug.py
- [[dot-test_debug_log_writes_file_when_enabled()]] - code - job_search/tests/test_dashboard_debug.py
- [[dot-test_env_var_enables_debug()]] - code - job_search/tests/test_dashboard_debug.py
- [[dot-test_log_state_diff_records_only_changes()]] - code - job_search/tests/test_dashboard_debug.py
- [[dot-test_start_rerun_trace_attaches_rerun_id_and_scope()]] - code - job_search/tests/test_dashboard_debug.py
- [[dot-test_summarize_recent_reruns_groups_events()]] - code - job_search/tests/test_dashboard_debug.py
- [[TestDashboardDebug]] - code - job_search/tests/test_dashboard_debug.py
- [[Tests for dashboard debug tracing helpers.]] - rationale - job_search/tests/test_dashboard_debug.py
- [[test_dashboard_debug.py]] - code - job_search/tests/test_dashboard_debug.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Test_Dashboard_Debug
SORT file.name ASC
```

## Connections to other communities
- 1 edge to [[_COMMUNITY_Dashboard Debug Trace]]

## Top bridge nodes
- [[test_dashboard_debug.py]] - degree 3, connects to 1 community