---
type: community
members: 62
---

# Academic Job Filters

**Members:** 62 nodes

## Members
- [[dot-test_academic_terms_list_covers_posting_titles()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_apply_dashboard_filters_academic_only()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_bim_coordinator_not_academic_display()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_blocks_phd_student_ads()]] - code - job_search/tests/test_phd_student_filter.py
- [[dot-test_broad_include_terms_still_cover_legacy_sql()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_butikkmedarbeider_excluded()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_description_forskning_alone_not_academic_display()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_effective_academic_roles_only_on_academic_track()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_fastlege_excluded()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_finance_controller_excluded()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_forsvar_infrastructure_engineer_not_academic()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_haystack_tolerates_nan_and_non_strings()]] - code - job_search/tests/test_phd_student_filter.py
- [[dot-test_industry_data_engineer_not_academic()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_it_controller_kept()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_it_enhetsleder_digitalisering_kept()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_keeps_postdoc_and_researcher()]] - code - job_search/tests/test_phd_student_filter.py
- [[dot-test_marketing_spam_excluded()]] - code - job_search/tests/test_job_filters_relevance.py
- [[dot-test_matches_norwegian_lecturer_titles()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_matches_university_postdoc()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_postdoctoral_fellowship_not_blocked()]] - code - job_search/tests/test_phd_student_filter.py
- [[dot-test_postdoktor_title_matches_academic_and_tech_filters()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_research_assistant_not_academic_display()]] - code - job_search/tests/test_academic_track_filter.py
- [[dot-test_tech_allowlist_covers_agentic_and_academic_roles()]] - code - job_search/tests/test_ingest_keywords.py
- [[AND (instr0 OR ...) — require at least one academic role token.]] - rationale - job_search/job_filters.py
- [[Academic CV track always applies the strict research-role display filter.]] - rationale - job_search/dashboard.py
- [[AcademicRoleFilterTests]] - code - job_search/tests/test_academic_track_filter.py
- [[Coerce filter fields to str; skip NoneNaNnon-strings (pandas empty cells).]] - rationale - job_search/job_filters.py
- [[Drop non-academic rows when keep_academic_only is True (pandas DataFrame).]] - rationale - job_search/job_filters.py
- [[Job text filters for ingest and dashboard. 1) Tech allowlist — showkeep…]] - rationale - job_search/job_filters.py
- [[NoiseBlocklistTests]] - code - job_search/tests/test_job_filters_relevance.py
- [[Pattern]] - code
- [[PhdStudentFilterTests]] - code - job_search/tests/test_phd_student_filter.py
- [[Post-filter overview rows with the same rules as ingest  explorer.]] - rationale - job_search/dashboard.py
- [[Stricter dashboard filter role terms in titlejobtitle, or university employer…]] - rationale - job_search/job_filters.py
- [[Tests for PhD student opening filter.]] - rationale - job_search/tests/test_phd_student_filter.py
- [[Tests for academic role filtering on the dashboard and ingest queries.]] - rationale - job_search/tests/test_academic_track_filter.py
- [[Tests for profile relevance filtering and expanded noise blocklist.]] - rationale - job_search/tests/test_job_filters_relevance.py
- [[True for financeaccounting controller ads; False for ITICT controller roles.]] - rationale - job_search/job_filters.py
- [[True when the posting is a PhD studentfellowship opening (candidate will…]] - rationale - job_search/job_filters.py
- [[True when titledescriptionemployer matches university or research role…]] - rationale - job_search/job_filters.py
- [[_filter_text_part()]] - code - job_search/job_filters.py
- [[_term_pattern()]] - code - job_search/job_filters.py
- [[apply_dashboard_filters()]] - code - job_search/dashboard.py
- [[effective_academic_roles_only()]] - code - job_search/dashboard.py
- [[filter_academic_roles_df()]] - code - job_search/job_filters.py
- [[haystack_for_filter()]] - code - job_search/job_filters.py
- [[haystack_title_employer()]] - code - job_search/job_filters.py
- [[job_filters.py]] - code - job_search/job_filters.py
- [[matches_academic_research_employer()]] - code - job_search/job_filters.py
- [[matches_academic_role()]] - code - job_search/job_filters.py
- [[matches_academic_role_display()]] - code - job_search/job_filters.py
- [[matches_any_include_term()]] - code - job_search/job_filters.py
- [[matches_exclude_terms()]] - code - job_search/job_filters.py
- [[matches_finance_controller()]] - code - job_search/job_filters.py
- [[matches_phd_student_opening()]] - code - job_search/job_filters.py
- [[pandas empty cells are float NaN; must not break ' '.join.]] - rationale - job_search/tests/test_phd_student_filter.py
- [[sql_require_academic_role()]] - code - job_search/job_filters.py
- [[term_hits()]] - code - job_search/score_jobs.py
- [[term_matches()]] - code - job_search/job_filters.py
- [[test_academic_track_filter.py]] - code - job_search/tests/test_academic_track_filter.py
- [[test_job_filters_relevance.py]] - code - job_search/tests/test_job_filters_relevance.py
- [[test_phd_student_filter.py]] - code - job_search/tests/test_phd_student_filter.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Academic_Job_Filters
SORT file.name ASC
```

## Connections to other communities
- 16 edges to [[_COMMUNITY_FINN Search Queries]]
- 13 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 10 edges to [[_COMMUNITY_Dashboard Job Export]]
- 7 edges to [[_COMMUNITY_NAV Job Ingest]]
- 6 edges to [[_COMMUNITY_Dashboard Search Cache]]
- 6 edges to [[_COMMUNITY_Test Job Filters Relevance]]
- 6 edges to [[_COMMUNITY_Job Filters]]
- 6 edges to [[_COMMUNITY_Ingest Keyword Collect]]
- 3 edges to [[_COMMUNITY_Test Academic Track Filter]]
- 1 edge to [[_COMMUNITY_Apply Artifact Options]]
- 1 edge to [[_COMMUNITY_Location Preferences]]

## Top bridge nodes
- [[job_filters.py]] - degree 34, connects to 7 communities
- [[haystack_for_filter()]] - degree 32, connects to 6 communities
- [[matches_any_include_term()]] - degree 19, connects to 5 communities
- [[term_matches()]] - degree 17, connects to 4 communities
- [[test_academic_track_filter.py]] - degree 15, connects to 4 communities