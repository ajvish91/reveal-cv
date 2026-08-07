---
type: community
members: 30
---

# FINN Search Queries

**Members:** 30 nodes

## Members
- [[dot-test_row_from_detail_maps_db_fields()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_row_from_search_card_without_detail()]] - code - job_search/tests/test_finn_ingest.py
- [[Any_8]] - code
- [[Any_11]] - code
- [[Any_12]] - code
- [[Default FINN.no search queries tuned from application history.]] - rationale - job_search/finn_search_queries.py
- [[Mark ACTIVE rows for source not seen in the current ingest run as INACTIVE.]] - rationale - job_search/ingest_common.py
- [[Namespace_8]] - code
- [[Normalize expires  validThrough from DB, API, or JSON-LD to a plain string or…]] - rationale - job_search/deadline_utils.py
- [[Shared helpers for job ingest scripts (NAV, FINN, …).]] - rationale - job_search/ingest_common.py
- [[build_job_url()]] - code - job_search/finn_job_client.py
- [[coerce_expires_value()]] - code - job_search/deadline_utils.py
- [[finn_search_queries.py]] - code - job_search/finn_search_queries.py
- [[ingest_common.py]] - code - job_search/ingest_common.py
- [[ingest_finn_jobs.py]] - code - job_search/ingest_finn_jobs.py
- [[load_queries()]] - code - job_search/ingest_finn_jobs.py
- [[location_guess_rogaland()]] - code - job_search/ingest_finn_jobs.py
- [[main()_11]] - code - job_search/ingest_finn_jobs.py
- [[mark_stale_jobs_inactive()]] - code - job_search/ingest_common.py
- [[matching_terms()]] - code - job_search/job_filters.py
- [[merge_exclude_terms()]] - code - job_search/job_filters.py
- [[merge_include_terms()]] - code - job_search/job_filters.py
- [[normalize_haystack()]] - code - job_search/ingest_nav_jobs.py
- [[parse_location_guess()]] - code - job_search/ingest_finn_jobs.py
- [[parse_term_field()]] - code - job_search/job_filters.py
- [[row_from_detail()]] - code - job_search/ingest_finn_jobs.py
- [[row_from_search_card()]] - code - job_search/ingest_finn_jobs.py
- [[run()]] - code - job_search/ingest_finn_jobs.py
- [[strip_html()]] - code - job_search/ingest_nav_jobs.py
- [[test_finn_ingest.py]] - code - job_search/tests/test_finn_ingest.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/FINN_Search_Queries
SORT file.name ASC
```

## Connections to other communities
- 22 edges to [[_COMMUNITY_NAV Job Ingest]]
- 21 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 18 edges to [[_COMMUNITY_FINN Job Client]]
- 16 edges to [[_COMMUNITY_Academic Job Filters]]
- 8 edges to [[_COMMUNITY_Ingest Keyword Collect]]
- 7 edges to [[_COMMUNITY_Dashboard Job Export]]
- 6 edges to [[_COMMUNITY_Location Preferences]]
- 5 edges to [[_COMMUNITY_Deadline Urgency Utils]]
- 2 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 2 edges to [[_COMMUNITY_Test Academic Track Filter]]

## Top bridge nodes
- [[ingest_finn_jobs.py]] - degree 43, connects to 7 communities
- [[run()]] - degree 20, connects to 5 communities
- [[merge_include_terms()]] - degree 8, connects to 4 communities
- [[merge_exclude_terms()]] - degree 8, connects to 4 communities
- [[coerce_expires_value()]] - degree 12, connects to 3 communities