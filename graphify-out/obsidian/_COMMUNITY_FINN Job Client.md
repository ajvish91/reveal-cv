---
type: community
members: 45
---

# FINN Job Client

**Members:** 45 nodes

## Members
- [[dot-__init__()_2]] - code - job_search/finn_job_client.py
- [[dot-_rate_limit()]] - code - job_search/finn_job_client.py
- [[dot-fetch_job_detail()]] - code - job_search/finn_job_client.py
- [[dot-fetch_text()]] - code - job_search/finn_job_client.py
- [[dot-search_jobs()]] - code - job_search/finn_job_client.py
- [[dot-test_build_search_url()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_default_queries_cover_application_lanes()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_extract_finnkode()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_finn_session_uses_fixture_html()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_load_queries_prefers_cli_over_defaults()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_parse_job_detail_html_fallback()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_parse_job_posting_json_ld()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_parse_search_cards_dedupes_and_extracts_fields()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_parse_search_cards_live_markup()]] - code - job_search/tests/test_finn_ingest.py
- [[dot-test_parse_wrapped_json_ld_job_posting()]] - code - job_search/tests/test_finn_ingest.py
- [[Any_10]] - code
- [[Extract job cards from a FINN search results page.]] - rationale - job_search/finn_job_client.py
- [[Fallback detail parse when JSON-LD JobPosting is missing.]] - rationale - job_search/finn_job_client.py
- [[FinnIngestTests]] - code - job_search/tests/test_finn_ingest.py
- [[FinnJobSession]] - code - job_search/finn_job_client.py
- [[HTMLParser]] - code
- [[HTTP client for FINN.no job search (HTML scrape + JSON-LD detail parse).]] - rationale - job_search/finn_job_client.py
- [[HTTPError]] - code
- [[SSLContext]] - code
- [[_address_fields()]] - code - job_search/finn_job_client.py
- [[_card_text()]] - code - job_search/finn_job_client.py
- [[_collect_schema_objects()]] - code - job_search/finn_job_client.py
- [[_detail_title()]] - code - job_search/finn_job_client.py
- [[_first_place()]] - code - job_search/finn_job_client.py
- [[_is_job_posting()]] - code - job_search/finn_job_client.py
- [[_iter_json_ld_objects()]] - code - job_search/finn_job_client.py
- [[_meta_content()]] - code - job_search/finn_job_client.py
- [[_org_name()]] - code - job_search/finn_job_client.py
- [[_parse_og_title_segments()]] - code - job_search/finn_job_client.py
- [[_should_retry_http_error()]] - code - job_search/finn_job_client.py
- [[_ssl_context()]] - code - job_search/finn_job_client.py
- [[_unwrap_json_ld_payload()]] - code - job_search/finn_job_client.py
- [[build_search_url()]] - code - job_search/finn_job_client.py
- [[extract_finnkode()]] - code - job_search/finn_job_client.py
- [[finn_job_client.py]] - code - job_search/finn_job_client.py
- [[http_get_text()]] - code - job_search/finn_job_client.py
- [[merge_job_detail()]] - code - job_search/finn_job_client.py
- [[parse_job_detail_html()]] - code - job_search/finn_job_client.py
- [[parse_job_posting_json_ld()]] - code - job_search/finn_job_client.py
- [[parse_search_cards()]] - code - job_search/finn_job_client.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/FINN_Job_Client
SORT file.name ASC
```

## Connections to other communities
- 18 edges to [[_COMMUNITY_FINN Search Queries]]
- 2 edges to [[_COMMUNITY_Dashboard Job Export]]
- 2 edges to [[_COMMUNITY_NAV Job Ingest]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]
- 1 edge to [[_COMMUNITY_Ingest Cycle Dashboard]]
- 1 edge to [[_COMMUNITY_Dashboard DB Loaders]]

## Top bridge nodes
- [[FinnJobSession]] - degree 15, connects to 4 communities
- [[finn_job_client.py]] - degree 27, connects to 2 communities
- [[FinnIngestTests]] - degree 15, connects to 2 communities
- [[parse_job_detail_html()]] - degree 11, connects to 1 community
- [[parse_job_posting_json_ld()]] - degree 11, connects to 1 community