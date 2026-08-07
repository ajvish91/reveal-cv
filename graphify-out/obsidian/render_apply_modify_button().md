---
source_file: "job_search/dashboard.py"
type: "code"
community: "Apply Pipeline Options"
location: "L4146"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Apply_Pipeline_Options
---

# render_apply_modify_button()

## Connections
- [[Any_6]] - `references` [EXTRACTED]
- [[Single Apply or Modify button that opens the configuration dialog.]] - `rationale_for` [EXTRACTED]
- [[_pipeline_active_for_job()]] - `calls` [EXTRACTED]
- [[_pipeline_busy()]] - `calls` [EXTRACTED]
- [[_pipeline_waiting_queue()]] - `calls` [EXTRACTED]
- [[_prepare_apply_modify_dialog()]] - `indirect_call` [INFERRED]
- [[_render_apply_form()]] - `calls` [EXTRACTED]
- [[apply_button_label()]] - `calls` [EXTRACTED]
- [[dashboard.py]] - `contains` [EXTRACTED]
- [[pipeline_queue_is_full()]] - `calls` [EXTRACTED]
- [[render_applied_role_row()]] - `calls` [EXTRACTED]
- [[render_compact_job_row()]] - `calls` [EXTRACTED]
- [[render_pipeline_panel()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Apply_Pipeline_Options