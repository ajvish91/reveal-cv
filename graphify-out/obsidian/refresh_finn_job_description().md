---
source_file: "job_search/dashboard.py"
type: "code"
community: "Dashboard Job Export"
location: "L1265"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Dashboard_Job_Export
---

# refresh_finn_job_description()

## Connections
- [[Any_6]] - `references` [EXTRACTED]
- [[Fetch FINN detail HTML when the DB row has no description_text.]] - `rationale_for` [EXTRACTED]
- [[FinnJobSession]] - `calls` [EXTRACTED]
- [[_safe_str()]] - `calls` [EXTRACTED]
- [[dashboard.py]] - `contains` [EXTRACTED]
- [[execute_apply_pipeline()]] - `calls` [EXTRACTED]
- [[strip_html()]] - `calls` [EXTRACTED]
- [[upsert_job()]] - `calls` [INFERRED]
- [[utc_now_iso()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Dashboard_Job_Export