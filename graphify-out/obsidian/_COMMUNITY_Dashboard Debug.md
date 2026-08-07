---
type: community
members: 3
---

# Dashboard Debug

**Members:** 3 nodes

## Members
- [[Stable short hash for debug-visible cache keys and filters.]] - rationale - job_search/dashboard_debug.py
- [[_hash_text()]] - code - job_search/dashboard_debug.py
- [[short_fingerprint()]] - code - job_search/dashboard_debug.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard_Debug
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Dashboard Debug Trace]]
- 2 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 1 edge to [[_COMMUNITY_Dashboard Job Export]]

## Top bridge nodes
- [[short_fingerprint()]] - degree 7, connects to 3 communities
- [[_hash_text()]] - degree 2, connects to 1 community