---
source_file: "job_search/dashboard.py"
type: "code"
community: "Ingest Cycle Dashboard"
location: "L1049"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Ingest_Cycle_Dashboard
---

# pipeline_fallback_eligible()

## Connections
- [[dot-test_false_when_panel_already_rendered()]] - `calls` [EXTRACTED]
- [[dot-test_skips_when_apply_dialog_open()]] - `calls` [EXTRACTED]
- [[dot-test_true_when_dialog_closed_and_pipeline_queued()]] - `calls` [EXTRACTED]
- [[True when the page-level fallback should render the active pipeline.]] - `rationale_for` [EXTRACTED]
- [[_pipeline_poll_fast_path_active()]] - `calls` [EXTRACTED]
- [[dashboard.py]] - `contains` [EXTRACTED]
- [[render_pipeline_panel_fallback()]] - `calls` [EXTRACTED]
- [[test_dashboard_applied_roles.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Ingest_Cycle_Dashboard