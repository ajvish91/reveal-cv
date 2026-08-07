---
source_file: "job_search/dashboard.py"
type: "code"
community: "Dashboard"
location: "L3501"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Dashboard
---

# _render_pipeline_completion_notice()

## Connections
- [[Top-of-page successerror banner for a finished pipeline when dialog is closed.]] - `rationale_for` [EXTRACTED]
- [[_completion_notice_payload()]] - `calls` [EXTRACTED]
- [[_dismiss_pipeline_notice()]] - `indirect_call` [INFERRED]
- [[_open_completion_notice_dialog()]] - `indirect_call` [INFERRED]
- [[dashboard.py]] - `contains` [EXTRACTED]
- [[main()_9]] - `calls` [EXTRACTED]
- [[pipeline_job_display_title()]] - `calls` [EXTRACTED]
- [[pipeline_notice_id()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Dashboard