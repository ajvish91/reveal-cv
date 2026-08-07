---
type: community
members: 109
---

# Private CV Apply

**Members:** 109 nodes

## Members
- [[dot-python()]] - code - cv_generation/private_cv.py
- [[dot-runs_root()]] - code - cv_generation/private_cv.py
- [[dot-test_deanonymized_output_redirects_to_repo_run()]] - code - cv_generation/tests/test_private_cv_resolve.py
- [[dot-test_enrich_legacy_run_from_parser_json()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_enrich_preserves_existing_company_segment()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_find_repo_run_by_timestamp_from_enriched_name()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_parse_folder_with_company()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_parse_legacy_folder_without_company()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_resolve_company_from_job_posting()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_resolve_deanon_output_dir_enriches_legacy_run()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_resolve_run_dir_finds_legacy_run_from_enriched_name()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_resolve_run_id_uses_repo_runs()]] - code - cv_generation/tests/test_private_cv_resolve.py
- [[dot-test_run_cv_tailoring_derives_company_from_job_posting()]] - code - cv_generation/tests/test_run_naming.py
- [[dot-test_run_folder_name_includes_company()]] - code - cv_generation/tests/test_run_naming.py
- [[After a repo renovation update config, stubs, and mapping keys from the…]] - rationale - cv_generation/private_cv.py
- [[ArgumentParser]] - code
- [[Best-effort company from parser output, tasks, or job_posting.txt.]] - rationale - cv_generation/run_naming.py
- [[Company for new run folders; never empty.]] - rationale - cv_generation/run_naming.py
- [[Compare education entry counts in source vs deanonymized markdown (PDF parser).]] - rationale - cv_generation/private_cv.py
- [[Copy current resolved CV markdown into ~privatecvcv.]] - rationale - cv_generation/private_cv.py
- [[Create Norwegian _no.md in the repo run folder (required before apply can copy…]] - rationale - cv_generation/private_cv.py
- [[Deanonymize a single cv_runs folder; return exit code.]] - rationale - cv_generation/private_cv.py
- [[Deanonymize and render Norwegian _no.md artifacts when present.]] - rationale - cv_generation/private_cv.py
- [[Deanonymize cover letter, application letter, research proposal, etc. when…]] - rationale - cv_generation/private_cv.py
- [[Deanonymized output folder; enriches legacy run ids with company metadata.]] - rationale - cv_generation/private_cv.py
- [[Find the single cv_runs folder sharing a UTC timestamp prefix.]] - rationale - cv_generation/run_naming.py
- [[Folder-safe company token, preserving casing (e.g. Storebrand).]] - rationale - cv_generation/run_naming.py
- [[If the user pointed at deanonymized output (only English artifacts), use the…]] - rationale - cv_generation/private_cv.py
- [[Install repo as editable package so `python -m cv_generation.private_cv` works…]] - rationale - cv_generation/private_cv.py
- [[MappingSyncResult]] - code - cv_generation/private_cv.py
- [[Merge repo template into private mapping. - New keys from the example are…]] - rationale - cv_generation/private_cv.py
- [[Namespace_4]] - code
- [[Old template keys replaced the whole  line and broke education parsing in…]] - rationale - cv_generation/private_cv.py
- [[Output folder basename with company when the repo run folder omitted it.…]] - rationale - cv_generation/run_naming.py
- [[Parse ``{timestamp}_{CompanySlug}_{role-slug}`` or legacy ``{timestamp}_{role-…]] - rationale - cv_generation/run_naming.py
- [[Path_15]] - code
- [[Path_19]] - code
- [[PrivateConfig]] - code - cv_generation/private_cv.py
- [[Refresh ~privatecvcv and ~privatecvsync so they always call this repo.]] - rationale - cv_generation/private_cv.py
- [[Resolve run folders for private_cv apply (repo source vs deanonymized output).]] - rationale - cv_generation/tests/test_private_cv_resolve.py
- [[Restore industry.md + academic.md from the newest cv_runscv__source.md…]] - rationale - cv_generation/private_cv.py
- [[Run folder naming ``{timestamp}_{CompanySlug}_{role-slug}``.]] - rationale - cv_generation/run_naming.py
- [[Run-local override first, then the same filename in ~privatecv.]] - rationale - cv_generation/private_cv.py
- [[TestPrivateCvDeanonOutput]] - code - cv_generation/tests/test_run_naming.py
- [[TestResolveRunDir]] - code - cv_generation/tests/test_private_cv_resolve.py
- [[TestRunCvTailoringFolderName]] - code - cv_generation/tests/test_run_naming.py
- [[TestRunNaming]] - code - cv_generation/tests/test_run_naming.py
- [[Tests for run folder naming and deanonymize output enrichment.]] - rationale - cv_generation/tests/test_run_naming.py
- [[True when the basename has a company segment between timestamp and role.]] - rationale - cv_generation/run_naming.py
- [[Use only the relevant English or Norwegian override mapping.]] - rationale - cv_generation/private_cv.py
- [[_apply_localized_artifacts()]] - code - cv_generation/private_cv.py
- [[_apply_supplementary_artifacts()]] - code - cv_generation/private_cv.py
- [[_audit_markdown()]] - code - cv_generation/private_cv.py
- [[_copy_cv_sources_to()]] - code - cv_generation/private_cv.py
- [[_detect_private_dir()]] - code - cv_generation/private_cv.py
- [[_expand()_1]] - code - cv_generation/private_cv.py
- [[_load_json_object()]] - code - cv_generation/run_naming.py
- [[_prefer_repo_run_source()]] - code - cv_generation/private_cv.py
- [[_stub_pythonpath_export()]] - code - cv_generation/private_cv.py
- [[_warn_education_parse()]] - code - cv_generation/private_cv.py
- [[_warn_legacy_degree_mapping_keys()]] - code - cv_generation/private_cv.py
- [[apply_one_run()]] - code - cv_generation/private_cv.py
- [[build_parser()]] - code - cv_generation/private_cv.py
- [[cmd_all_runs()]] - code - cv_generation/private_cv.py
- [[cmd_apply()]] - code - cv_generation/private_cv.py
- [[cmd_audit()]] - code - cv_generation/private_cv.py
- [[cmd_edit()]] - code - cv_generation/private_cv.py
- [[cmd_export_cv_sources()]] - code - cv_generation/private_cv.py
- [[cmd_localize()]] - code - cv_generation/private_cv.py
- [[cmd_pdf()]] - code - cv_generation/private_cv.py
- [[cmd_recover_cv_sources()]] - code - cv_generation/private_cv.py
- [[cmd_refresh()]] - code - cv_generation/private_cv.py
- [[cmd_setup()]] - code - cv_generation/private_cv.py
- [[cmd_sync()]] - code - cv_generation/private_cv.py
- [[cmd_sync_keys()]] - code - cv_generation/private_cv.py
- [[company_slug()]] - code - cv_generation/run_naming.py
- [[e.g. ``20260601T122139Z_Storebrand_senior-ai-platform-engineer``.]] - rationale - cv_generation/run_naming.py
- [[enrich_run_folder_name()]] - code - cv_generation/run_naming.py
- [[ensure_repo_package_installed()]] - code - cv_generation/private_cv.py
- [[example_mapping_path()]] - code - cv_generation/private_cv.py
- [[find_repo_run_by_timestamp()]] - code - cv_generation/run_naming.py
- [[folder_includes_company()]] - code - cv_generation/run_naming.py
- [[load_config()]] - code - cv_generation/private_cv.py
- [[load_raw_json()]] - code - cv_generation/private_cv.py
- [[main()_5]] - code - cv_generation/private_cv.py
- [[mapping_override_path()]] - code - cv_generation/private_cv.py
- [[merge_mapping_from_example()]] - code - cv_generation/private_cv.py
- [[parse_company_from_job_posting()]] - code - cv_generation/run_naming.py
- [[parse_run_folder_basename()]] - code - cv_generation/run_naming.py
- [[print_mapping_sync_report()]] - code - cv_generation/private_cv.py
- [[private_cv.py]] - code - cv_generation/private_cv.py
- [[read_run_company()]] - code - cv_generation/run_naming.py
- [[read_run_role()]] - code - cv_generation/run_naming.py
- [[resolve_company_for_folder()]] - code - cv_generation/run_naming.py
- [[resolve_cv_package_dir()]] - code - cv_generation/private_cv.py
- [[resolve_deanon_output_dir()]] - code - cv_generation/private_cv.py
- [[resolve_mapping_for_artifact()]] - code - cv_generation/private_cv.py
- [[resolve_run_dir()_1]] - code - cv_generation/private_cv.py
- [[run_deanonymize()]] - code - cv_generation/private_cv.py
- [[run_folder_name()]] - code - cv_generation/run_naming.py
- [[run_naming.py]] - code - cv_generation/run_naming.py
- [[run_render_pdf()]] - code - cv_generation/private_cv.py
- [[save_raw_json()]] - code - cv_generation/private_cv.py
- [[slugify()]] - code - cv_generation/run_naming.py
- [[supplementary_artifact_filenames()]] - code - cv_generation/cv_application_artifacts.py
- [[test_private_cv_resolve.py]] - code - cv_generation/tests/test_private_cv_resolve.py
- [[test_run_naming.py]] - code - cv_generation/tests/test_run_naming.py
- [[write_config()]] - code - cv_generation/private_cv.py
- [[write_private_stubs()]] - code - cv_generation/private_cv.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Private_CV_Apply
SORT file.name ASC
```

## Connections to other communities
- 9 edges to [[_COMMUNITY_Run Cv Tailoring]]
- 4 edges to [[_COMMUNITY_Deanonymize Cvs]]
- 4 edges to [[_COMMUNITY_Ingest Keyword Collect]]
- 2 edges to [[_COMMUNITY_Render Cv Pdf]]
- 2 edges to [[_COMMUNITY_Norwegian CV Localization]]
- 2 edges to [[_COMMUNITY_CV PDF Renderer]]
- 1 edge to [[_COMMUNITY_Application Artifacts]]
- 1 edge to [[_COMMUNITY_Dashboard Job Export]]
- 1 edge to [[_COMMUNITY_Apply Pipeline Options]]
- 1 edge to [[_COMMUNITY_Repo Paths]]

## Top bridge nodes
- [[private_cv.py]] - degree 57, connects to 6 communities
- [[supplementary_artifact_filenames()]] - degree 6, connects to 3 communities
- [[run_naming.py]] - degree 17, connects to 1 community
- [[test_run_naming.py]] - degree 17, connects to 1 community
- [[cmd_audit()]] - degree 10, connects to 1 community