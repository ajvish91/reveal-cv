---
type: community
members: 14
---

# Dashboard

**Members:** 14 nodes

## Members
- [[dot-test_display_title()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_notice_id_is_stable()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_result_details_include_existing_artifacts()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Human-readable job label for status bar  queue captions.]] - rationale - job_search/dashboard.py
- [[Prefer a parked completion (queue advanced); else the idle finished pipeline.]] - rationale - job_search/dashboard.py
- [[Reopen result UI for a finished job (including after queue advanced).]] - rationale - job_search/dashboard.py
- [[TestPipelineResultDetails]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Top-of-page successerror banner for a finished pipeline when dialog is closed.]] - rationale - job_search/dashboard.py
- [[_completion_notice_payload()]] - code - job_search/dashboard.py
- [[_dismiss_pipeline_notice()]] - code - job_search/dashboard.py
- [[_open_completion_notice_dialog()]] - code - job_search/dashboard.py
- [[_render_pipeline_completion_notice()]] - code - job_search/dashboard.py
- [[pipeline_job_display_title()]] - code - job_search/dashboard.py
- [[pipeline_notice_id()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Dashboard
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Dashboard Job Export]]
- 4 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 4 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]
- 1 edge to [[_COMMUNITY_Dashboard Debug Trace]]
- 1 edge to [[_COMMUNITY_Dashboard Search Cache]]

## Top bridge nodes
- [[pipeline_job_display_title()]] - degree 7, connects to 3 communities
- [[_render_pipeline_completion_notice()]] - degree 8, connects to 2 communities
- [[_completion_notice_payload()]] - degree 6, connects to 2 communities
- [[pipeline_notice_id()]] - degree 5, connects to 2 communities
- [[_open_completion_notice_dialog()]] - degree 5, connects to 2 communities