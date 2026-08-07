---
type: community
members: 20
---

# Apply Artifact Options

**Members:** 20 nodes

## Members
- [[dot-test_apply_button_label()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_apply_pipeline_options_flags_map_to_expected_fields()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_default_artifact_options_academic()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_default_artifact_options_industry()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_dialog_artifact_bundle_academic_always_shows_docs()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_dialog_artifact_bundle_industry_postdoc_shows_academic_docs()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_dialog_artifact_bundle_industry_skips_jd_dependency()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_is_modify_mode()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[dot-test_row_suggests_academic_documents_postdoktor()]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[Cached JD scan for academic artifact checkboxes (plain industry skips the scan).]] - rationale - job_search/dashboard.py
- [[Industry open path always defaults cover letter without needing JD markers.]] - rationale - job_search/tests/test_dashboard_applied_roles.py
- [[One-shot artifact defaults  existing-file flags for the Apply dialog.]] - rationale - job_search/dashboard.py
- [[Pre-check artifact generation toggles from posting detection.]] - rationale - job_search/dashboard.py
- [[TestApplyModifyHelpers]] - code - job_search/tests/test_dashboard_applied_roles.py
- [[True when titleemployer look like a postdocresearcher call (cheap; no JD…]] - rationale - job_search/dashboard.py
- [[_cached_default_artifact_options()]] - code - job_search/dashboard.py
- [[_dialog_artifact_bundle()]] - code - job_search/dashboard.py
- [[apply_button_label()]] - code - job_search/dashboard.py
- [[default_artifact_options()]] - code - job_search/dashboard.py
- [[row_suggests_academic_documents()]] - code - job_search/dashboard.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Apply_Artifact_Options
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_Apply Pipeline Options]]
- 5 edges to [[_COMMUNITY_Dashboard Job Export]]
- 5 edges to [[_COMMUNITY_Explorer Pipeline Gates]]
- 3 edges to [[_COMMUNITY_Pipeline Queue Metrics]]
- 1 edge to [[_COMMUNITY_Application Artifacts]]
- 1 edge to [[_COMMUNITY_Dashboard DB Loaders]]
- 1 edge to [[_COMMUNITY_Academic Job Filters]]

## Top bridge nodes
- [[row_suggests_academic_documents()]] - degree 8, connects to 5 communities
- [[_dialog_artifact_bundle()]] - degree 13, connects to 4 communities
- [[apply_button_label()]] - degree 5, connects to 4 communities
- [[default_artifact_options()]] - degree 7, connects to 3 communities
- [[TestApplyModifyHelpers]] - degree 11, connects to 2 communities