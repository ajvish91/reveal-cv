---
type: community
members: 8
---

# Dashboard

**Members:** 8 nodes

## Members
- [[dot-test_preserves_existing_applied_at()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_rejects_unknown_status()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_sets_applied_at_when_moving_to_applied()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Build ``upsert_application`` payload for a status change. Preserves notes,…]] - rationale - job_search/dashboard.py
- [[Normalize DBpandas cell values to optional stripped text.]] - rationale - job_search/dashboard.py
- [[TestApplicationStatusUpsertRow]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[_sql_optional_text()]] - code - job_search/dashboard.py
- [[application_status_upsert_row()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Dashboard Job Export]]
- 2 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 2 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 1 edge to [[_COMMUNITY_Pipeline Metrics Format]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]

## Top bridge nodes
- [[application_status_upsert_row()]] - degree 12, connects to 4 communities
- [[_sql_optional_text()]] - degree 5, connects to 2 communities
- [[TestApplicationStatusUpsertRow]] - degree 5, connects to 2 communities