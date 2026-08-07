# Graph Report - .  (2026-08-07)

## Corpus Check
- 220 files · ~124,579 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2087 nodes · 4635 edges · 148 communities (133 shown, 15 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 210 edges (avg confidence: 0.74)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Private CV Apply
- Dashboard Job Export
- Academic Job Filters
- Apply Pipeline Options
- Pipeline Queue Metrics
- Explorer Pipeline Gates
- Dashboard DB Loaders
- FINN Job Client
- CV Assemble Markdown
- Norwegian CV Localization
- CV PDF Renderer
- Ingest Keyword Collect
- Pipeline Metrics Format
- Dashboard Debug Trace
- Demo Walkthrough Docs
- Dashboard Search Cache
- NAV Job Ingest
- Agent Pipeline Runner
- PDF Layout Flowables
- FINN Search Queries
- Inspirit Data Platform Jobs
- Location Preferences
- Plain Markdown PDF
- Apply Prompts Config
- Ingest Cycle Dashboard
- Deadline Urgency Utils
- Dashboard Auto Refresh
- Agent Providers
- CV Sidebar Layout
- Apply Dialog Fast Path
- Job Dedup Helpers
- Cover Letter Generator
- Apply Artifact Options
- TEK Rogaland Fetch
- NAV Feed Client
- ATS PDF Check
- Applied Roles UI
- Application Artifacts
- Dashboard Scroll Styles
- CV Style Profile Limits
- Deanonymize Cvs
- Deanonymize Cvs
- Agent Cli
- Run Cv Tailoring
- Agent Interop
- Supplementary Generator
- Render Cv Pdf
- Test Agent Interop
- Dashboard
- Test Dashboard Ingest
- Dashboard
- Job Posting Fujitsu Senior
- Finn 469744220 Senior Data
- Simula Uib Research Scientist
- Test Cover Letter Generator
- Cv Private
- Test Cv Norwegian Paths
- Finn 469351664 Senior Integration
- Finn 471026018 Fagansvarlig Dataforsknin
- Gjensidige Data Scientist 468693066
- Laerdal Ai Engineer
- Uia Postdoc Ai Cultural
- Agents
- Agent Contract
- Cv Pdf Renderer
- Pmm Senior Ai Engineer
- Six Robotics Principal Ai
- Dashboard
- Job Filters
- Test Dashboard Debug
- Run Demo
- Readme
- Cv Source Sync
- Test Job Filters Relevance
- Agent Interop
- Finn 467933786 Platform Engineer
- Dashboard
- Test Academic Track Filter
- Agent Interop
- Cv Automation
- Finn 465564641 Postdoctoral Research
- Finn 468491746 Principal Architect
- Finn 468693066 Data Scientist
- Storebrand Senior Ai Platform
- Privacy
- Readme
- Falkor Software Ai Engineer
- Finn 465089104 Ml Ai
- Finn 466330851 Associate Software
- Finn 467762339 Postdoctoral Fellow
- Finn 468670212 Postdoctoral Research
- Finn 469233460 Ki Ingeni
- Finn 469415440 Data Scientist
- Ntnu Aid Postdoc Human
- Sanna Full Stack Ai
- Pipeline Impact
- Linkedin
- Linkedin
- Orcid
- Cv Photo Placeholder
- Cv Industry Source
- Import Cv Pdf
- Finn 469070200 Data Engineer
- Nav 117D8Fcd-B7F0-43Eb-B6Fd-78C929F6F227
- Nav 32825E09-0F94-4992-B5B6-27231Ec25522
- English Writing Samples
- Test Dashboard Applied Roles
- Repo Paths
- Check Safe To Push
- Cake
- Cake
- Email
- Github
- Github
- Google Scholar
- Google Scholar
- Location
- Location
- Mail
- Map-Pin
- Orcid
- Phone
- Phone
- Cv Automation
- Attensi Data Engineer
- Nav 31Fab261-775B-49Db-88Ff-920037F3D58F
- Vipps Agentic Commerce Engineer
- Forwardmedia Boston Context
- Tritium Backend Context
- Dashboard
- Dashboard
- Email
- Render Private Cv.Example
- Job Detail Html Only
- Git And Privacy
- Dashboard Debug
- init py
- Finn 468154746 Developer Software
- Vipps Agentic Commerce Engineer
- init py
- Agent Apply Job
- Bulk Apply Deanonymize
- init py
- Agent Interop
- Agent Interop
- Requirements
- Requirements
- Requirements

## God Nodes (most connected - your core abstractions)
1. `main()` - 52 edges
2. `ApplyPipelineOptions` - 35 edges
3. `haystack_for_filter()` - 32 edges
4. `PrivateConfig` - 30 edges
5. `connect()` - 30 edges
6. `init_schema()` - 30 edges
7. `debug_log()` - 29 edges
8. `run()` - 29 edges
9. `PipelineMetricsCollector` - 26 edges
10. `parse_cv_markdown()` - 25 edges

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

## Communities (148 total, 15 thin omitted)

### Community 0 - "Private CV Apply"
Cohesion: 0.05
Nodes (91): supplementary_artifact_filenames(), _apply_localized_artifacts(), apply_one_run(), _apply_supplementary_artifacts(), _audit_markdown(), build_parser(), cmd_all_runs(), cmd_apply() (+83 more)

### Community 1 - "Dashboard Job Export"
Cohesion: 0.07
Nodes (57): _append_pipeline_log_line(), best_job_url(), cv_job_filename(), enrich_jobs_df(), export_job_to_cv_file(), format_job_export_text(), format_location(), _handle_application_status_update() (+49 more)

### Community 2 - "Academic Job Filters"
Cohesion: 0.07
Nodes (35): apply_dashboard_filters(), effective_academic_roles_only(), Academic CV track always applies the strict research-role display filter., Post-filter overview rows with the same rules as ingest / explorer., filter_academic_roles_df(), _filter_text_part(), haystack_for_filter(), haystack_title_employer() (+27 more)

### Community 3 - "Apply Pipeline Options"
Cohesion: 0.07
Nodes (44): normalize_apply_language(), _activate_pipeline_from_item(), apply_dialog_language_key(), apply_pipeline_options_from_mapping(), apply_pipeline_options_to_mapping(), ApplyPipelineOptions, build_pipeline_queue_item(), _can_enqueue_current_job() (+36 more)

### Community 4 - "Pipeline Queue Metrics"
Cohesion: 0.06
Nodes (55): load_pipeline_metrics(), Path, Resolve a run basename to ``cv_generation/cv_runs/<run_id>``., resolve_run_dir(), _advance_pipeline_queue_after_finish(), _apply_modify_dialog_body(), _build_pipeline_result(), dequeue_pipeline_item() (+47 more)

### Community 5 - "Explorer Pipeline Gates"
Cohesion: 0.05
Nodes (30): build_explorer_filter_chips(), can_enqueue_pipeline(), _explorer_jobs_cache_fingerprint(), extract_run_ids_from_notes(), pipeline_metrics_summary_for_notes(), pipeline_phase_is_busy(), pipeline_queue_is_full(), pipeline_queue_remaining() (+22 more)

### Community 6 - "Dashboard DB Loaders"
Cohesion: 0.10
Nodes (41): cache_data, Connection, count_research_roles_in_db(), filter_phd_student_df(), ingest_active_source_counts(), load_applications_df(), load_applied_roles_df(), load_jobs_df() (+33 more)

### Community 7 - "FINN Job Client"
Cohesion: 0.09
Nodes (29): HTMLParser, _address_fields(), build_search_url(), _card_text(), _collect_schema_objects(), _detail_title(), extract_finnkode(), FinnJobSession (+21 more)

### Community 8 - "CV Assemble Markdown"
Cohesion: 0.10
Nodes (36): apply_bullet_tailor(), assemble_final_cv_markdown(), _coerce_bullets(), _collect_institution_names(), _degree_kind(), designation_from_job_role(), _education_institutions_by_degree(), experience_role_key() (+28 more)

### Community 9 - "Norwegian CV Localization"
Cohesion: 0.09
Nodes (34): ArtifactKind, build_localization_prompt(), count_experience_bullets(), count_experience_roles(), count_norwegian_cover_letter_body_words(), _cover_letter_body_text(), detect_track(), _experience_section_lines() (+26 more)

### Community 10 - "CV PDF Renderer"
Cohesion: 0.09
Nodes (35): _cleanup(), _compact_sidebar_stack(), _contact_href(), _contact_icon_key(), _contact_paragraph_markup(), _detect_document_language(), _education_degree_field_line(), _education_header_row() (+27 more)

### Community 11 - "Ingest Keyword Collect"
Cohesion: 0.10
Nodes (29): collect_ingest_keywords(), collect_keywords_from_cvs(), Merge CV profile keywords/skills with curated application-history boosts for…, Keywords used by NAV/FINN ingest for --keyword-filter matching and --list-…, Expose demo detection for tests and diagnostics., using_demo_cv_keywords(), all_default_finn_search_queries(), merge_unique_terms() (+21 more)

### Community 12 - "Pipeline Metrics Format"
Cohesion: 0.11
Nodes (19): estimate_energy_kwh(), estimate_tokens_from_text(), format_duration_sec(), format_pipeline_metrics_summary(), json_dumps(), peak_rss_mb(), PipelineMetrics, PipelineMetricsCollector (+11 more)

### Community 13 - "Dashboard Debug Trace"
Cohesion: 0.13
Nodes (33): _active_rerun_context(), _append_file(), debug_enabled_from_env(), debug_log(), _format_event(), _generate_rerun_id(), init_dashboard_debug(), is_debug_enabled() (+25 more)

### Community 14 - "Demo Walkthrough Docs"
Cohesion: 0.07
Nodes (33): ALEX RIVERA fictional candidate, Anonymized-first public demo, One-repo job search and CV generation architecture, Demo walkthrough, scripts/run_demo.py, 60-second demo script, Tailor in public Reveal in private, Private CV workflow (+25 more)

### Community 15 - "Dashboard Search Cache"
Cohesion: 0.08
Nodes (33): apply_text_search_filter(), _cache_exec_count(), finish_rerun_trace(), Mark the active rerun trace complete and retain a short sidebar summary., Context manager that logs a timing event on exit., timing_span(), dedupe_jobs_df(), _import_module_resilient() (+25 more)

### Community 16 - "NAV Job Ingest"
Cohesion: 0.12
Nodes (25): effective_if_modified_since(), feed_item_rogaland_guess(), main(), parse_state_timestamp(), Any, datetime, Namespace, rogaland_from_locations() (+17 more)

### Community 17 - "Agent Pipeline Runner"
Cohesion: 0.17
Nodes (30): load_json(), list_providers(), Path, Role from JD parser output, then job_posting.txt, then task job_meta., resolve_job_role_title(), build_prompt(), extract_final_cv_markdown(), extract_priority_terms() (+22 more)

### Community 18 - "PDF Layout Flowables"
Cohesion: 0.18
Nodes (31): _academic_main_column_story_from_cv(), _ats_list_paragraph(), CvContent, _education_flowables(), _experience_flowables(), _experience_header_row(), _icon_row(), _industry_main_column_story_from_cv() (+23 more)

### Community 19 - "FINN Search Queries"
Cohesion: 0.14
Nodes (24): coerce_expires_value(), Any, Normalize expires / validThrough from DB, API, or JSON-LD to a plain string or…, build_job_url(), Default FINN.no search queries tuned from application history., mark_stale_jobs_inactive(), Any, Shared helpers for job ingest scripts (NAV, FINN, …). (+16 more)

### Community 20 - "Inspirit Data Platform Jobs"
Cohesion: 0.07
Nodes (28): Azure ML and Fabric Notebooks, Data Engineer (Inspirit), Data Scientist (Inspirit), dbt Data Transformations, Inspirit365, Medallion / Star-Snowflake Data Modeling, Microsoft Fabric / Azure Data Platform, BI Analyseplattform (+20 more)

### Community 21 - "Location Preferences"
Cohesion: 0.10
Nodes (12): _candidate_tokens(), LocationMatch, match_preferred_location(), merged_preferred_locations(), normalize_location_token(), _preferred_tokens(), _FakeResponse, JobSearchPipelineTests (+4 more)

### Community 22 - "Plain Markdown PDF"
Cohesion: 0.12
Nodes (15): markdown_inline_to_reportlab(), Convert lightweight markdown inline emphasis to ReportLab paragraph markup.…, _add_paragraph(), _add_table(), build_plain_markdown_story(), _is_table_separator_row(), _paragraph_styles(), _parse_table_row() (+7 more)

### Community 23 - "Apply Prompts Config"
Cohesion: 0.13
Nodes (12): apply_language_markdown_section(), apply_prompts_markdown_section(), apply_prompts_path(), merge_apply_prompts(), normalize_apply_prompts(), Path, Optional user tailoring instructions for a CV run folder., Per-job popover may override sidebar; ``inherit`` keeps the sidebar default. (+4 more)

### Community 24 - "Ingest Cycle Dashboard"
Cohesion: 0.09
Nodes (21): _execute_ingest_cycle(), get_db_path(), IngestCycleOptions, _inject_dashboard_css(), parse_ingest_cycle_output(), pipeline_fallback_eligible(), _pipeline_poll_fast_path_active(), True when the page-level fallback should render the active pipeline. (+13 more)

### Community 25 - "Deadline Urgency Utils"
Cohesion: 0.20
Nodes (15): date, apply_soon_badge(), days_until_deadline(), is_apply_soon(), _normalize_year(), parse_deadline(), Parse job application deadlines and compute urgency., Days from today until deadline (0 = today). None if unknown or past parsing. (+7 more)

### Community 26 - "Dashboard Auto Refresh"
Cohesion: 0.13
Nodes (13): Sidebar toggle for periodic cache refresh (does not run ingest)., format_auto_refresh_label(), Dashboard data refresh helpers (no Streamlit dependency)., True when ``now_monotonic`` is at or past the next scheduled cache refresh., Return interval length in seconds, or ``None`` when auto-refresh is off., refresh_interval_seconds(), should_periodic_refresh(), render_auto_refresh_sidebar_section() (+5 more)

### Community 27 - "Agent Providers"
Cohesion: 0.23
Nodes (11): ABC, AgentProvider, AgentRunResult, AnthropicAgentProvider, CursorAgentProvider, get_provider(), ManualAgentProvider, OpenAIAgentProvider (+3 more)

### Community 28 - "CV Sidebar Layout"
Cohesion: 0.14
Nodes (19): BaseDocTemplate, _build_dual_column_layout(), _draw_full_height_sidebar(), _ensure_photo_placeholder(), _on_cv_page(), _prepare_sidebar_photo_file(), Path, Circular PNG placeholder for sidebar headshot when no private photo is… (+11 more)

### Community 29 - "Apply Dialog Fast Path"
Cohesion: 0.12
Nodes (14): _apply_dialog_fast_path_active(), apply_dialog_ready(), _apply_dialog_snapshot(), pipeline_active_for_job_key(), Open Apply/Modify when session flags are ready; return True to skip caller body., True when session holds an active pipeline for ``job_key`` (no Streamlit)., True when Apply/Modify may open: valid row context or active pipeline for the…, Return session-state patches that clear stale dialog flags (no Streamlit). (+6 more)

### Community 30 - "Job Dedup Helpers"
Cohesion: 0.17
Nodes (15): dedup_key(), dedupe_jobs_df(), _merge_duplicate_fields(), normalize_text(), _pick_primary_index(), Any, DataFrame, Series (+7 more)

### Community 31 - "Cover Letter Generator"
Cohesion: 0.27
Nodes (17): _call_cover_letter_agent(), cover_letter_markdown_path(), CoverLetterResult, generate_cover_letter_markdown(), is_cover_letter_required(), manual_cover_letter_prompt_path(), manual_cover_letter_response_path(), maybe_generate_cover_letter() (+9 more)

### Community 32 - "Apply Artifact Options"
Cohesion: 0.13
Nodes (11): apply_button_label(), _cached_default_artifact_options(), default_artifact_options(), _dialog_artifact_bundle(), Pre-check artifact generation toggles from posting detection., Cached JD scan for academic artifact checkboxes (plain industry skips the scan)., True when title/employer look like a postdoc/researcher call (cheap; no JD…, One-shot artifact defaults / existing-file flags for the Apply dialog. (+3 more)

### Community 33 - "TEK Rogaland Fetch"
Cohesion: 0.24
Nodes (19): addr_rogaland(), analyze_member(), brreg_query_name(), collect_brreg_org_addresses(), curl_bytes(), curl_json(), extract_content_html(), fetch_all_underenheter() (+11 more)

### Community 34 - "NAV Feed Client"
Cohesion: 0.21
Nodes (14): default_if_modified_since(), fetch_feed_entry(), fetch_feed_page(), fetch_public_token(), http_get_json(), NavFeedSession, Any, datetime (+6 more)

### Community 35 - "ATS PDF Check"
Cohesion: 0.24
Nodes (17): build_report(), compare_markdown_keywords(), detect_format_issues(), extract_pdf_text(), keyword_coverage(), load_must_have_terms(), load_priority_terms(), main() (+9 more)

### Community 36 - "Applied Roles UI"
Cohesion: 0.13
Nodes (11): bulk_deanonymize_command(), _count_applied_roles(), filter_applied_roles_df(), Build a job row dict suitable for ``execute_apply_pipeline`` from an…, Combined ``cv apply`` command for drafted rows with CV run IDs in notes., Collapsible applied-roles list with status filter and compact rows., Drafts and applied-role lists for the current CV track., render_applied_roles_section() (+3 more)

### Community 37 - "Application Artifacts"
Cohesion: 0.19
Nodes (9): detect_supplementary_artifacts(), normalize_upper_name_variants(), Supplementary application markdown files beyond final_cv.md. Used by private_cv…, Heuristic: which supplementary files the posting likely needs., Add title-case aliases for fully-uppercase personal-name keys. Example: ``MITCH…, supplementary_artifact_for(), SupplementaryArtifact, Application artifact registry and deanonymize helpers. (+1 more)

### Community 38 - "Dashboard Scroll Styles"
Cohesion: 0.15
Nodes (16): _finalize_dashboard_scroll(), Inject unified scroll manager once per rerun, after page content exists., format_treff_count(), inject_scroll_manager(), inject_scroll_restoration(), inject_scroll_to_job_list(), Streamlit dashboard layout styles (job cards, explorer search, pagination)., One boot script: install manager once, then restore and/or scroll-to-list. (+8 more)

### Community 39 - "CV Style Profile Limits"
Cohesion: 0.18
Nodes (11): _apply_profile_length_limits(), Trim Profile / Summary so PDF main column stays within a practical page budget., normalize_profile_paragraphs(), normalize_summary_bullets(), Shared CV tailoring style rules for agents and run scaffolding. See…, Trim to max_chars, preferring a word boundary and a closing period., Enforce Profile length for PDF layout. Returns (trimmed paragraphs, warnings)., Enforce academic Summary bullet count and length. (+3 more)

### Community 40 - "Deanonymize Cvs"
Cohesion: 0.23
Nodes (15): is_placeholder_value(), list_files(), load_mapping(), main(), parse_args(), partial_document_glob_hint(), Namespace, Path (+7 more)

### Community 41 - "Deanonymize Cvs"
Cohesion: 0.19
Nodes (12): _abbreviate_norwegian_months(), apply_replacements(), expand_mapping_norwegian_dates(), looks_like_cv_date_key(), norwegian_date_variants(), _preferred_norwegian_date_value(), CV experience lines often use mar./jul./jun. instead of mars/juli/juni., Plausible Norwegian date strings produced from an English mapping key/value. (+4 more)

### Community 42 - "Agent Cli"
Cohesion: 0.38
Nodes (13): main(), parse_args(), _prior_outputs(), Namespace, Path, _resolve_step(), _run_build_prompt(), _run_pipeline_cmd() (+5 more)

### Community 43 - "Run Cv Tailoring"
Cohesion: 0.24
Nodes (12): contract_metadata(), write_contract_manifest(), application_artifacts_markdown(), Scaffold note written into each new cv_runs/<id>/ folder., as_markdown(), SubagentSpec, main(), parse_args() (+4 more)

### Community 44 - "Agent Interop"
Cohesion: 0.14
Nodes (14): Step 06 assembler, Step 05 ats_checker, Step 04 bullet_tailor, Step 01 jd_parser, Step 02 keyword_ranker, Step 03 track_selector, assembler Subagent, ats_check_pdf (+6 more)

### Community 45 - "Supplementary Generator"
Cohesion: 0.35
Nodes (13): read_apply_prompts(), strip_markdown_response(), build_application_letter_prompt(), build_research_proposal_prompt(), _call_markdown_agent(), _generate_doc(), _manual_paths(), maybe_generate_application_letter() (+5 more)

### Community 46 - "Render Cv Pdf"
Cohesion: 0.21
Nodes (11): is_plain_pdf_markdown(), Path, True when markdown should render as plain one-column PDF (not styled CV)., _to_name_case_if_upper(), _ensure_project_cwd(), _import_renderer(), _looks_like_plain_document(), main() (+3 more)

### Community 47 - "Test Agent Interop"
Cohesion: 0.29
Nodes (4): build_assembler_output(), _prepare_run(), Path, TestAgentInterop

### Community 48 - "Dashboard"
Cohesion: 0.18
Nodes (14): fragment, _job_explorer_page_changed(), _job_page_scroll_prev_key(), _job_page_state_key(), paginate_jobs_df(), Prominent free-text search at the top of Job explorer., Session key tracking prior page so pagination can trigger scroll-to-list., True when Job explorer page index changed since the last render. Compares… (+6 more)

### Community 49 - "Test Dashboard Ingest"
Cohesion: 0.22
Nodes (5): build_ingest_cycle_command(), Build ``scripts/run_job_search_cycle.py`` argv for dashboard ingest., Tests for dashboard ingest-cycle helpers (no Streamlit runtime)., TestBuildIngestCycleCommand, TestParseIngestCycleOutput

### Community 50 - "Dashboard"
Cohesion: 0.18
Nodes (11): _completion_notice_payload(), _dismiss_pipeline_notice(), _open_completion_notice_dialog(), pipeline_job_display_title(), pipeline_notice_id(), Prefer a parked completion (queue advanced); else the idle finished pipeline., Reopen result UI for a finished job (including after queue advanced)., Top-of-page success/error banner for a finished pipeline when dialog is closed. (+3 more)

### Community 51 - "Job Posting Fujitsu Senior"
Cohesion: 0.17
Nodes (13): Agentic AI Security and Autonomy, Ethical AI Bias Mitigation Compliance, Fujitsu Research India Private Limited, LLM Safety Security and Alignment, Fujitsu Senior Researcher 8547, Applied AI Prototyping, AI Competence Center ML Research Engineer, Automation Engine Guardrails (+5 more)

### Community 52 - "Finn 469744220 Senior Data"
Cohesion: 0.19
Nodes (13): Data Governance, ETL/ELT Pipelines, EXPERIS AS, Lakehouse / Medallion Architecture, Modern Data Platforms, Senior Data Engineer - Data & AI, Snowflake, Databricks, Microsoft Fabric, Databricks, Snowflake, Microsoft Fabric (+5 more)

### Community 53 - "Simula Uib Research Scientist"
Cohesion: 0.21
Nodes (13): Privacy-preserving machine learning, Centre for Quantum Communication Networks and Applications (QCNA), Quantum information theory, Research Scientist in Information Theory, Simula UiB, Statistical learning theory, Centre for Sustainable, Risk-averse and Ethical AI (SURE-AI), Researcher – AI Security and Privacy (+5 more)

### Community 54 - "Test Cover Letter Generator"
Cohesion: 0.35
Nodes (3): build_cover_letter_prompt(), Path, TestCoverLetterGenerator

### Community 55 - "Cv Private"
Cohesion: 0.29
Nodes (10): _expand(), _is_real_http_url(), _mapping_raw(), profile_photo_from_mapping(), Path, Build deanonymize search/replace pairs from ``_*_url`` metadata keys. Template…, Return path to a profile photo file, or None to use the in-repo placeholder.…, resolve_profile_photo_path() (+2 more)

### Community 56 - "Test Cv Norwegian Paths"
Cohesion: 0.24
Nodes (6): looks_like_norwegian_cover_letter(), looks_like_norwegian_cv(), True when markdown uses Norwegian CV section labels / H1., Heuristic: body uses common Bokmål markers (not just a Norwegian role title)., Norwegian localization must write *_no.md and never replace English sources., TestNorwegianPathGuards

### Community 57 - "Finn 469351664 Senior Integration"
Cohesion: 0.18
Nodes (11): Agentic AI Frameworks, Coding Agents, AI and Agents for Insights Work, Data og AI Engineer, PwC Norway, Scalable Data and AI Solutions Consulting, AI Agents for Cloud Integration, Azure Cloud Integration (Logic Apps APIM ADF) (+3 more)

### Community 58 - "Finn 471026018 Fagansvarlig Dataforsknin"
Cohesion: 0.18
Nodes (11): Fagansvarlig dataforskning og kunstig intelligens, Språkmodeller, agenter og moderne KI-arkitektur, MLOps og modellforvaltning, Skagerak Kraft AS, Tidsserieanalyse og forecasting, MLOps, AI, AI-agenter og automatisering, AI sandkasser, MVPs og POCs (+3 more)

### Community 59 - "Gjensidige Data Scientist 468693066"
Cohesion: 0.20
Nodes (11): Center of Excellence for AI og automatisering (Skadedivisjonen), Data Scientist - Gjensidige AI CoE, Databricks og dbt, Generativ AI, språkmodeller og RAG, Gjensidige, LangChain / LangGraph, Business Intelligence og Analytics-konsulent / Data- og AI engineer, ETL/ELT med høy datakvalitet (+3 more)

### Community 60 - "Laerdal Ai Engineer"
Cohesion: 0.18
Nodes (11): AI agents in Copilot Studio / Azure Foundry, AI Engineer - Laerdal Medical, Internal AI enablement, Laerdal Medical, Power Platform, Internal AI stack / platform, Power Platform, Copilot Studio, UiPath, Azure AI Foundry, Automation and digital assistants (+3 more)

### Community 61 - "Uia Postdoc Ai Cultural"
Cohesion: 0.22
Nodes (11): CreaTeME Centre for Excellence in Education, MishMash - Center for AI and Creativity, AI for Nordic cultural heritage discovery and rights, Post-doctoral Research Fellow in AI and Cultural Heritage, University of Agder (UiA), WP6 AI for cultural heritage, Generative AI and disinformation narratives, Large language models and democratic public trust (+3 more)

### Community 62 - "Agents"
Cohesion: 0.20
Nodes (10): application_letter.md, cover_letter.md, Cover Letter Voice, CV Tailoring Style, MITCH EVANS Placeholder, research_proposal.md, Supplementary Application Documents, Step 07 Cover Letter (+2 more)

### Community 63 - "Agent Contract"
Cohesion: 0.38
Nodes (8): manual_prompt_path(), manual_response_path(), Any, Path, required_top_level_keys(), validate_output_against_task(), write_json(), Tests for the agent-portable CV pipeline surface.

### Community 64 - "Cv Pdf Renderer"
Cohesion: 0.24
Nodes (10): _draw_centered_sidebar_sections_on_canvas(), _draw_flowables_top_down(), _draw_spread_sections_on_canvas(), _flowables_height(), Insert flexible gaps between sidebar sections to fill available height., Spread sections vertically to fill the sidebar., Center languages + hobbies as one block; fixed gap between sections, equal…, _sidebar_frame_height() (+2 more)

### Community 65 - "Pmm Senior Ai Engineer"
Cohesion: 0.20
Nodes (10): Agentic AI frameworks and MCP, GenAI methods, Designing and deploying machine learning models, People Made Machines (PMM), Senior AI Engineer - People Made Machines, Agentic workflows and tool use, AI Innovation Lead - Tieto Banktech, AI governance in banking / regulatory context (+2 more)

### Community 66 - "Six Robotics Principal Ai"
Cohesion: 0.22
Nodes (10): On-prem LLM and GPU infrastructure, Principal AI Enablement Engineer, Six Robotics, Sovereign AI setup, UAV autonomy and swarm platforms, AI-assistert utvikling og agentic coding, Cursor, Claude Code, GitHub Copilot, AugmentCode, Java, Spring Boot, PostgreSQL, AWS/Heroku (+2 more)

### Community 67 - "Dashboard"
Cohesion: 0.20
Nodes (10): _dismiss_apply_modify_dialog(), _mark_dashboard_scroll_restore(), _on_apply_dialog_cancel_click(), _on_apply_dialog_close_click(), _on_apply_dialog_dismiss(), Request scroll restore on the next full dashboard render (e.g. after dialog…, Clear dialog flags immediately; optionally drop completed pipeline UI state.…, st.dialog X / Esc: drop dialog flags only (pipeline keeps running). (+2 more)

### Community 68 - "Job Filters"
Cohesion: 0.20
Nodes (10): _jobs_query_fragments(), AND (instr>0 OR ...) — require at least one tech token., SQL fragment: require CV keyword/skill overlap (exclude location/TEK-only…, SQL fragment: exclude rows whose title/description match PhD-student blocklist., SQL pre-filter on title/jobtitle/employer using strict role + university tokens., sql_exclude_fragments(), sql_phd_student_exclude(), sql_require_academic_role_display() (+2 more)

### Community 70 - "Run Demo"
Cohesion: 0.47
Nodes (9): assemble_run(), copy_seed_outputs(), ensure_demo_cv_dir(), main(), prepare_run(), print_walkthrough(), Path, render_pdf() (+1 more)

### Community 71 - "Readme"
Cohesion: 0.25
Nodes (9): Private CV Data Separation, Project Boundary, Anonymized Placeholders, Privacy-First Workflow, check_safe_to_push.py, Reveal CV, shared Module, Tailor in Public, Reveal in Private (+1 more)

### Community 72 - "Cv Source Sync"
Cohesion: 0.33
Nodes (8): enrich_body_from_front_matter(), full_cv_markdown(), _hobby_bullets(), _language_bullets(), Apply languages and hobbies from YAML front matter into markdown sections., Rebuild file text with front matter + enriched body for run sync., Replace bullet list under ## Section until the next ## heading., _replace_section_bullets()

### Community 73 - "Test Job Filters Relevance"
Cohesion: 0.31
Nodes (4): has_profile_relevance(), Any, True when a scored job has CV keyword/skill overlap. Location-only (+5) and…, ProfileRelevanceTests

### Community 74 - "Agent Interop"
Cohesion: 0.25
Nodes (8): agent_apply_job.sh, Future MCP Thin Wrapper, Provider: cursor, Provider: manual, Run Folder Contract, Cursor Token Metering Opacity, cv_generation Module, pypdf

### Community 75 - "Finn 467933786 Platform Engineer"
Cohesion: 0.25
Nodes (8): Retrieval-Augmented Generation (RAG), Vector Search, KI-Driven Ecosystem for Norwegian Export, Norwegian Energy Partners, Platform Engineer & AI-enabler, AI Engineer (Platform/Cloud), Norconsult Digital, RAG and Agent-Based Solutions

### Community 76 - "Dashboard"
Cohesion: 0.32
Nodes (5): application_status_upsert_row(), Normalize DB/pandas cell values to optional stripped text., Build ``upsert_application`` payload for a status change. Preserves notes,…, _sql_optional_text(), TestApplicationStatusUpsertRow

### Community 77 - "Test Academic Track Filter"
Cohesion: 0.29
Nodes (3): finn_search_queries_for_track(), FINN queries for ``industry``, ``academic``, or ``both`` (default ingest)., AcademicFinnQueryTests

### Community 78 - "Agent Interop"
Cohesion: 0.29
Nodes (7): agent_cli, Dashboard vs External Agents, Norwegian B1 Localization, job_search Module, Norway-First Locale Strategy, selectolax, streamlit

### Community 79 - "Cv Automation"
Cohesion: 0.29
Nodes (7): Iconify API Fetch, Lucide CV Sidebar Icons, Academic CV Track, Industry CV Track, track_selector Subagent, Demo Academic CV Source, track_selector Spec

### Community 80 - "Finn 465564641 Postdoctoral Research"
Cohesion: 0.33
Nodes (7): Ethics of Embodied AI, Norwegian Centre for Embodied AI (NCEI), NCEI Ethics Framework / Ethics Toolbox, Physical AI and Robot Morphology Co-design, Postdoctoral Research Fellow in Ethics of Embodied AI, University of Oslo, Robustness Ethics and Accountability in KI

### Community 81 - "Finn 468491746 Principal Architect"
Cohesion: 0.29
Nodes (7): AI-First SaaS Platform Architecture, Industrial Decarbonization via Software, LCA.no AS, Principal Architect SaaS Platform & AI, Product Carbon Footprint and LCA Software, Platform for AI-Generated and Project Applications, Security Observability and Monitoring

### Community 82 - "Finn 468693066 Data Scientist"
Cohesion: 0.29
Nodes (7): Center of Excellence for AI and Automation (Claims), Data Scientist (Gjensidige), Databricks and dbt Pipelines, Gjensidige, New AI Unit for Insurance Services, Fremtind, Senior Data Scientist (Fremtind)

### Community 83 - "Storebrand Senior Ai Platform"
Cohesion: 0.33
Nodes (7): Ansvarlig bruk av KI, Trustworthy and responsible AI, Bridge from prototyping to production (Dev → Prod), AI platforms and paved road for developers, Platform for responsible AI, Senior AI Platform Engineer - Storebrand, Storebrand

### Community 84 - "Privacy"
Cohesion: 0.33
Nodes (6): Deanonymize Privately, cv_identity_mapping.json, Deanonymized Output Folder, Private Identity Boundary, private_cv apply / local reveal, private_cv setup

### Community 85 - "Readme"
Cohesion: 0.40
Nodes (6): Northline Labs ML Engineer Job, ALEX RIVERA Demo Candidate, Northline ML Engineer Demo Run, scripts/run_demo.py, Demo Northline ML Engineer Job File, ALEX RIVERA Demo Candidate

### Community 86 - "Falkor Software Ai Engineer"
Cohesion: 0.40
Nodes (6): Digital Twins, Falkor (KONGSBERG), Industrial AI Software, MLOps, Software AI Engineer, MLOps for ML Lifecycle

### Community 87 - "Finn 465089104 Ml Ai"
Cohesion: 0.33
Nodes (6): LLM Inference Optimization, ML/AI Engineer, Targeting and Personalization, Piano Software Norway, RAG Pipelines, RAG and Generative AI for Claims

### Community 88 - "Finn 466330851 Associate Software"
Cohesion: 0.33
Nodes (6): Associate Software Engineer - Computer Vision & AI, NOV (National Oilwell Varco), Object Detection and Scene Perception, Monocular and Stereo Camera on GPU Linux, Vision AI Sensor Solutions, Computer Vision (Preferred Experience)

### Community 89 - "Finn 467762339 Postdoctoral Fellow"
Cohesion: 0.33
Nodes (6): Drought Stress Phenotyping, Field Digital Twins, Norwegian University of Life Sciences (NMBU), Postdoctoral Fellow AI-Driven Digital Phenotyping, SmartWheat Project, UAV Multispectral Hyperspectral RGB Imagery

### Community 90 - "Finn 468670212 Postdoctoral Research"
Cohesion: 0.33
Nodes (6): Geometric Deep Learning, Lie Størmer Center, Postdoctoral Research Fellow Mathematical Foundations of AI, Structure-Preserving Algorithms for ML, SURE-AI Project, UiT The Arctic University of Norway

### Community 91 - "Finn 469233460 Ki Ingeni"
Cohesion: 0.33
Nodes (6): Data-Centric Defense with AI as Force Multiplier, Forsvaret, Forsvarets Senter for Data og KI, KI-ingeniør Data Scientist (Prosjektstilling), MLOps and CI/CD for Operational AI, MLOps and Model Monitoring in Production

### Community 92 - "Finn 469415440 Data Scientist"
Cohesion: 0.33
Nodes (6): Data Lake / Lakehouse Analytics-Ready Data, Data Scientist - NORCE Analytics, Digital Twins (Project Domain), TensorFlow PyTorch scikit-learn, NORCE Research AS, NORCE Analytics Initiative

### Community 93 - "Ntnu Aid Postdoc Human"
Cohesion: 0.47
Nodes (6): AI for Decisions (AID) Center, Postdoctoral Fellow – AI for Decisions (AID), Human–AI collaboration for decision-making, Human-in-the-loop decision support, ISCHI research group, NTNU

### Community 94 - "Sanna Full Stack Ai"
Cohesion: 0.40
Nodes (6): Accounting automation platform, AI vs deterministic rules vs human-in-the-loop, Full-Stack (AI) Engineer - Sanna, Production LLMs and AI-driven workflows, Sanna, TypeScript, Effect.ts, PostgreSQL, SvelteKit

### Community 95 - "Pipeline Impact"
Cohesion: 0.33
Nodes (6): Energy Estimation Formula v1, Luccioni et al. 2023, Patterson et al. 2021, pipeline_metrics.json, run_agent_pipeline, run_cv_tailoring

### Community 96 - "Linkedin"
Cohesion: 0.40
Nodes (5): CV LinkedIn profile contact link, LinkedIn lowercase in wordmark logo, Rounded letter i with tittle dot, Rounded arched letter n, LinkedIn professional networking platform

### Community 97 - "Linkedin"
Cohesion: 0.40
Nodes (5): Connected contact figure paths, LinkedIn-style people network SVG icon, Small circle person head, Vertical torso bar for primary person, CV LinkedIn professional profile marker

### Community 98 - "Orcid"
Cohesion: 0.40
Nodes (5): Avatar circle for person face, ORCID ID badge SVG icon, Identity text line stubs on card, CV ORCID researcher ID profile link, Rounded rectangle card frame

### Community 99 - "Cv Photo Placeholder"
Cohesion: 0.40
Nodes (5): Circular light-gray frame around figure, CV header photo slot when no real photo, Default profile photo placeholder avatar, Abstract head circle shape, Abstract shoulders / torso oval

### Community 100 - "Cv Industry Source"
Cohesion: 0.40
Nodes (5): ALEX RIVERA, Demo Industry CV Source, Demo final_cv.md, Final CV ML ENGINEER Role, Demo tailored_cv.md

### Community 101 - "Import Cv Pdf"
Cohesion: 0.60
Nodes (4): extract_pdf_text(), main(), Path, sanitize_filename()

### Community 102 - "Finn 469070200 Data Engineer"
Cohesion: 0.40
Nodes (5): Data Engineer GEOMETOC (Etterretningstjenesten), Etterretningstjenesten, Automated Geographic Data Pipelines, GEOMETOC Geographic Meteorological Oceanographic Data, Geographic Information Systems (GIS)

### Community 103 - "Nav 117D8Fcd-B7F0-43Eb-B6Fd-78C929F6F227"
Cohesion: 0.40
Nodes (5): Cyber Security Engineer - Remota, Identitets- og tilgangsstyring, endepunktsbeskyttelse, ISO 27001 og NIS2, Remota AS, Remote Operations Center (ROC)

### Community 104 - "Nav 32825E09-0F94-4992-B5B6-27231Ec25522"
Cohesion: 0.40
Nodes (5): Samskaping av e-helseløsninger, Digital hjemmeoppfølging for skrøpelige eldre, Høgskulen på Vestlandet / Senter for omsorgsforskning vest, Postdoktor innen e-helse/tjenester, Forskningsgruppen Teknologi, helse og samfunn

### Community 105 - "English Writing Samples"
Cohesion: 0.40
Nodes (5): Academic application letter style, English connectors and flow, English cover letter voice, Norwegian B1 writing style, Norwegian B1 connectors

### Community 107 - "Repo Paths"
Cohesion: 0.40
Nodes (4): load_repo_dotenv(), Path, Repository layout paths (shared by job search and CV generation)., Load KEY=VALUE lines from repo .env into os.environ (does not override…

### Community 108 - "Check Safe To Push"
Cohesion: 0.70
Nodes (4): main(), Path, scan_file(), should_scan()

### Community 109 - "Cake"
Cohesion: 0.50
Nodes (4): Birthday cake CV icon (date of birth), Single-tier cake body with frosting wave, Three candles with flame dots, CV contact marker for date of birth

### Community 110 - "Cake"
Cohesion: 0.50
Nodes (4): Birthday cake SVG icon (date of birth), Rounded cake body with wavy frosting path, Light stroke line-art UI glyph on dark, Three candle sticks with flame dots

### Community 111 - "Email"
Cohesion: 0.50
Nodes (4): CV sidebar email address marker, Email envelope SVG contact icon, Diagonal flap path meeting at center, Rounded rectangle envelope body

### Community 112 - "Github"
Cohesion: 0.50
Nodes (4): Cat-like ears on Octocat outline, GitHub Octocat silhouette logo, CV GitHub profile / code portfolio link, GitHub version control platform brand

### Community 113 - "Github"
Cohesion: 0.50
Nodes (4): CV GitHub repository profile link marker, Head body tentacle stroke path, GitHub Octocat outline SVG icon, Curved tail appendage path

### Community 114 - "Google Scholar"
Cohesion: 0.50
Nodes (4): Google Scholar academic profile CV marker, Diamond-shaped mortarboard top, Graduation cap / mortarboard icon, Tassel hanging from cap corner

### Community 115 - "Google Scholar"
Cohesion: 0.50
Nodes (4): Open academic book / scholar SVG icon, Angled book cover layers, Google Scholar citations profile CV link, Curved page sides hanging below covers

### Community 116 - "Location"
Cohesion: 0.50
Nodes (4): CV geographic address / city contact marker, Inner circle eye of map pin, Map pin / location marker icon, Inverted teardrop pin body

### Community 117 - "Location"
Cohesion: 0.50
Nodes (4): Centered circle location dot, CV sidebar location / residence field marker, Map pin location SVG icon, Teardrop pin outline path

### Community 118 - "Mail"
Cohesion: 0.50
Nodes (4): CV email contact alternate glyph, Mail envelope SVG icon, Diagonal flap fold path, Rounded rectangle envelope body

### Community 119 - "Map-Pin"
Cohesion: 0.50
Nodes (4): Center circle geographic point, CV geographic location field glyph, Map-pin SVG location marker, Teardrop pin outline path

### Community 120 - "Orcid"
Cohesion: 0.50
Nodes (4): ORCID ID card / badge icon, Person head-and-shoulders silhouette, ORCID researcher persistent identifier link, Two horizontal text placeholder bars

### Community 121 - "Phone"
Cohesion: 0.50
Nodes (4): CV phone number contact marker, Earpiece end of handset, Telephone handset contact icon, Mouthpiece end of handset

### Community 122 - "Phone"
Cohesion: 0.50
Nodes (4): Call connection / dial UI metaphor, Phone call receiver SVG icon, Curved modern handset stroke, CV telephone contact field marker

### Community 123 - "Cv Automation"
Cohesion: 0.67
Nodes (4): jd_parser Subagent, keyword_ranker Subagent, jd_parser Spec, keyword_ranker Spec

### Community 124 - "Attensi Data Engineer"
Cohesion: 0.50
Nodes (4): Attensi Next-Gen Data Platform, Attensi Data Engineer, AI-Assisted Development Tools, AW Academy Data Engineer Program

### Community 125 - "Nav 31Fab261-775B-49Db-88Ff-920037F3D58F"
Cohesion: 0.50
Nodes (4): Bjerkreim kommune, Enhetsleder for IT og digitalisering, Google Workspace for Education, Microsoft 365 og Intune

### Community 126 - "Vipps Agentic Commerce Engineer"
Cohesion: 0.50
Nodes (4): Agentic Commerce, LLM-driven prototypes, Vipps shopping assistant, Vipps MobilePay

### Community 127 - "Forwardmedia Boston Context"
Cohesion: 0.50
Nodes (4): Democracy base, ForwardMedia Research Centre, Responsible media technology, University of Boston

### Community 128 - "Tritium Backend Context"
Cohesion: 0.50
Nodes (4): Azure and AWS deployment, MEAN stack, REST APIs and scalable backends, Tritium Consulting

### Community 129 - "Dashboard"
Cohesion: 0.50
Nodes (4): _copy_text_to_clipboard(), Copy ``text`` via browser clipboard API (runs in the app document)., Show a bash command with an adjacent Copy button., _render_copyable_bash_command()

### Community 130 - "Dashboard"
Cohesion: 0.50
Nodes (4): _open_pipeline_dialog(), Rebuild enough dialog state to reopen pipeline progress/results from the page., Reopen the existing Apply/Modify dialog for the active pipeline., _restore_pipeline_dialog_context()

### Community 131 - "Email"
Cohesion: 0.67
Nodes (3): CV email / messaging contact channel, Envelope flap V-fold lines, Email envelope CV contact icon

### Community 133 - "Job Detail Html Only"
Cohesion: 0.67
Nodes (3): Piano Software Norway ML/AI Engineer, FINN HTML-only job detail fixture, Piano Software Norway HTML fixture

### Community 134 - "Git And Privacy"
Cohesion: 0.67
Nodes (3): Pluggable agent providers, check_safe_to_push.py, Git-ready privacy plan

### Community 135 - "Dashboard Debug"
Cohesion: 0.67
Nodes (3): _hash_text(), Stable short hash for debug-visible cache keys and filters., short_fingerprint()

## Knowledge Gaps
- **215 isolated node(s):** `SubagentSpec`, `render_private_cv.example.sh script`, `PYTHONPATH`, `agent_apply_job.sh script`, `bulk_apply_deanonymize.sh script` (+210 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `load_default_profiles()` connect `Ingest Keyword Collect` to `Private CV Apply`, `Dashboard DB Loaders`, `Run Cv Tailoring`, `NAV Job Ingest`, `Agent Pipeline Runner`, `FINN Search Queries`, `Location Preferences`?**
  _High betweenness centrality (0.055) - this node is a cross-community bridge._
- **Why does `supplementary_artifact_filenames()` connect `Private CV Apply` to `Dashboard Job Export`, `Apply Pipeline Options`, `Application Artifacts`?**
  _High betweenness centrality (0.039) - this node is a cross-community bridge._
- **Why does `Row` connect `TEK Rogaland Fetch` to `Dashboard DB Loaders`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `main()` (e.g. with `connect()` and `init_schema()`) actually correct?**
  _`main()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `ApplyPipelineOptions` (e.g. with `FinnJobSession` and `TestApplicationStatusUpsertRow`) actually correct?**
  _`ApplyPipelineOptions` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `PrivateConfig` (e.g. with `TestResolveRunDir` and `TestPrivateCvDeanonOutput`) actually correct?**
  _`PrivateConfig` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `SubagentSpec`, `render_private_cv.example.sh script`, `PYTHONPATH` to the rest of the system?**
  _215 weakly-connected nodes found - possible documentation gaps or missing edges._