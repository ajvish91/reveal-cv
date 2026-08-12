# Graph Report - job search automation  (2026-08-12)

## Corpus Check
- 143 files · ~124,907 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2093 nodes · 4660 edges · 144 communities (129 shown, 15 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 208 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6f53c747`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- PrivateConfig
- dashboard.py
- haystack_for_filter
- Any
- _apply_modify_dialog_body
- test_dashboard_applied_roles.py
- connect
- finn_job_client.py
- cv_assemble.py
- cv_norwegian.py
- Path
- JobProfile
- cover_letter_generator.py
- debug_log
- Job search pipeline
- main
- pipeline_metrics.py
- run_agent_pipeline.py
- cv_pdf_renderer.py
- configure_logging
- Data Engineer (Inspirit)
- apply_prompts.py
- job_filters.py
- run_naming.py
- DataFrame
- deadline_utils.py
- should_periodic_refresh
- agent_providers.py
- parse_cv_markdown
- apply_dialog_ready
- job_dedup.py
- agent_cli.py
- _dialog_artifact_bundle
- fetch_tek_rogaland_members.py
- _render_pipeline_completion_notice
- ats_check_pdf.py
- matches_academic_role_display
- deanonymize_cvs.py
- dashboard_styles.py
- test_cv_tracks.py
- plain_markdown_pdf.py
- private_cv.py
- TestAppliedRolesHelpers
- cv_private.py
- assembler Subagent
- extract_run_ids_from_notes
- render_styled_cv_pdf
- test_agent_interop.py
- ingest_nav_jobs.py
- build_ingest_cycle_command
- run_cv_tailoring.py
- Fujitsu Senior Researcher 8547
- Senior Data Engineer - Data & AI
- Research Scientist in Information Theory
- _render_job_explorer_fragment
- cv_source_sync.py
- TestCoverLetterGenerator
- Senior Integration Engineer
- Fagansvarlig dataforskning og kunstig intelligens
- Data Scientist - Gjensidige AI CoE
- Generative AI Specialist - Statnett
- Post-doctoral Research Fellow in AI and Cultural Heritage
- Supplementary Application Documents
- resolve_sidebar_photo_path
- localize_run
- AI Innovation Lead - Tieto Banktech
- Principal AI Enablement Engineer
- score_jobs.py
- ingest_finn_jobs.py
- _dismiss_apply_modify_dialog
- run_demo.py
- Privacy-First Workflow
- has_profile_relevance
- TestDashboardDebug
- Run Folder Contract
- Retrieval-Augmented Generation (RAG)
- application_status_upsert_row
- timing_span
- job_search Module
- Industry CV Track
- Ethics of Embodied AI
- Platform for AI-Generated and Project Applications
- Data Scientist (Gjensidige)
- Platform for responsible AI
- Private Identity Boundary
- Northline ML Engineer Demo Run
- Digital Twins
- ML/AI Engineer
- Vision AI Sensor Solutions
- Field Digital Twins
- Postdoctoral Research Fellow Mathematical Foundations of AI
- KI-ingeniør Data Scientist (Prosjektstilling)
- Data Scientist - NORCE Analytics
- Postdoctoral Fellow – AI for Decisions (AID)
- Tech Lead Bergen - AI-assisted development
- Energy Estimation Formula v1
- LinkedIn lowercase in wordmark logo
- Connected contact figure paths
- Rounded rectangle card frame
- Circular light-gray frame around figure
- Demo Industry CV Source
- log_state_diff
- Data Engineer GEOMETOC (Etterretningstjenesten)
- Cyber Security Engineer - Remota
- Postdoktor innen e-helse/tjenester
- English cover letter voice
- _FakeResponse
- check_safe_to_push.py
- Birthday cake CV icon (date of birth)
- Birthday cake SVG icon (date of birth)
- Email envelope SVG contact icon
- GitHub Octocat silhouette logo
- Head body tentacle stroke path
- Diamond-shaped mortarboard top
- Open academic book / scholar SVG icon
- Map pin / location marker icon
- Map pin location SVG icon
- Mail envelope SVG icon
- Map-pin SVG location marker
- ORCID ID card / badge icon
- Earpiece end of handset
- Phone call receiver SVG icon
- jd_parser Subagent
- Attensi Next-Gen Data Platform
- Enhetsleder for IT og digitalisering
- Agentic Commerce
- ForwardMedia Research Centre
- Tritium Consulting
- Email envelope CV contact icon
- render_private_cv.example.sh
- Piano Software Norway HTML fixture
- Git-ready privacy plan
- cv_generation/__init__.py
- Developer / Software Engineer
- Agentic systems
- job_search/__init__.py
- agent_apply_job.sh
- bulk_apply_deanonymize.sh
- shared/__init__.py
- Provider: anthropic
- Provider: openai
- certifi
- pandas
- pyyaml

## God Nodes (most connected - your core abstractions)
1. `main()` - 52 edges
2. `ApplyPipelineOptions` - 35 edges
3. `haystack_for_filter()` - 32 edges
4. `PrivateConfig` - 31 edges
5. `connect()` - 30 edges
6. `init_schema()` - 30 edges
7. `debug_log()` - 29 edges
8. `run()` - 28 edges
9. `JobProfile` - 28 edges
10. `PipelineMetricsCollector` - 26 edges

## Surprising Connections (you probably didn't know these)
- `cv_style.py Tailoring Constants` --semantically_similar_to--> `CV Tailoring Style`  [INFERRED] [semantically similar]
  cv_generation/CV_AUTOMATION.md → AGENTS.md
- `Deanonymize Privately` --semantically_similar_to--> `private_cv apply / local reveal`  [INFERRED] [semantically similar]
  cv_generation/CV_AUTOMATION.md → PRIVACY.md
- `ALEX RIVERA Demo Candidate` --semantically_similar_to--> `ALEX RIVERA Demo Candidate`  [INFERRED] [semantically similar]
  cv_generation/demo/README.md → PRIVACY.md
- `Piano Software Norway ML/AI Engineer` --semantically_similar_to--> `Piano Software Norway HTML fixture`  [INFERRED] [semantically similar]
  cv_generation/tests/fixtures/legacy_run_no_company/job_posting.txt → job_search/tests/fixtures/finn/job_detail_html_only.html
- `ALEX RIVERA fictional candidate` --semantically_similar_to--> `ALEX RIVERA (industry demo)`  [INFERRED] [semantically similar]
  docs/DEMO.md → shared/cv/industry.demo.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Six-Step CV Tailoring Subagent Pipeline** — cv_generation_cv_automation_jd_parser, cv_generation_cv_automation_keyword_ranker, cv_generation_cv_automation_track_selector, cv_generation_cv_automation_bullet_tailor, cv_generation_cv_automation_ats_checker, cv_generation_cv_automation_assembler [EXTRACTED 1.00]
- **Setup Tailor Reveal Privacy Workflow** — privacy_private_cv_setup, privacy_run_cv_tailoring, privacy_run_agent_pipeline, privacy_private_cv_apply [EXTRACTED 1.00]
- **Agent Provider Transport Adapters** — cv_generation_agent_interop_provider_cursor, cv_generation_agent_interop_provider_anthropic, cv_generation_agent_interop_provider_openai, cv_generation_agent_interop_provider_manual [EXTRACTED 1.00]
- **Production RAG and LLM Application Roles** — cv_generation_jobs_falkor_software_ai_engineer_rag, cv_generation_jobs_finn_465089104_ml_ai_engineer_rag, cv_generation_jobs_finn_468693066_data_scientist_rag, cv_generation_jobs_finn_469335085_ai_engineer_rag [INFERRED 0.85]
- **Modern Analytics Data Platform (dbt / Warehouse)** — cv_generation_jobs_finn_468844158_data_engineer_snowflake_dbt_airflow, cv_generation_jobs_finn_468883659_senior_data_engineer_snowflake_dbt, cv_generation_jobs_finn_468145996_data_engineer_data_scientist_dbt, cv_generation_jobs_finn_468693066_data_scientist_databricks_dbt [INFERRED 0.85]
- **Norwegian Postdoctoral AI Research Positions** — cv_generation_jobs_finn_465564641_postdoctoral_research_fellow_in_ethics_of_embodi_postdoc_ethics_embodied_ai, cv_generation_jobs_finn_467762339_postdoctoral_fellow_within_ai_driven_digital_phe_postdoc_digital_phenotyping, cv_generation_jobs_finn_468670212_postdoctoral_research_fellow_in_mathematical_fou_postdoc_math_foundations_ai [INFERRED 0.75]
- **Modern cloud data platform stack (Databricks/Snowflake/Fabric)** — cv_generation_jobs_finn_469744220_senior_data_engineer_data_ai_experis_snowflake_databricks_fabric, cv_generation_jobs_metier_bi_analytics_konsulent_microsoft_fabric_databricks, cv_generation_jobs_twoday_senior_data_engineer_data_scientist_databricks_snowflake_fabric, cv_generation_jobs_gjensidige_data_scientist_468693066_databricks_dbt [INFERRED 0.85]
- **Production generative AI / LLM systems** — cv_generation_jobs_gjensidige_data_scientist_468693066_generative_ai_rag, cv_generation_jobs_tieto_banktech_ai_innovation_rag_pipelines, cv_generation_jobs_tieto_banktech_ai_innovation_agentic_workflows, cv_generation_jobs_pmm_senior_ai_engineer_oslo_genai_methods, cv_generation_jobs_sanna_full_stack_ai_engineer_production_llm_workflows, cv_generation_jobs_statnett_generative_ai_specialist_generative_ai_it_ot [INFERRED 0.75]
- **Academic AI research positions (postdoc/researcher)** — cv_generation_jobs_ntnu_aid_postdoc_human_ai_decisions_aid_postdoc_role, cv_generation_jobs_nav_32825e09_0f94_4992_b5b6_27231ec25522_postdoktor_innen_e_helse_tjenester_postdoktor_ehelse_role, cv_generation_jobs_uia_postdoc_ai_cultural_heritage_postdoc_ai_cultural_heritage_role, cv_generation_jobs_uio_nxtgenfake_researcher_generative_ai_disinformation_nxtgenfake_researcher_role, cv_generation_jobs_usn_ai_security_privacy_researcher_ai_security_privacy_researcher_role, cv_generation_jobs_simula_uib_research_scientist_information_theory_research_scientist_role [INFERRED 0.75]
- **Privacy-first Tailor then Reveal workflow** — docs_demo_anonymized_first_workflow, docs_demo_video_script_tailor_reveal, docs_show_hn_privacy_model, docs_git_and_privacy_private_workflow [INFERRED 0.85]
- **Job search ingest score dashboard flow** — job_search_job_search_nav_ingest, job_search_job_search_finn_ingest, job_search_job_search_score_jobs, job_search_job_search_dashboard, job_search_job_search_run_job_search_cycle [EXTRACTED 1.00]
- **FINN detail and search parse fixture variants** — job_search_tests_fixtures_finn_job_detail_json_ld_jobposting, job_search_tests_fixtures_finn_job_detail_html_only_html_body_posting, job_search_tests_fixtures_finn_job_detail_wrapped_ld_json_wrapped_jobposting, job_search_tests_fixtures_finn_search_results_search_ad_cards, job_search_tests_fixtures_finn_search_results_live_job_card_layout [INFERRED 0.85]

## Communities (144 total, 15 thin omitted)

### Community 0 - "PrivateConfig"
Cohesion: 0.13
Nodes (26): _apply_localized_artifacts(), _apply_markdown_artifacts(), apply_one_run(), _apply_supplementary_artifacts(), mapping_override_path(), _prefer_repo_run_source(), PrivateConfig, Path (+18 more)

### Community 1 - "dashboard.py"
Cohesion: 0.10
Nodes (44): _append_pipeline_log_line(), best_job_url(), cv_job_filename(), export_job_to_cv_file(), format_job_export_text(), format_location(), _format_score_caption(), _handle_application_status_update() (+36 more)

### Community 2 - "haystack_for_filter"
Cohesion: 0.18
Nodes (11): haystack_for_filter(), matches_exclude_terms(), matches_finance_controller(), matches_phd_student_opening(), True for finance/accounting controller ads; False for IT/ICT controller roles., True when the posting is a PhD *student/fellowship* opening (candidate will…, NoiseBlocklistTests, Tests for profile relevance filtering and expanded noise blocklist. (+3 more)

### Community 3 - "Any"
Cohesion: 0.08
Nodes (47): normalize_apply_language(), utc_now_iso(), _activate_pipeline_from_item(), _advance_pipeline_queue_after_finish(), apply_dialog_language_key(), apply_pipeline_options_from_mapping(), apply_pipeline_options_to_mapping(), ApplyPipelineOptions (+39 more)

### Community 4 - "_apply_modify_dialog_body"
Cohesion: 0.06
Nodes (45): _apply_modify_dialog_body(), _build_pipeline_result(), _copy_text_to_clipboard(), _open_pipeline_dialog(), _pipeline_active_for_job(), _pipeline_job_title(), _pipeline_log_text(), pipeline_result_details() (+37 more)

### Community 5 - "test_dashboard_applied_roles.py"
Cohesion: 0.05
Nodes (27): build_explorer_filter_chips(), can_enqueue_pipeline(), _explorer_jobs_cache_fingerprint(), pipeline_job_display_title(), pipeline_phase_is_busy(), pipeline_queue_is_full(), pipeline_queue_remaining(), pipeline_queue_slots_used() (+19 more)

### Community 6 - "connect"
Cohesion: 0.14
Nodes (28): cache_data, Connection, count_research_roles_in_db(), filter_phd_student_df(), load_applications_df(), load_applied_roles_df(), load_jobs_df(), load_overview_jobs_bundle() (+20 more)

### Community 7 - "finn_job_client.py"
Cohesion: 0.06
Nodes (43): BaseException, HTMLParser, HTTPError, _address_fields(), build_search_url(), _card_text(), _collect_schema_objects(), _detail_title() (+35 more)

### Community 8 - "cv_assemble.py"
Cohesion: 0.14
Nodes (25): apply_bullet_tailor(), _coerce_bullets(), _collect_institution_names(), _degree_kind(), _education_institutions_by_degree(), experience_role_key(), extract_experience_roles(), _match_tailored_role() (+17 more)

### Community 9 - "cv_norwegian.py"
Cohesion: 0.08
Nodes (32): ArtifactKind, build_localization_prompt(), count_experience_bullets(), count_experience_roles(), count_norwegian_cover_letter_body_words(), _cover_letter_body_text(), detect_track(), _experience_section_lines() (+24 more)

### Community 10 - "Path"
Cohesion: 0.11
Nodes (20): _execute_ingest_cycle(), get_db_path(), ingest_active_source_counts(), IngestCycleOptions, parse_ingest_cycle_output(), Path, User-selected ingest cycle options from the dashboard sidebar., Parse step labels and JSON summaries from ``run_job_search_cycle`` stdout. (+12 more)

### Community 11 - "JobProfile"
Cohesion: 0.07
Nodes (36): extract_pdf_text(), main(), Path, sanitize_filename(), collect_ingest_keywords(), Merge CV profile keywords/skills with curated application-history boosts for…, Keywords used by NAV/FINN ingest for --keyword-filter matching and --list-…, Expose demo detection for tests and diagnostics. (+28 more)

### Community 12 - "cover_letter_generator.py"
Cohesion: 0.15
Nodes (33): cover_letter_markdown_path(), CoverLetterResult, generate_cover_letter_markdown(), is_cover_letter_required(), manual_cover_letter_prompt_path(), manual_cover_letter_response_path(), maybe_generate_cover_letter(), Any (+25 more)

### Community 13 - "debug_log"
Cohesion: 0.15
Nodes (29): _active_rerun_context(), _append_file(), debug_enabled_from_env(), debug_log(), _format_event(), _generate_rerun_id(), _hash_text(), init_dashboard_debug() (+21 more)

### Community 14 - "Job search pipeline"
Cohesion: 0.07
Nodes (33): ALEX RIVERA fictional candidate, Anonymized-first public demo, One-repo job search and CV generation architecture, Demo walkthrough, scripts/run_demo.py, 60-second demo script, Tailor in public Reveal in private, Private CV workflow (+25 more)

### Community 15 - "main"
Cohesion: 0.08
Nodes (27): _cache_exec_count(), _handle_delete_application(), _infer_page_rerun_reason(), _infer_page_scope(), _init_ingest_session_state(), _init_pipeline_session_state(), _init_refresh_session_state(), _invalidate_dashboard_data_caches() (+19 more)

### Community 16 - "pipeline_metrics.py"
Cohesion: 0.11
Nodes (18): estimate_energy_kwh(), estimate_tokens_from_text(), format_duration_sec(), format_pipeline_metrics_summary(), json_dumps(), load_pipeline_metrics(), peak_rss_mb(), PipelineMetrics (+10 more)

### Community 17 - "run_agent_pipeline.py"
Cohesion: 0.16
Nodes (29): list_providers(), Path, Role from JD parser output, then job_posting.txt, then task job_meta., resolve_job_role_title(), build_prompt(), experience_inventory(), extract_final_cv_markdown(), extract_priority_terms() (+21 more)

### Community 18 - "cv_pdf_renderer.py"
Cohesion: 0.10
Nodes (57): _academic_main_column_story_from_cv(), _ats_list_paragraph(), _compact_sidebar_stack(), _contact_href(), _contact_icon_key(), _contact_paragraph_markup(), CvContent, _draw_centered_sidebar_sections_on_canvas() (+49 more)

### Community 19 - "configure_logging"
Cohesion: 0.14
Nodes (17): configure_logging(), get_logger(), log_json_summary(), Path, Central logging configuration for the job_search package., Configure the ``job_search`` logger tree (file + optional stderr)., Return a child logger under the ``job_search`` namespace., Log an ingest/score summary dict (also printed to stdout by callers). (+9 more)

### Community 20 - "Data Engineer (Inspirit)"
Cohesion: 0.07
Nodes (28): Azure ML and Fabric Notebooks, Data Engineer (Inspirit), Data Scientist (Inspirit), dbt Data Transformations, Inspirit365, Medallion / Star-Snowflake Data Modeling, Microsoft Fabric / Azure Data Platform, BI Analyseplattform (+20 more)

### Community 21 - "apply_prompts.py"
Cohesion: 0.14
Nodes (13): apply_language_markdown_section(), apply_prompts_markdown_section(), apply_prompts_path(), merge_apply_prompts(), normalize_apply_prompts(), Path, Optional user tailoring instructions for a CV run folder., Per-job popover may override sidebar; ``inherit`` keeps the sidebar default. (+5 more)

### Community 22 - "job_filters.py"
Cohesion: 0.13
Nodes (21): _jobs_query_fragments(), _filter_text_part(), merge_exclude_terms(), merge_include_terms(), _merge_terms_ordered(), parse_term_field(), Job text filters for ingest and dashboard. 1) **Tech allowlist** — show/keep…, Coerce filter fields to str; skip None/NaN/non-strings (pandas empty cells). (+13 more)

### Community 23 - "run_naming.py"
Cohesion: 0.11
Nodes (26): company_slug(), enrich_run_folder_name(), find_repo_run_by_timestamp(), folder_includes_company(), _load_json_object(), parse_company_from_job_posting(), parse_role_from_job_posting(), parse_run_folder_basename() (+18 more)

### Community 24 - "DataFrame"
Cohesion: 0.16
Nodes (17): apply_dashboard_filters(), apply_text_search_filter(), dedupe_jobs_df(), enrich_jobs_df(), _import_module_resilient(), _load_explorer_jobs_df(), _log_dashboard_filter_state(), DataFrame (+9 more)

### Community 25 - "deadline_utils.py"
Cohesion: 0.16
Nodes (20): date, apply_soon_badge(), coerce_expires_value(), days_until_deadline(), deadline_display(), is_apply_soon(), _normalize_year(), parse_deadline() (+12 more)

### Community 26 - "should_periodic_refresh"
Cohesion: 0.15
Nodes (11): format_auto_refresh_label(), Dashboard data refresh helpers (no Streamlit dependency)., True when ``now_monotonic`` is at or past the next scheduled cache refresh., Return interval length in seconds, or ``None`` when auto-refresh is off., refresh_interval_seconds(), should_periodic_refresh(), Tests for dashboard periodic refresh helpers (no Streamlit runtime)., TestAutoRefreshOptions (+3 more)

### Community 27 - "agent_providers.py"
Cohesion: 0.21
Nodes (13): ABC, AgentProvider, AgentRunResult, AnthropicAgentProvider, call_markdown_agent(), CursorAgentProvider, get_provider(), ManualAgentProvider (+5 more)

### Community 28 - "parse_cv_markdown"
Cohesion: 0.09
Nodes (24): _apply_profile_length_limits(), Trim Profile / Summary so PDF main column stays within a practical page budget., _cleanup(), _detect_document_language(), _education_item_from_block(), _parse_bullet_section(), parse_cv_markdown(), _parse_education_bullet_line() (+16 more)

### Community 29 - "apply_dialog_ready"
Cohesion: 0.15
Nodes (10): _apply_dialog_fast_path_active(), apply_dialog_ready(), pipeline_active_for_job_key(), True when session holds an active pipeline for ``job_key`` (no Streamlit)., True when Apply/Modify may open: valid row context or active pipeline for the…, Return session-state patches that clear stale dialog flags (no Streamlit)., True when the Apply/Modify dialog should short-circuit the heavy dashboard page., reconcile_apply_dialog_flags() (+2 more)

### Community 30 - "job_dedup.py"
Cohesion: 0.17
Nodes (15): dedup_key(), dedupe_jobs_df(), _merge_duplicate_fields(), normalize_text(), _pick_primary_index(), Any, DataFrame, Series (+7 more)

### Community 31 - "agent_cli.py"
Cohesion: 0.37
Nodes (14): main(), parse_args(), _prior_outputs(), Namespace, Path, _resolve_step(), _run_build_prompt(), _run_pipeline_cmd() (+6 more)

### Community 32 - "_dialog_artifact_bundle"
Cohesion: 0.11
Nodes (13): apply_button_label(), _cached_default_artifact_options(), default_artifact_options(), _dialog_artifact_bundle(), existing_artifact_flags(), Pre-check artifact generation toggles from posting detection., Cached JD scan for academic artifact checkboxes (plain industry skips the scan)., True when title/employer look like a postdoc/researcher call (cheap; no JD… (+5 more)

### Community 33 - "fetch_tek_rogaland_members.py"
Cohesion: 0.24
Nodes (19): addr_rogaland(), analyze_member(), brreg_query_name(), collect_brreg_org_addresses(), curl_bytes(), curl_json(), extract_content_html(), fetch_all_underenheter() (+11 more)

### Community 34 - "_render_pipeline_completion_notice"
Cohesion: 0.24
Nodes (9): _completion_notice_payload(), _dismiss_pipeline_notice(), _open_completion_notice_dialog(), pipeline_notice_id(), Prefer a parked completion (queue advanced); else the idle finished pipeline., Reopen result UI for a finished job (including after queue advanced)., Top-of-page success/error banner for a finished pipeline when dialog is closed., _render_pipeline_completion_notice() (+1 more)

### Community 35 - "ats_check_pdf.py"
Cohesion: 0.24
Nodes (17): build_report(), compare_markdown_keywords(), detect_format_issues(), extract_pdf_text(), keyword_coverage(), load_must_have_terms(), load_priority_terms(), main() (+9 more)

### Community 36 - "matches_academic_role_display"
Cohesion: 0.09
Nodes (16): effective_academic_roles_only(), Academic CV track always applies the strict research-role display filter., Default FINN.no search queries tuned from application history., matches_academic_role(), matches_academic_role_display(), True when title/description/employer matches university or research role…, Stricter dashboard filter: role terms in title/jobtitle, or university employer…, all_default_finn_search_queries() (+8 more)

### Community 37 - "deanonymize_cvs.py"
Cohesion: 0.06
Nodes (39): detect_supplementary_artifacts(), is_plain_pdf_markdown(), normalize_upper_name_variants(), Path, Supplementary application markdown files beyond final_cv.md. Used by private_cv…, Heuristic: which supplementary files the posting likely needs., True when markdown should render as plain one-column PDF (not styled CV)., Add title-case aliases for fully-uppercase personal-name keys. Example: ``MITCH… (+31 more)

### Community 38 - "dashboard_styles.py"
Cohesion: 0.08
Nodes (24): _finalize_dashboard_scroll(), _inject_dashboard_css(), pipeline_fallback_eligible(), _pipeline_poll_fast_path_active(), True when the page-level fallback should render the active pipeline., Inject unified scroll manager once per rerun, after page content exists., Render the active pipeline at page level when its row is off-screen., True when pipeline polling should skip job loads (dialog dismissed, worker… (+16 more)

### Community 39 - "test_cv_tracks.py"
Cohesion: 0.09
Nodes (22): assemble_final_cv_markdown(), designation_from_job_role(), Headline under the name on the CV/PDF (e.g. ML/AI Engineer -> ML/AI ENGINEER)., Keep at most max_count skills, preferring terms that match ranked JD keywords., render_cv_markdown(), select_tailored_skills(), _is_academic_cv(), _is_industry_cv() (+14 more)

### Community 40 - "plain_markdown_pdf.py"
Cohesion: 0.18
Nodes (13): markdown_inline_to_reportlab(), Convert lightweight markdown inline emphasis to ReportLab paragraph markup.…, _add_paragraph(), _add_table(), build_plain_markdown_story(), _is_table_separator_row(), _paragraph_styles(), _parse_table_row() (+5 more)

### Community 41 - "private_cv.py"
Cohesion: 0.11
Nodes (44): supplementary_artifact_filenames(), is_placeholder_value(), load_mapping(), True when the mapping value is still an unfilled template, not real PII., _audit_markdown(), build_parser(), cmd_all_runs(), cmd_apply() (+36 more)

### Community 42 - "TestAppliedRolesHelpers"
Cohesion: 0.13
Nodes (11): bulk_deanonymize_command(), _count_applied_roles(), filter_applied_roles_df(), Build a job row dict suitable for ``execute_apply_pipeline`` from an…, Combined ``cv apply`` command for drafted rows with CV run IDs in notes., Collapsible applied-roles list with status filter and compact rows., Drafts and applied-role lists for the current CV track., render_applied_roles_section() (+3 more)

### Community 43 - "cv_private.py"
Cohesion: 0.29
Nodes (10): _expand(), _is_real_http_url(), _mapping_raw(), profile_photo_from_mapping(), Path, Build deanonymize search/replace pairs from ``_*_url`` metadata keys. Template…, Return path to a profile photo file, or None to use the in-repo placeholder.…, resolve_profile_photo_path() (+2 more)

### Community 44 - "assembler Subagent"
Cohesion: 0.14
Nodes (14): Step 06 assembler, Step 05 ats_checker, Step 04 bullet_tailor, Step 01 jd_parser, Step 02 keyword_ranker, Step 03 track_selector, assembler Subagent, ats_check_pdf (+6 more)

### Community 45 - "extract_run_ids_from_notes"
Cohesion: 0.15
Nodes (11): Resolve a run basename to ``cv_generation/cv_runs/<run_id>``., resolve_run_dir(), extract_run_ids_from_notes(), pipeline_metrics_for_run_id(), pipeline_metrics_summary_for_notes(), Return CV run folder basenames from application notes (``CV run: …`` lines)., Load ``pipeline_metrics.json`` for a run basename, if present., One-line impact summary from the latest CV run referenced in notes. (+3 more)

### Community 46 - "render_styled_cv_pdf"
Cohesion: 0.19
Nodes (14): BaseDocTemplate, _build_dual_column_layout(), render_styled_cv_pdf(), Path, render_plain_markdown_pdf(), _ensure_project_cwd(), _import_renderer(), main() (+6 more)

### Community 47 - "test_agent_interop.py"
Cohesion: 0.22
Nodes (8): manual_prompt_path(), manual_response_path(), Path, build_assembler_output(), _prepare_run(), Path, Tests for the agent-portable CV pipeline surface., TestAgentInterop

### Community 48 - "ingest_nav_jobs.py"
Cohesion: 0.23
Nodes (15): mark_stale_jobs_inactive(), Any, Shared helpers for job ingest scripts (NAV, FINN, …)., Mark ACTIVE rows for *source* not seen in the current ingest run as INACTIVE., strip_html(), effective_if_modified_since(), feed_item_rogaland_guess(), main() (+7 more)

### Community 49 - "build_ingest_cycle_command"
Cohesion: 0.22
Nodes (5): build_ingest_cycle_command(), Build ``scripts/run_job_search_cycle.py`` argv for dashboard ingest., Tests for dashboard ingest-cycle helpers (no Streamlit runtime)., TestBuildIngestCycleCommand, TestParseIngestCycleOutput

### Community 50 - "run_cv_tailoring.py"
Cohesion: 0.26
Nodes (13): contract_metadata(), Any, required_top_level_keys(), validate_output_against_task(), write_contract_manifest(), write_json(), application_artifacts_markdown(), Scaffold note written into each new cv_runs/<id>/ folder. (+5 more)

### Community 51 - "Fujitsu Senior Researcher 8547"
Cohesion: 0.17
Nodes (13): Agentic AI Security and Autonomy, Ethical AI Bias Mitigation Compliance, Fujitsu Research India Private Limited, LLM Safety Security and Alignment, Fujitsu Senior Researcher 8547, Applied AI Prototyping, AI Competence Center ML Research Engineer, Automation Engine Guardrails (+5 more)

### Community 52 - "Senior Data Engineer - Data & AI"
Cohesion: 0.19
Nodes (13): Data Governance, ETL/ELT Pipelines, EXPERIS AS, Lakehouse / Medallion Architecture, Modern Data Platforms, Senior Data Engineer - Data & AI, Snowflake, Databricks, Microsoft Fabric, Databricks, Snowflake, Microsoft Fabric (+5 more)

### Community 53 - "Research Scientist in Information Theory"
Cohesion: 0.21
Nodes (13): Privacy-preserving machine learning, Centre for Quantum Communication Networks and Applications (QCNA), Quantum information theory, Research Scientist in Information Theory, Simula UiB, Statistical learning theory, Centre for Sustainable, Risk-averse and Ethical AI (SURE-AI), Researcher – AI Security and Privacy (+5 more)

### Community 54 - "_render_job_explorer_fragment"
Cohesion: 0.15
Nodes (16): fragment, finish_rerun_trace(), Mark the active rerun trace complete and retain a short sidebar summary., _job_explorer_page_changed(), _job_page_scroll_prev_key(), _job_page_state_key(), paginate_jobs_df(), Prominent free-text search at the top of Job explorer. (+8 more)

### Community 55 - "cv_source_sync.py"
Cohesion: 0.33
Nodes (8): enrich_body_from_front_matter(), full_cv_markdown(), _hobby_bullets(), _language_bullets(), Apply languages and hobbies from YAML front matter into markdown sections., Rebuild file text with front matter + enriched body for run sync., Replace bullet list under ## Section until the next ## heading., _replace_section_bullets()

### Community 56 - "TestCoverLetterGenerator"
Cohesion: 0.35
Nodes (3): build_cover_letter_prompt(), Path, TestCoverLetterGenerator

### Community 57 - "Senior Integration Engineer"
Cohesion: 0.18
Nodes (11): Agentic AI Frameworks, Coding Agents, AI and Agents for Insights Work, Data og AI Engineer, PwC Norway, Scalable Data and AI Solutions Consulting, AI Agents for Cloud Integration, Azure Cloud Integration (Logic Apps APIM ADF) (+3 more)

### Community 58 - "Fagansvarlig dataforskning og kunstig intelligens"
Cohesion: 0.17
Nodes (12): Fagansvarlig dataforskning og kunstig intelligens, Språkmodeller, agenter og moderne KI-arkitektur, MLOps og modellforvaltning, Ansvarlig bruk av KI, Skagerak Kraft AS, Tidsserieanalyse og forecasting, MLOps, AI, AI-agenter og automatisering (+4 more)

### Community 59 - "Data Scientist - Gjensidige AI CoE"
Cohesion: 0.20
Nodes (11): Center of Excellence for AI og automatisering (Skadedivisjonen), Data Scientist - Gjensidige AI CoE, Databricks og dbt, Generativ AI, språkmodeller og RAG, Gjensidige, LangChain / LangGraph, Business Intelligence og Analytics-konsulent / Data- og AI engineer, ETL/ELT med høy datakvalitet (+3 more)

### Community 60 - "Generative AI Specialist - Statnett"
Cohesion: 0.33
Nodes (6): AI agents in Copilot Studio / Azure Foundry, Power Platform, Copilot Studio, UiPath, Azure AI Foundry, Automation and digital assistants, Generative AI in IT/OT architecture, Generative AI Specialist - Statnett, Statnett

### Community 61 - "Post-doctoral Research Fellow in AI and Cultural Heritage"
Cohesion: 0.22
Nodes (11): CreaTeME Centre for Excellence in Education, MishMash - Center for AI and Creativity, AI for Nordic cultural heritage discovery and rights, Post-doctoral Research Fellow in AI and Cultural Heritage, University of Agder (UiA), WP6 AI for cultural heritage, Generative AI and disinformation narratives, Large language models and democratic public trust (+3 more)

### Community 62 - "Supplementary Application Documents"
Cohesion: 0.20
Nodes (10): application_letter.md, cover_letter.md, Cover Letter Voice, CV Tailoring Style, MITCH EVANS Placeholder, research_proposal.md, Supplementary Application Documents, Step 07 Cover Letter (+2 more)

### Community 63 - "resolve_sidebar_photo_path"
Cohesion: 0.38
Nodes (7): _ensure_photo_placeholder(), _prepare_sidebar_photo_file(), Path, Circular PNG placeholder for sidebar headshot when no private photo is…, Center-crop to square and apply a circular mask (matches sidebar headshot…, Private photo (env/mapping/CLI) or in-repo placeholder., resolve_sidebar_photo_path()

### Community 64 - "localize_run"
Cohesion: 0.24
Nodes (8): localize_run(), looks_like_norwegian_cover_letter(), looks_like_norwegian_cv(), Path, True when markdown uses Norwegian CV section labels / H1., Heuristic: body uses common Bokmål markers (not just a Norwegian role title)., Norwegian localization must write *_no.md and never replace English sources., TestNorwegianPathGuards

### Community 65 - "AI Innovation Lead - Tieto Banktech"
Cohesion: 0.20
Nodes (10): Agentic AI frameworks and MCP, GenAI methods, Designing and deploying machine learning models, People Made Machines (PMM), Senior AI Engineer - People Made Machines, Agentic workflows and tool use, AI Innovation Lead - Tieto Banktech, AI governance in banking / regulatory context (+2 more)

### Community 66 - "Principal AI Enablement Engineer"
Cohesion: 0.20
Nodes (10): AI Engineer - Laerdal Medical, Internal AI enablement, Laerdal Medical, Power Platform, Internal AI stack / platform, On-prem LLM and GPU infrastructure, Principal AI Enablement Engineer, Six Robotics (+2 more)

### Community 67 - "score_jobs.py"
Cohesion: 0.16
Nodes (15): matches_academic_research_employer(), matches_any_include_term(), term_matches(), find_tek_match(), haystack_for_job(), load_tek_by_norm(), main(), norm_company() (+7 more)

### Community 68 - "ingest_finn_jobs.py"
Cohesion: 0.23
Nodes (17): build_job_url(), load_queries(), location_guess_rogaland(), main(), parse_location_guess(), Any, Namespace, row_from_detail() (+9 more)

### Community 69 - "_dismiss_apply_modify_dialog"
Cohesion: 0.20
Nodes (10): _dismiss_apply_modify_dialog(), _mark_dashboard_scroll_restore(), _on_apply_dialog_cancel_click(), _on_apply_dialog_close_click(), _on_apply_dialog_dismiss(), Request scroll restore on the next full dashboard render (e.g. after dialog…, Clear dialog flags immediately; optionally drop completed pipeline UI state.…, st.dialog X / Esc: drop dialog flags only (pipeline keeps running). (+2 more)

### Community 70 - "run_demo.py"
Cohesion: 0.45
Nodes (10): assemble_run(), copy_seed_outputs(), ensure_demo_cv_dir(), main(), missing_agent_outputs(), prepare_run(), print_walkthrough(), Path (+2 more)

### Community 71 - "Privacy-First Workflow"
Cohesion: 0.25
Nodes (9): Private CV Data Separation, Project Boundary, Anonymized Placeholders, Privacy-First Workflow, check_safe_to_push.py, Reveal CV, shared Module, Tailor in Public, Reveal in Private (+1 more)

### Community 72 - "has_profile_relevance"
Cohesion: 0.27
Nodes (6): filter_academic_roles_df(), has_profile_relevance(), Any, True when a scored job has CV keyword/skill overlap. Location-only (+5) and…, Drop non-academic rows when keep_academic_only is True (pandas DataFrame)., ProfileRelevanceTests

### Community 74 - "Run Folder Contract"
Cohesion: 0.25
Nodes (8): agent_apply_job.sh, Future MCP Thin Wrapper, Provider: cursor, Provider: manual, Run Folder Contract, Cursor Token Metering Opacity, cv_generation Module, pypdf

### Community 75 - "Retrieval-Augmented Generation (RAG)"
Cohesion: 0.25
Nodes (8): Retrieval-Augmented Generation (RAG), Vector Search, KI-Driven Ecosystem for Norwegian Export, Norwegian Energy Partners, Platform Engineer & AI-enabler, AI Engineer (Platform/Cloud), Norconsult Digital, RAG and Agent-Based Solutions

### Community 76 - "application_status_upsert_row"
Cohesion: 0.32
Nodes (5): application_status_upsert_row(), Normalize DB/pandas cell values to optional stripped text., Build ``upsert_application`` payload for a status change. Preserves notes,…, _sql_optional_text(), TestApplicationStatusUpsertRow

### Community 77 - "timing_span"
Cohesion: 0.25
Nodes (8): _apply_dialog_snapshot(), Context manager that logs a timing event on exit., timing_span(), Open Apply/Modify when session flags are ready; return True to skip caller body., True when Apply/Modify dialog flags are ready (pure helper for tests +…, Drop orphan ``apply_dialog_*`` flags so an empty dialog never mounts., _reconcile_apply_dialog_state(), yield_to_apply_modify_dialog()

### Community 78 - "job_search Module"
Cohesion: 0.29
Nodes (7): agent_cli, Dashboard vs External Agents, Norwegian B1 Localization, job_search Module, Norway-First Locale Strategy, selectolax, streamlit

### Community 79 - "Industry CV Track"
Cohesion: 0.29
Nodes (7): Iconify API Fetch, Lucide CV Sidebar Icons, Academic CV Track, Industry CV Track, track_selector Subagent, Demo Academic CV Source, track_selector Spec

### Community 80 - "Ethics of Embodied AI"
Cohesion: 0.33
Nodes (7): Ethics of Embodied AI, Norwegian Centre for Embodied AI (NCEI), NCEI Ethics Framework / Ethics Toolbox, Physical AI and Robot Morphology Co-design, Postdoctoral Research Fellow in Ethics of Embodied AI, University of Oslo, Robustness Ethics and Accountability in KI

### Community 81 - "Platform for AI-Generated and Project Applications"
Cohesion: 0.29
Nodes (7): AI-First SaaS Platform Architecture, Industrial Decarbonization via Software, LCA.no AS, Principal Architect SaaS Platform & AI, Product Carbon Footprint and LCA Software, Platform for AI-Generated and Project Applications, Security Observability and Monitoring

### Community 82 - "Data Scientist (Gjensidige)"
Cohesion: 0.29
Nodes (7): Center of Excellence for AI and Automation (Claims), Data Scientist (Gjensidige), Databricks and dbt Pipelines, Gjensidige, New AI Unit for Insurance Services, Fremtind, Senior Data Scientist (Fremtind)

### Community 83 - "Platform for responsible AI"
Cohesion: 0.40
Nodes (6): Trustworthy and responsible AI, Bridge from prototyping to production (Dev → Prod), AI platforms and paved road for developers, Platform for responsible AI, Senior AI Platform Engineer - Storebrand, Storebrand

### Community 84 - "Private Identity Boundary"
Cohesion: 0.33
Nodes (6): Deanonymize Privately, cv_identity_mapping.json, Deanonymized Output Folder, Private Identity Boundary, private_cv apply / local reveal, private_cv setup

### Community 85 - "Northline ML Engineer Demo Run"
Cohesion: 0.40
Nodes (6): Northline Labs ML Engineer Job, ALEX RIVERA Demo Candidate, Northline ML Engineer Demo Run, scripts/run_demo.py, Demo Northline ML Engineer Job File, ALEX RIVERA Demo Candidate

### Community 86 - "Digital Twins"
Cohesion: 0.40
Nodes (6): Digital Twins, Falkor (KONGSBERG), Industrial AI Software, MLOps, Software AI Engineer, MLOps for ML Lifecycle

### Community 87 - "ML/AI Engineer"
Cohesion: 0.33
Nodes (6): LLM Inference Optimization, ML/AI Engineer, Targeting and Personalization, Piano Software Norway, RAG Pipelines, RAG and Generative AI for Claims

### Community 88 - "Vision AI Sensor Solutions"
Cohesion: 0.33
Nodes (6): Associate Software Engineer - Computer Vision & AI, NOV (National Oilwell Varco), Object Detection and Scene Perception, Monocular and Stereo Camera on GPU Linux, Vision AI Sensor Solutions, Computer Vision (Preferred Experience)

### Community 89 - "Field Digital Twins"
Cohesion: 0.33
Nodes (6): Drought Stress Phenotyping, Field Digital Twins, Norwegian University of Life Sciences (NMBU), Postdoctoral Fellow AI-Driven Digital Phenotyping, SmartWheat Project, UAV Multispectral Hyperspectral RGB Imagery

### Community 90 - "Postdoctoral Research Fellow Mathematical Foundations of AI"
Cohesion: 0.33
Nodes (6): Geometric Deep Learning, Lie Størmer Center, Postdoctoral Research Fellow Mathematical Foundations of AI, Structure-Preserving Algorithms for ML, SURE-AI Project, UiT The Arctic University of Norway

### Community 91 - "KI-ingeniør Data Scientist (Prosjektstilling)"
Cohesion: 0.33
Nodes (6): Data-Centric Defense with AI as Force Multiplier, Forsvaret, Forsvarets Senter for Data og KI, KI-ingeniør Data Scientist (Prosjektstilling), MLOps and CI/CD for Operational AI, MLOps and Model Monitoring in Production

### Community 92 - "Data Scientist - NORCE Analytics"
Cohesion: 0.33
Nodes (6): Data Lake / Lakehouse Analytics-Ready Data, Data Scientist - NORCE Analytics, Digital Twins (Project Domain), TensorFlow PyTorch scikit-learn, NORCE Research AS, NORCE Analytics Initiative

### Community 93 - "Postdoctoral Fellow – AI for Decisions (AID)"
Cohesion: 0.21
Nodes (12): AI for Decisions (AID) Center, Postdoctoral Fellow – AI for Decisions (AID), Human–AI collaboration for decision-making, Human-in-the-loop decision support, ISCHI research group, NTNU, Accounting automation platform, AI vs deterministic rules vs human-in-the-loop (+4 more)

### Community 94 - "Tech Lead Bergen - AI-assisted development"
Cohesion: 0.50
Nodes (5): AI-assistert utvikling og agentic coding, Cursor, Claude Code, GitHub Copilot, AugmentCode, Java, Spring Boot, PostgreSQL, AWS/Heroku, Spekkdrevet utvikling, Tech Lead Bergen - AI-assisted development

### Community 95 - "Energy Estimation Formula v1"
Cohesion: 0.33
Nodes (6): Energy Estimation Formula v1, Luccioni et al. 2023, Patterson et al. 2021, pipeline_metrics.json, run_agent_pipeline, run_cv_tailoring

### Community 96 - "LinkedIn lowercase in wordmark logo"
Cohesion: 0.40
Nodes (5): CV LinkedIn profile contact link, LinkedIn lowercase in wordmark logo, Rounded letter i with tittle dot, Rounded arched letter n, LinkedIn professional networking platform

### Community 97 - "Connected contact figure paths"
Cohesion: 0.40
Nodes (5): Connected contact figure paths, LinkedIn-style people network SVG icon, Small circle person head, Vertical torso bar for primary person, CV LinkedIn professional profile marker

### Community 98 - "Rounded rectangle card frame"
Cohesion: 0.40
Nodes (5): Avatar circle for person face, ORCID ID badge SVG icon, Identity text line stubs on card, CV ORCID researcher ID profile link, Rounded rectangle card frame

### Community 99 - "Circular light-gray frame around figure"
Cohesion: 0.40
Nodes (5): Circular light-gray frame around figure, CV header photo slot when no real photo, Default profile photo placeholder avatar, Abstract head circle shape, Abstract shoulders / torso oval

### Community 100 - "Demo Industry CV Source"
Cohesion: 0.40
Nodes (5): ALEX RIVERA, Demo Industry CV Source, Demo final_cv.md, Final CV ML ENGINEER Role, Demo tailored_cv.md

### Community 101 - "log_state_diff"
Cohesion: 0.40
Nodes (5): log_state_diff(), _normalize_state_value(), Snapshot a small, high-signal subset of session state for rerun diffs., Log only state keys that changed since the previous completed rerun., snapshot_state_subset()

### Community 102 - "Data Engineer GEOMETOC (Etterretningstjenesten)"
Cohesion: 0.40
Nodes (5): Data Engineer GEOMETOC (Etterretningstjenesten), Etterretningstjenesten, Automated Geographic Data Pipelines, GEOMETOC Geographic Meteorological Oceanographic Data, Geographic Information Systems (GIS)

### Community 103 - "Cyber Security Engineer - Remota"
Cohesion: 0.40
Nodes (5): Cyber Security Engineer - Remota, Identitets- og tilgangsstyring, endepunktsbeskyttelse, ISO 27001 og NIS2, Remota AS, Remote Operations Center (ROC)

### Community 104 - "Postdoktor innen e-helse/tjenester"
Cohesion: 0.40
Nodes (5): Samskaping av e-helseløsninger, Digital hjemmeoppfølging for skrøpelige eldre, Høgskulen på Vestlandet / Senter for omsorgsforskning vest, Postdoktor innen e-helse/tjenester, Forskningsgruppen Teknologi, helse og samfunn

### Community 105 - "English cover letter voice"
Cohesion: 0.40
Nodes (5): Academic application letter style, English connectors and flow, English cover letter voice, Norwegian B1 writing style, Norwegian B1 connectors

### Community 108 - "check_safe_to_push.py"
Cohesion: 0.70
Nodes (4): main(), Path, scan_file(), should_scan()

### Community 109 - "Birthday cake CV icon (date of birth)"
Cohesion: 0.50
Nodes (4): Birthday cake CV icon (date of birth), Single-tier cake body with frosting wave, Three candles with flame dots, CV contact marker for date of birth

### Community 110 - "Birthday cake SVG icon (date of birth)"
Cohesion: 0.50
Nodes (4): Birthday cake SVG icon (date of birth), Rounded cake body with wavy frosting path, Light stroke line-art UI glyph on dark, Three candle sticks with flame dots

### Community 111 - "Email envelope SVG contact icon"
Cohesion: 0.50
Nodes (4): CV sidebar email address marker, Email envelope SVG contact icon, Diagonal flap path meeting at center, Rounded rectangle envelope body

### Community 112 - "GitHub Octocat silhouette logo"
Cohesion: 0.50
Nodes (4): Cat-like ears on Octocat outline, GitHub Octocat silhouette logo, CV GitHub profile / code portfolio link, GitHub version control platform brand

### Community 113 - "Head body tentacle stroke path"
Cohesion: 0.50
Nodes (4): CV GitHub repository profile link marker, Head body tentacle stroke path, GitHub Octocat outline SVG icon, Curved tail appendage path

### Community 114 - "Diamond-shaped mortarboard top"
Cohesion: 0.50
Nodes (4): Google Scholar academic profile CV marker, Diamond-shaped mortarboard top, Graduation cap / mortarboard icon, Tassel hanging from cap corner

### Community 115 - "Open academic book / scholar SVG icon"
Cohesion: 0.50
Nodes (4): Open academic book / scholar SVG icon, Angled book cover layers, Google Scholar citations profile CV link, Curved page sides hanging below covers

### Community 116 - "Map pin / location marker icon"
Cohesion: 0.50
Nodes (4): CV geographic address / city contact marker, Inner circle eye of map pin, Map pin / location marker icon, Inverted teardrop pin body

### Community 117 - "Map pin location SVG icon"
Cohesion: 0.50
Nodes (4): Centered circle location dot, CV sidebar location / residence field marker, Map pin location SVG icon, Teardrop pin outline path

### Community 118 - "Mail envelope SVG icon"
Cohesion: 0.50
Nodes (4): CV email contact alternate glyph, Mail envelope SVG icon, Diagonal flap fold path, Rounded rectangle envelope body

### Community 119 - "Map-pin SVG location marker"
Cohesion: 0.50
Nodes (4): Center circle geographic point, CV geographic location field glyph, Map-pin SVG location marker, Teardrop pin outline path

### Community 120 - "ORCID ID card / badge icon"
Cohesion: 0.50
Nodes (4): ORCID ID card / badge icon, Person head-and-shoulders silhouette, ORCID researcher persistent identifier link, Two horizontal text placeholder bars

### Community 121 - "Earpiece end of handset"
Cohesion: 0.50
Nodes (4): CV phone number contact marker, Earpiece end of handset, Telephone handset contact icon, Mouthpiece end of handset

### Community 122 - "Phone call receiver SVG icon"
Cohesion: 0.50
Nodes (4): Call connection / dial UI metaphor, Phone call receiver SVG icon, Curved modern handset stroke, CV telephone contact field marker

### Community 123 - "jd_parser Subagent"
Cohesion: 0.67
Nodes (4): jd_parser Subagent, keyword_ranker Subagent, jd_parser Spec, keyword_ranker Spec

### Community 124 - "Attensi Next-Gen Data Platform"
Cohesion: 0.50
Nodes (4): Attensi Next-Gen Data Platform, Attensi Data Engineer, AI-Assisted Development Tools, AW Academy Data Engineer Program

### Community 125 - "Enhetsleder for IT og digitalisering"
Cohesion: 0.50
Nodes (4): Bjerkreim kommune, Enhetsleder for IT og digitalisering, Google Workspace for Education, Microsoft 365 og Intune

### Community 126 - "Agentic Commerce"
Cohesion: 0.50
Nodes (4): Agentic Commerce, LLM-driven prototypes, Vipps shopping assistant, Vipps MobilePay

### Community 127 - "ForwardMedia Research Centre"
Cohesion: 0.50
Nodes (4): Democracy base, ForwardMedia Research Centre, Responsible media technology, University of Boston

### Community 128 - "Tritium Consulting"
Cohesion: 0.50
Nodes (4): Azure and AWS deployment, MEAN stack, REST APIs and scalable backends, Tritium Consulting

### Community 131 - "Email envelope CV contact icon"
Cohesion: 0.67
Nodes (3): CV email / messaging contact channel, Envelope flap V-fold lines, Email envelope CV contact icon

### Community 133 - "Piano Software Norway HTML fixture"
Cohesion: 0.67
Nodes (3): Piano Software Norway ML/AI Engineer, FINN HTML-only job detail fixture, Piano Software Norway HTML fixture

### Community 134 - "Git-ready privacy plan"
Cohesion: 0.67
Nodes (3): Pluggable agent providers, check_safe_to_push.py, Git-ready privacy plan

## Knowledge Gaps
- **215 isolated node(s):** `SubagentSpec`, `render_private_cv.example.sh script`, `PYTHONPATH`, `agent_apply_job.sh script`, `bulk_apply_deanonymize.sh script` (+210 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_default_profiles()` connect `JobProfile` to `score_jobs.py`, `ingest_finn_jobs.py`, `matches_academic_role_display`, `private_cv.py`, `ingest_nav_jobs.py`, `run_agent_pipeline.py`, `run_cv_tailoring.py`?**
  _High betweenness centrality (0.041) - this node is a cross-community bridge._
- **Why does `Row` connect `fetch_tek_rogaland_members.py` to `score_jobs.py`?**
  _High betweenness centrality (0.037) - this node is a cross-community bridge._
- **Why does `supplementary_artifact_filenames()` connect `private_cv.py` to `PrivateConfig`, `dashboard.py`, `_dialog_artifact_bundle`, `deanonymize_cvs.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `main()` (e.g. with `connect()` and `init_schema()`) actually correct?**
  _`main()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `ApplyPipelineOptions` (e.g. with `FinnJobSession` and `TestApplicationStatusUpsertRow`) actually correct?**
  _`ApplyPipelineOptions` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `PrivateConfig` (e.g. with `TestResolveRunDir` and `TestPrivateCvDeanonOutput`) actually correct?**
  _`PrivateConfig` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `SubagentSpec`, `render_private_cv.example.sh script`, `PYTHONPATH` to the rest of the system?**
  _215 weakly-connected nodes found - possible documentation gaps or missing edges._