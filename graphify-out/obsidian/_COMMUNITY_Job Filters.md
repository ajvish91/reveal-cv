---
type: community
members: 10
---

# Job Filters

**Members:** 10 nodes

## Members
- [[AND (instr0 OR ...) — require at least one tech token.]] - rationale - job_search/job_filters.py
- [[SQL fragment exclude rows whose titledescription match PhD-student blocklist.]] - rationale - job_search/job_filters.py
- [[SQL fragment require CV keywordskill overlap (exclude locationTEK-only…]] - rationale - job_search/job_filters.py
- [[SQL pre-filter on titlejobtitleemployer using strict role + university tokens.]] - rationale - job_search/job_filters.py
- [[_jobs_query_fragments()]] - code - job_search/dashboard.py
- [[sql_exclude_fragments()]] - code - job_search/job_filters.py
- [[sql_phd_student_exclude()]] - code - job_search/job_filters.py
- [[sql_require_academic_role_display()]] - code - job_search/job_filters.py
- [[sql_require_any_include()]] - code - job_search/job_filters.py
- [[sql_require_profile_relevance()]] - code - job_search/job_filters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Job_Filters
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Dashboard Job Export]]
- 6 edges to [[_COMMUNITY_Academic Job Filters]]
- 2 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 1 edge to [[_COMMUNITY_Pipeline Queue Metrics]]

## Top bridge nodes
- [[_jobs_query_fragments()]] - degree 9, connects to 3 communities
- [[sql_require_any_include()]] - degree 5, connects to 2 communities
- [[sql_require_profile_relevance()]] - degree 4, connects to 2 communities
- [[sql_phd_student_exclude()]] - degree 4, connects to 2 communities
- [[sql_require_academic_role_display()]] - degree 4, connects to 2 communities