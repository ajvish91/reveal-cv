---
type: community
members: 9
---

# Test Job Filters Relevance

**Members:** 9 nodes

## Members
- [[dot-test_apply_dashboard_filters_drops_location_only()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_keyword_match_is_relevant()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_location_only_score_is_not_relevant()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_tek_boost_with_keyword_overlap_is_relevant()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_tek_boost_without_keywords_is_not_relevant()]] - code - job_search/tests/test_job_filters_relevance.py
- [[Any_16]] - code
- [[ProfileRelevanceTests]] - code - job_search/tests/test_job_filters_relevance.py
- [[True when a scored job has CV keywordskill overlap. Location-only (+5) and…]] - rationale - job_search/job_filters.py
- [[has_profile_relevance()]] - code - job_search/job_filters.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Test_Job_Filters_Relevance
SORT file.name ASC
```

## Connections to other communities
- 6 edges to [[_COMMUNITY_Academic Job Filters]]
- 1 edge to [[_COMMUNITY_Dashboard Job Export]]

## Top bridge nodes
- [[has_profile_relevance()]] - degree 10, connects to 2 communities
- [[ProfileRelevanceTests]] - degree 6, connects to 1 community
- [[Any_16]] - degree 2, connects to 1 community
- [[dot-test_apply_dashboard_filters_drops_location_only()]] - degree 2, connects to 1 community