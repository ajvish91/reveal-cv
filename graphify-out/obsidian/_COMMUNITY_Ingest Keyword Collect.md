---
type: community
members: 41
---

# Ingest Keyword Collect

**Members:** 41 nodes

## Members
- [[dot-test_application_boosts_cover_applied_role_lanes()]] - code - job_search/tests/test_ingest_keywords.py
- [[dot-test_collect_merges_cv_skills_and_application_boosts()]] - code - job_search/tests/test_ingest_keywords.py
- [[dot-test_collect_without_skills_omits_skill_terms()]] - code - job_search/tests/test_ingest_keywords.py
- [[dot-test_demo_profiles_detected()]] - code - job_search/tests/test_ingest_keywords.py
- [[dot-test_finn_academic_queries_merged_by_default()]] - code - job_search/tests/test_ingest_keywords.py
- [[dot-test_finn_queries_cover_application_lanes()]] - code - job_search/tests/test_ingest_keywords.py
- [[dot-test_real_cv_dedupes_overlapping_boosts()]] - code - job_search/tests/test_ingest_keywords.py
- [[dot-test_using_demo_cv_keywords_helper()]] - code - job_search/tests/test_ingest_keywords.py
- [[CLI load and print a summary of default CVs.]] - rationale - shared/cv_loader.py
- [[Curated search and ingest keywords derived from cv_runs application history.…]] - rationale - job_search/role_search_config.py
- [[Directory used as the CV root for load_default_profiles(). Precedence 1.…]] - rationale - shared/cv_loader.py
- [[Expose demo detection for tests and diagnostics.]] - rationale - job_search/ingest_keywords.py
- [[Industry + academic FINN queries (deduped, stable order).]] - rationale - job_search/role_search_config.py
- [[IngestKeywordTests]] - code - job_search/tests/test_ingest_keywords.py
- [[Keywords used by NAVFINN ingest for --keyword-filter matching and --list-…]] - rationale - job_search/ingest_keywords.py
- [[Load industry + academic from resolve_cv_dir() (personal .md preferred over…]] - rationale - shared/cv_loader.py
- [[Merge CV profile keywordsskills with curated application-history boosts for…]] - rationale - job_search/ingest_keywords.py
- [[Path_31]] - code
- [[Prefer stem.md (your real CV); fall back to stem.demo.md (repo template).]] - rationale - shared/cv_loader.py
- [[Split YAML front matter (--- ... ---) from markdown body.]] - rationale - shared/cv_loader.py
- [[True when every loaded profile comes from .demo.md (repo CI  demo mode).]] - rationale - job_search/role_search_config.py
- [[_demo_profile()]] - code - job_search/tests/test_ingest_keywords.py
- [[_dir_has_profiles()]] - code - shared/cv_loader.py
- [[_profile_path()]] - code - shared/cv_loader.py
- [[_real_profile()]] - code - job_search/tests/test_ingest_keywords.py
- [[all_default_finn_search_queries()]] - code - job_search/role_search_config.py
- [[collect_ingest_keywords()]] - code - job_search/ingest_keywords.py
- [[collect_keywords_from_cvs()]] - code - job_search/ingest_keywords.py
- [[cv_loader.py]] - code - shared/cv_loader.py
- [[ingest_keywords.py]] - code - job_search/ingest_keywords.py
- [[load_default_profiles()]] - code - shared/cv_loader.py
- [[load_profile()]] - code - shared/cv_loader.py
- [[main()_17]] - code - shared/cv_loader.py
- [[merge_unique_terms()]] - code - job_search/role_search_config.py
- [[parse_cv_markdown()_1]] - code - shared/cv_loader.py
- [[patch]] - code
- [[profiles_use_demo_templates()]] - code - job_search/role_search_config.py
- [[resolve_cv_dir()]] - code - shared/cv_loader.py
- [[role_search_config.py]] - code - job_search/role_search_config.py
- [[test_ingest_keywords.py]] - code - job_search/tests/test_ingest_keywords.py
- [[using_demo_cv_keywords()]] - code - job_search/ingest_keywords.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Ingest_Keyword_Collect
SORT file.name ASC
```

## Connections to other communities
- 11 edges to [[_COMMUNITY_Location Preferences]]
- 8 edges to [[_COMMUNITY_FINN Search Queries]]
- 6 edges to [[_COMMUNITY_NAV Job Ingest]]
- 6 edges to [[_COMMUNITY_Academic Job Filters]]
- 4 edges to [[_COMMUNITY_Private CV Apply]]
- 4 edges to [[_COMMUNITY_Agent Pipeline Runner]]
- 4 edges to [[_COMMUNITY_Dashboard DB Loaders]]
- 3 edges to [[_COMMUNITY_Run Cv Tailoring]]
- 3 edges to [[_COMMUNITY_Test Academic Track Filter]]
- 2 edges to [[_COMMUNITY_Test Cover Letter Generator]]
- 1 edge to [[_COMMUNITY_Import Cv Pdf]]
- 1 edge to [[_COMMUNITY_Test Cv Norwegian Paths]]

## Top bridge nodes
- [[load_default_profiles()]] - degree 25, connects to 7 communities
- [[cv_loader.py]] - degree 19, connects to 7 communities
- [[role_search_config.py]] - degree 12, connects to 4 communities
- [[patch]] - degree 8, connects to 3 communities
- [[test_ingest_keywords.py]] - degree 15, connects to 2 communities