---
type: community
members: 8
---

# Test Academic Track Filter

**Members:** 8 nodes

## Members
- [[dot-test_academic_queries_present()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_both_track_merges_industry_and_academic()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_industry_defaults_unchanged()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_industry_track_omits_academic_only_queries()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_postdoktor_in_academic_finn_queries()]] - code - job_search/tests/test_academic_track_filter.py
- [[AcademicFinnQueryTests]] - code - job_search/tests/test_academic_track_filter.py
- [[FINN queries for ``industry``, ``academic``, or ``both`` (default ingest).]] - rationale - job_search/role_search_config.py
- [[finn_search_queries_for_track()]] - code - job_search/role_search_config.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Test_Academic_Track_Filter
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Ingest Keyword Collect]]
- 3 edges to [[_COMMUNITY_Academic Job Filters]]
- 2 edges to [[_COMMUNITY_FINN Search Queries]]

## Top bridge nodes
- [[finn_search_queries_for_track()]] - degree 8, connects to 3 communities
- [[AcademicFinnQueryTests]] - degree 7, connects to 1 community
- [[dot-test_both_track_merges_industry_and_academic()]] - degree 3, connects to 1 community