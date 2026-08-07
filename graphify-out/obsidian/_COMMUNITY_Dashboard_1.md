---
type: community
members: 10
---

# Dashboard

**Members:** 10 nodes

## Members
- [[Cancel button on_click — clears flags before main() so fast path is skipped.]] - rationale - job_search/dashboard.py
- [[Clear dialog flags immediately; optionally drop completed pipeline UI state.…]] - rationale - job_search/dashboard.py
- [[Close result dialog but keep finished pipeline state reopenable from the page.]] - rationale - job_search/dashboard.py
- [[Request scroll restore on the next full dashboard render (e.g. after dialog…]] - rationale - job_search/dashboard.py
- [[_dismiss_apply_modify_dialog()]] - code - job_search/dashboard.py
- [[_mark_dashboard_scroll_restore()]] - code - job_search/dashboard.py
- [[_on_apply_dialog_cancel_click()]] - code - job_search/dashboard.py
- [[_on_apply_dialog_close_click()]] - code - job_search/dashboard.py
- [[_on_apply_dialog_dismiss()]] - code - job_search/dashboard.py
- [[st.dialog X  Esc drop dialog flags only (pipeline keeps running).]] - rationale - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard
SORT file.name ASC
```

## Connections to other communities
- 5 edges to [[_COMMUNITY_Dashboard Job Export]]
- 2 edges to [[_COMMUNITY_Dashboard Debug Trace]]
- 2 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]

## Top bridge nodes
- [[_dismiss_apply_modify_dialog()]] - degree 8, connects to 3 communities
- [[_mark_dashboard_scroll_restore()]] - degree 4, connects to 2 communities
- [[_on_apply_dialog_cancel_click()]] - degree 4, connects to 2 communities
- [[_on_apply_dialog_close_click()]] - degree 4, connects to 2 communities
- [[_on_apply_dialog_dismiss()]] - degree 3, connects to 1 community