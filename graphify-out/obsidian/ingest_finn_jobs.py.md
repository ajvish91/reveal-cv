---
source_file: "job_search/ingest_finn_jobs.py"
type: "code"
community: "FINN Search Queries"
location: "L1"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/FINN_Search_Queries
---

# ingest_finn_jobs.py

## Connections
- [[FinnJobSession]] - `imports` [EXTRACTED]
- [[build_job_url()]] - `imports` [EXTRACTED]
- [[coerce_expires_value()]] - `imports` [EXTRACTED]
- [[collect_ingest_keywords()]] - `imports` [EXTRACTED]
- [[configure_logging()]] - `imports` [EXTRACTED]
- [[connect()]] - `imports` [EXTRACTED]
- [[cv_loader.py]] - `imports_from` [EXTRACTED]
- [[deadline_utils.py]] - `imports_from` [EXTRACTED]
- [[finn_job_client.py]] - `imports_from` [EXTRACTED]
- [[finn_search_queries.py]] - `imports_from` [EXTRACTED]
- [[get_logger()]] - `imports` [EXTRACTED]
- [[haystack_for_filter()]] - `imports` [EXTRACTED]
- [[ingest_common.py]] - `imports_from` [EXTRACTED]
- [[ingest_keywords.py]] - `imports_from` [EXTRACTED]
- [[ingest_nav_jobs.py]] - `imports_from` [EXTRACTED]
- [[init_schema()]] - `imports` [EXTRACTED]
- [[job_db.py]] - `imports_from` [EXTRACTED]
- [[job_filters.py]] - `imports_from` [EXTRACTED]
- [[load_default_profiles()]] - `imports` [EXTRACTED]
- [[load_queries()]] - `contains` [EXTRACTED]
- [[location_guess_rogaland()]] - `contains` [EXTRACTED]
- [[location_preferences.py]] - `imports_from` [EXTRACTED]
- [[log_json_summary()]] - `imports` [EXTRACTED]
- [[logging_config.py]] - `imports_from` [EXTRACTED]
- [[main()_11]] - `contains` [EXTRACTED]
- [[mark_stale_jobs_inactive()]] - `imports` [EXTRACTED]
- [[match_preferred_location()]] - `imports` [EXTRACTED]
- [[matches_any_include_term()]] - `imports` [EXTRACTED]
- [[matches_exclude_terms()]] - `imports` [EXTRACTED]
- [[matching_terms()]] - `imports` [EXTRACTED]
- [[merge_exclude_terms()]] - `imports` [EXTRACTED]
- [[merge_include_terms()]] - `imports` [EXTRACTED]
- [[merged_preferred_locations()]] - `imports` [EXTRACTED]
- [[normalize_haystack()]] - `imports` [EXTRACTED]
- [[parse_location_guess()]] - `contains` [EXTRACTED]
- [[row_from_detail()]] - `contains` [EXTRACTED]
- [[row_from_search_card()]] - `contains` [EXTRACTED]
- [[run()]] - `contains` [EXTRACTED]
- [[set_state()]] - `imports` [EXTRACTED]
- [[strip_html()]] - `imports` [EXTRACTED]
- [[test_finn_ingest.py]] - `imports_from` [EXTRACTED]
- [[upsert_job()]] - `imports` [EXTRACTED]
- [[utc_now_iso()_1]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/FINN_Search_Queries