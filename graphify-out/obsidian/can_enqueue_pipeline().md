---
source_file: "job_search/dashboard.py"
type: "code"
community: "Explorer Pipeline Gates"
location: "L619"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Explorer_Pipeline_Gates
---

# can_enqueue_pipeline()

## Connections
- [[dot-test_can_enqueue_idle_starts_ok()]] - `calls` [EXTRACTED]
- [[dot-test_can_enqueue_rejects_duplicate_active_and_waiting()]] - `calls` [EXTRACTED]
- [[dot-test_can_enqueue_rejects_when_full_or_ingest()]] - `calls` [EXTRACTED]
- [[Any_6]] - `references` [EXTRACTED]
- [[Return ``(ok, reason)`` for starting or enqueueing ``job_key``. When idle…]] - `rationale_for` [EXTRACTED]
- [[_can_enqueue_current_job()]] - `calls` [EXTRACTED]
- [[_queue_apply_pipeline()]] - `calls` [EXTRACTED]
- [[_render_apply_form()]] - `calls` [EXTRACTED]
- [[dashboard.py]] - `contains` [EXTRACTED]
- [[pipeline_queue_is_full()]] - `calls` [EXTRACTED]
- [[test_dashboard_applied_roles.py]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Explorer_Pipeline_Gates