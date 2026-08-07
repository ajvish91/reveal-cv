---
type: community
members: 21
---

# Job Dedup Helpers

**Members:** 21 nodes

## Members
- [[dot-test_dedup_key_uses_employer_and_title()]] - code - job_search/tests/test_job_dedup.py
- [[dot-test_dedupe_prefers_higher_score()]] - code - job_search/tests/test_job_dedup.py
- [[dot-test_dedupe_prefers_nav_apply_url_when_scores_tie()]] - code - job_search/tests/test_job_dedup.py
- [[dot-test_normalize_text_strips_punctuation_and_whitespace()]] - code - job_search/tests/test_job_dedup.py
- [[Any_15]] - code
- [[Collapse rows that share the same normalized employer + title. Keeps the…]] - rationale - job_search/job_dedup.py
- [[Cross-source job deduplication (NAV Arbeidsplassen + FINN.no).]] - rationale - job_search/job_dedup.py
- [[DataFrame_1]] - code
- [[Highest score wins; tie-break toward NAV.]] - rationale - job_search/job_dedup.py
- [[JobDedupTests]] - code - job_search/tests/test_job_dedup.py
- [[Lowercase, strip punctuation, collapse whitespace.]] - rationale - job_search/job_dedup.py
- [[Series_1]] - code
- [[_merge_duplicate_fields()]] - code - job_search/job_dedup.py
- [[_pick_primary_index()]] - code - job_search/job_dedup.py
- [[_row_link()]] - code - job_search/job_dedup.py
- [[_source_rank()]] - code - job_search/job_dedup.py
- [[dedup_key()]] - code - job_search/job_dedup.py
- [[dedupe_jobs_df()_1]] - code - job_search/job_dedup.py
- [[job_dedup.py]] - code - job_search/job_dedup.py
- [[normalize_text()]] - code - job_search/job_dedup.py
- [[test_job_dedup.py]] - code - job_search/tests/test_job_dedup.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Job_Dedup_Helpers
SORT file.name ASC
```
