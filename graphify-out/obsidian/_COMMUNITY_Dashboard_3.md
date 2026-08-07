---
type: community
members: 4
---

# Dashboard

**Members:** 4 nodes

## Members
- [[Copy ``text`` via browser clipboard API (runs in the app document).]] - rationale - job_search/dashboard.py
- [[Show a bash command with an adjacent Copy button.]] - rationale - job_search/dashboard.py
- [[_copy_text_to_clipboard()]] - code - job_search/dashboard.py
- [[_render_copyable_bash_command()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard
SORT file.name ASC
```

## Connections to other communities
- 2 edges to [[_COMMUNITY_Dashboard Job Export]]
- 1 edge to [[_COMMUNITY_Pipeline Queue Metrics]]

## Top bridge nodes
- [[_render_copyable_bash_command()]] - degree 4, connects to 2 communities
- [[_copy_text_to_clipboard()]] - degree 3, connects to 1 community