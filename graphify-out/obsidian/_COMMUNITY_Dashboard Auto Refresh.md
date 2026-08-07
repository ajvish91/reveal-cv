---
type: community
members: 23
---

# Dashboard Auto Refresh

**Members:** 23 nodes

## Members
- [[dot-test_default_off_with_standard_intervals()]] - code - job_search/tests/test_dashboard_refresh.py
- [[dot-test_disabled_interval_never_refreshes()]] - code - job_search/tests/test_dashboard_refresh.py
- [[dot-test_due_after_interval()]] - code - job_search/tests/test_dashboard_refresh.py
- [[dot-test_due_at_interval_boundary()]] - code - job_search/tests/test_dashboard_refresh.py
- [[dot-test_not_due_before_interval()]] - code - job_search/tests/test_dashboard_refresh.py
- [[dot-test_off_and_interval_labels()]] - code - job_search/tests/test_dashboard_refresh.py
- [[dot-test_off_returns_none()]] - code - job_search/tests/test_dashboard_refresh.py
- [[dot-test_positive_minutes_to_seconds()]] - code - job_search/tests/test_dashboard_refresh.py
- [[Dashboard data refresh helpers (no Streamlit dependency).]] - rationale - job_search/dashboard_refresh.py
- [[Return interval length in seconds, or ``None`` when auto-refresh is off.]] - rationale - job_search/dashboard_refresh.py
- [[Sidebar toggle for periodic cache refresh (does not run ingest).]] - rationale - job_search/dashboard.py
- [[TestAutoRefreshOptions]] - code - job_search/tests/test_dashboard_refresh.py
- [[TestFormatAutoRefreshLabel]] - code - job_search/tests/test_dashboard_refresh.py
- [[TestRefreshIntervalSeconds]] - code - job_search/tests/test_dashboard_refresh.py
- [[TestShouldPeriodicRefresh]] - code - job_search/tests/test_dashboard_refresh.py
- [[Tests for dashboard periodic refresh helpers (no Streamlit runtime).]] - rationale - job_search/tests/test_dashboard_refresh.py
- [[True when ``now_monotonic`` is at or past the next scheduled cache refresh.]] - rationale - job_search/dashboard_refresh.py
- [[dashboard_refresh.py]] - code - job_search/dashboard_refresh.py
- [[format_auto_refresh_label()]] - code - job_search/dashboard_refresh.py
- [[refresh_interval_seconds()]] - code - job_search/dashboard_refresh.py
- [[render_auto_refresh_sidebar_section()]] - code - job_search/dashboard.py
- [[should_periodic_refresh()]] - code - job_search/dashboard_refresh.py
- [[test_dashboard_refresh.py]] - code - job_search/tests/test_dashboard_refresh.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard_Auto_Refresh
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Dashboard Job Export]]
- 1 edge to [[_COMMUNITY_Dashboard Search Cache]]

## Top bridge nodes
- [[render_auto_refresh_sidebar_section()]] - degree 4, connects to 2 communities
- [[should_periodic_refresh()]] - degree 10, connects to 1 community
- [[dashboard_refresh.py]] - degree 6, connects to 1 community
- [[format_auto_refresh_label()]] - degree 5, connects to 1 community