---
type: community
members: 14
---

# Dashboard

**Members:** 14 nodes

## Members
- [[Job explorer isolated so in-section control changes skip overview  applied…]] - rationale - job_search/dashboard.py
- [[Prominent free-text search at the top of Job explorer.]] - rationale - job_search/dashboard.py
- [[Render pagination controls; return (page, start_idx, end_idx_exclusive).]] - rationale - job_search/dashboard.py
- [[Session key tracking prior page so pagination can trigger scroll-to-list.]] - rationale - job_search/dashboard.py
- [[Slice ``df`` for the current page (pagination controls rendered separately).]] - rationale - job_search/dashboard.py
- [[True when Job explorer page index changed since the last render. Compares…]] - rationale - job_search/dashboard.py
- [[_job_explorer_page_changed()]] - code - job_search/dashboard.py
- [[_job_page_scroll_prev_key()]] - code - job_search/dashboard.py
- [[_job_page_state_key()]] - code - job_search/dashboard.py
- [[_render_job_explorer_fragment()]] - code - job_search/dashboard.py
- [[fragment]] - code
- [[paginate_jobs_df()]] - code - job_search/dashboard.py
- [[render_job_explorer_search_bar()]] - code - job_search/dashboard.py
- [[render_job_list_pagination()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_Dashboard Job Export]]
- 6 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 3 edges to [[_COMMUNITY_Dashboard Debug Trace]]
- 2 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 2 edges to [[_COMMUNITY_Dashboard Scroll Styles]]

## Top bridge nodes
- [[_render_job_explorer_fragment()]] - degree 18, connects to 5 communities
- [[render_job_list_pagination()]] - degree 5, connects to 2 communities
- [[paginate_jobs_df()]] - degree 5, connects to 2 communities
- [[_job_page_state_key()]] - degree 5, connects to 1 community
- [[_job_explorer_page_changed()]] - degree 5, connects to 1 community