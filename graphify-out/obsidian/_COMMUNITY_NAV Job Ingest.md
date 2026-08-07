---
type: community
members: 33
---

# NAV Job Ingest

**Members:** 33 nodes

## Members
- [[dot-test_configure_logging_writes_to_file()]] - code - job_search/tests/test_logging_config.py
- [[dot-test_log_json_summary_does_not_crash()]] - code - job_search/tests/test_logging_config.py
- [[dot-test_tail_log_file_returns_last_lines()]] - code - job_search/tests/test_logging_config.py
- [[Any_13]] - code
- [[Central logging configuration for the job_search package.]] - rationale - job_search/logging_config.py
- [[Configure the ``job_search`` logger tree (file + optional stderr).]] - rationale - job_search/logging_config.py
- [[Log an ingestscore summary dict (also printed to stdout by callers).]] - rationale - job_search/logging_config.py
- [[Logger]] - code
- [[LoggingConfigTests]] - code - job_search/tests/test_logging_config.py
- [[Namespace_9]] - code
- [[Path_26]] - code
- [[Return a child logger under the ``job_search`` namespace.]] - rationale - job_search/logging_config.py
- [[Return the last lines from the job search log (read-only).]] - rationale - job_search/logging_config.py
- [[Tests for job_search.logging_config.]] - rationale - job_search/tests/test_logging_config.py
- [[_resolve_level()]] - code - job_search/logging_config.py
- [[configure_logging()]] - code - job_search/logging_config.py
- [[datetime]] - code
- [[effective_if_modified_since()]] - code - job_search/ingest_nav_jobs.py
- [[feed_item_rogaland_guess()]] - code - job_search/ingest_nav_jobs.py
- [[get_logger()]] - code - job_search/logging_config.py
- [[ingest_nav_jobs.py]] - code - job_search/ingest_nav_jobs.py
- [[keyword_match()]] - code - job_search/ingest_nav_jobs.py
- [[log_json_summary()]] - code - job_search/logging_config.py
- [[logging_config.py]] - code - job_search/logging_config.py
- [[main()_12]] - code - job_search/ingest_nav_jobs.py
- [[main()_16]] - code - scripts/run_job_search_cycle.py
- [[parse_state_timestamp()]] - code - job_search/ingest_nav_jobs.py
- [[rogaland_from_locations()]] - code - job_search/ingest_nav_jobs.py
- [[run()_1]] - code - job_search/ingest_nav_jobs.py
- [[run_job_search_cycle.py]] - code - scripts/run_job_search_cycle.py
- [[run_step()]] - code - scripts/run_job_search_cycle.py
- [[tail_log_file()]] - code - job_search/logging_config.py
- [[test_logging_config.py]] - code - job_search/tests/test_logging_config.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/NAV_Job_Ingest
SORT file.name ASC
```

## Connections to other communities
- 23 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 22 edges to [[_COMMUNITY_FINN Search Queries]]
- 7 edges to [[_COMMUNITY_Academic Job Filters]]
- 6 edges to [[_COMMUNITY_Ingest Keyword Collect]]
- 5 edges to [[_COMMUNITY_Location Preferences]]
- 5 edges to [[_COMMUNITY_NAV Feed Client]]
- 4 edges to [[_COMMUNITY_Dashboard Job Export]]
- 2 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 2 edges to [[_COMMUNITY_FINN Job Client]]
- 1 edge to [[_COMMUNITY_Deadline Urgency Utils]]

## Top bridge nodes
- [[ingest_nav_jobs.py]] - degree 44, connects to 7 communities
- [[run()_1]] - degree 29, connects to 6 communities
- [[configure_logging()]] - degree 17, connects to 4 communities
- [[logging_config.py]] - degree 13, connects to 4 communities
- [[get_logger()]] - degree 12, connects to 4 communities