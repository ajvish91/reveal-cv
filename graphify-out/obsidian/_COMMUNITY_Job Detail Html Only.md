---
type: community
members: 3
---

# Job Detail Html Only

**Members:** 3 nodes

## Members
- [[FINN HTML-only job detail fixture]] - document - job_search/tests/fixtures/finn/job_detail_html_only.html
- [[Piano Software Norway HTML fixture]] - concept - job_search/tests/fixtures/finn/job_detail_html_only.html
- [[Piano Software Norway MLAI Engineer]] - document - cv_generation/tests/fixtures/legacy_run_no_company/job_posting.txt

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Job_Detail_Html_Only
SORT file.name ASC
```
