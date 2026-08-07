---
source_file: "job_search/ingest_nav_jobs.py"
type: "code"
community: "NAV Job Ingest"
location: "L1"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/NAV_Job_Ingest
---

# ingest_nav_jobs.py

## Connections
- [[NavFeedSession]] - `imports` [EXTRACTED]
- [[coerce_expires_value()]] - `imports` [EXTRACTED]
- [[collect_ingest_keywords()]] - `imports` [EXTRACTED]
- [[configure_logging()]] - `imports` [EXTRACTED]
- [[connect()]] - `imports` [EXTRACTED]
- [[cv_loader.py]] - `imports_from` [EXTRACTED]
- [[datetime]] - `imports_from` [EXTRACTED]
- [[deadline_utils.py]] - `imports_from` [EXTRACTED]
- [[default_if_modified_since()]] - `imports` [EXTRACTED]
- [[effective_if_modified_since()]] - `contains` [EXTRACTED]
- [[feed_item_rogaland_guess()]] - `contains` [EXTRACTED]
- [[get_logger()]] - `imports` [EXTRACTED]
- [[get_state()]] - `imports` [EXTRACTED]
- [[haystack_for_filter()]] - `imports` [EXTRACTED]
- [[ingest_common.py]] - `imports_from` [EXTRACTED]
- [[ingest_finn_jobs.py]] - `imports_from` [EXTRACTED]
- [[ingest_keywords.py]] - `imports_from` [EXTRACTED]
- [[init_schema()]] - `imports` [EXTRACTED]
- [[job_db.py]] - `imports_from` [EXTRACTED]
- [[job_filters.py]] - `imports_from` [EXTRACTED]
- [[keyword_match()]] - `contains` [EXTRACTED]
- [[load_default_profiles()]] - `imports` [EXTRACTED]
- [[location_preferences.py]] - `imports_from` [EXTRACTED]
- [[log_json_summary()]] - `imports` [EXTRACTED]
- [[logging_config.py]] - `imports_from` [EXTRACTED]
- [[main()_12]] - `contains` [EXTRACTED]
- [[mark_stale_jobs_inactive()]] - `imports` [EXTRACTED]
- [[match_preferred_location()]] - `imports` [EXTRACTED]
- [[matches_any_include_term()]] - `imports` [EXTRACTED]
- [[matches_exclude_terms()]] - `imports` [EXTRACTED]
- [[matching_terms()]] - `imports` [EXTRACTED]
- [[merge_exclude_terms()]] - `imports` [EXTRACTED]
- [[merge_include_terms()]] - `imports` [EXTRACTED]
- [[merged_preferred_locations()]] - `imports` [EXTRACTED]
- [[nav_feed_client.py]] - `imports_from` [EXTRACTED]
- [[normalize_haystack()]] - `contains` [EXTRACTED]
- [[parse_state_timestamp()]] - `contains` [EXTRACTED]
- [[rogaland_from_locations()]] - `contains` [EXTRACTED]
- [[run()_1]] - `contains` [EXTRACTED]
- [[set_state()]] - `imports` [EXTRACTED]
- [[strip_html()]] - `contains` [EXTRACTED]
- [[test_job_search_pipeline.py]] - `imports_from` [EXTRACTED]
- [[upsert_job()]] - `imports` [EXTRACTED]
- [[utc_now_iso()_1]] - `imports` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/NAV_Job_Ingest