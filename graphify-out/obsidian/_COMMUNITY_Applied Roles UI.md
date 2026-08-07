---
type: community
members: 18
---

# Applied Roles UI

**Members:** 18 nodes

## Members
- [[dot-test_bulk_deanonymize_command_requires_two_drafted()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_bulk_deanonymize_command_single_run_returns_none()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_count_applied_roles_by_status_group()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_default_status_filters_split_drafts_and_applied()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_filter_applied_roles_df()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_row_dict_for_apply_from_app()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_status_badge_markdown()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Build a job row dict suitable for ``execute_apply_pipeline`` from an…]] - rationale - job_search/dashboard.py
- [[Collapsible applied-roles list with status filter and compact rows.]] - rationale - job_search/dashboard.py
- [[Combined ``cv apply`` command for drafted rows with CV run IDs in notes.]] - rationale - job_search/dashboard.py
- [[Drafts and applied-role lists for the current CV track.]] - rationale - job_search/dashboard.py
- [[TestAppliedRolesHelpers]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[_count_applied_roles()]] - code - job_search/dashboard.py
- [[_render_applied_roles_subsection()]] - code - job_search/dashboard.py
- [[bulk_deanonymize_command()]] - code - job_search/dashboard.py
- [[filter_applied_roles_df()]] - code - job_search/dashboard.py
- [[render_applied_roles_section()]] - code - job_search/dashboard.py
- [[row_dict_for_apply_from_app()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Applied_Roles_UI
SORT file.name ASC
```

## Connections to other communities
- 10 edges to [[_COMMUNITY_Dashboard Job Export]]
- 6 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 5 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 1 edge to [[_COMMUNITY_Pipeline Queue Metrics]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]
- 1 edge to [[_COMMUNITY_Dashboard DB Loaders]]

## Top bridge nodes
- [[bulk_deanonymize_command()]] - degree 8, connects to 3 communities
- [[row_dict_for_apply_from_app()]] - degree 7, connects to 3 communities
- [[render_applied_roles_section()]] - degree 6, connects to 3 communities
- [[filter_applied_roles_df()]] - degree 5, connects to 3 communities
- [[_count_applied_roles()]] - degree 5, connects to 3 communities