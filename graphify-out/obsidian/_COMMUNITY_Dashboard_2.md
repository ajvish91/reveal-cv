---
type: community
members: 4
---

# Dashboard

**Members:** 4 nodes

## Members
- [[Rebuild enough dialog state to reopen pipeline progressresults from the page.]] - rationale - job_search/dashboard.py
- [[Reopen the existing ApplyModify dialog for the active pipeline.]] - rationale - job_search/dashboard.py
- [[_open_pipeline_dialog()]] - code - job_search/dashboard.py
- [[_restore_pipeline_dialog_context()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Dashboard Job Export]]
- 1 edge to [[_COMMUNITY_Dashboard Debug Trace]]
- 1 edge to [[_COMMUNITY_Pipeline Queue Metrics]]

## Top bridge nodes
- [[_open_pipeline_dialog()]] - degree 5, connects to 3 communities
- [[_restore_pipeline_dialog_context()]] - degree 3, connects to 1 community