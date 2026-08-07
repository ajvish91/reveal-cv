---
source_file: "job_search/dashboard.py"
type: "rationale"
community: "Pipeline Queue Metrics"
location: "L1374"
tags:
  - graphify/rationale
  - graphify/EXTRACTED
  - community/Pipeline_Queue_Metrics
---

# Sync worker progress first, then only mark orphaned if nothing is alive.

## Connections
- [[_sync_then_recover_pipeline()]] - `rationale_for` [EXTRACTED]

#graphify/rationale #graphify/EXTRACTED #community/Pipeline_Queue_Metrics