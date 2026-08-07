---
source_file: "job_search/dashboard.py"
type: "code"
community: "Dashboard Job Export"
location: "L4336"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Dashboard_Job_Export
---

# _handle_application_status_update()

## Connections
- [[Any_6]] - `references` [EXTRACTED]
- [[Series]] - `references` [EXTRACTED]
- [[Upsert application status, refresh caches, and rerun the dashboard.]] - `rationale_for` [EXTRACTED]
- [[_invalidate_dashboard_data_caches()]] - `calls` [EXTRACTED]
- [[application_status_upsert_row()]] - `calls` [EXTRACTED]
- [[dashboard.py]] - `contains` [EXTRACTED]
- [[render_application_status_controls()]] - `calls` [EXTRACTED]
- [[render_applied_role_row()]] - `calls` [EXTRACTED]
- [[upsert_application()]] - `calls` [INFERRED]

#graphify/code #graphify/EXTRACTED #community/Dashboard_Job_Export