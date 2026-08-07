---
source_file: "cv_generation/cover_letter_generator.py"
type: "code"
community: "Cover Letter Generator"
location: "L1"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Cover_Letter_Generator
---

# cover_letter_generator.py

## Connections
- [[AgentRunResult]] - `imports` [EXTRACTED]
- [[CoverLetterResult]] - `contains` [EXTRACTED]
- [[PipelineMetricsCollector]] - `imports` [EXTRACTED]
- [[_call_cover_letter_agent()]] - `contains` [EXTRACTED]
- [[_looks_like_cover_letter()]] - `imports` [EXTRACTED]
- [[_render_plain_markdown_pdf()]] - `imports` [EXTRACTED]
- [[agent_contract.py]] - `imports_from` [EXTRACTED]
- [[agent_providers.py]] - `imports_from` [EXTRACTED]
- [[apply_prompts.py]] - `imports_from` [EXTRACTED]
- [[build_cover_letter_prompt()]] - `contains` [EXTRACTED]
- [[cover_letter_markdown_path()]] - `contains` [EXTRACTED]
- [[cv_application_artifacts.py]] - `imports_from` [EXTRACTED]
- [[cv_norwegian.py]] - `imports_from` [EXTRACTED]
- [[cv_style.py]] - `imports_from` [EXTRACTED]
- [[detect_supplementary_artifacts()]] - `imports` [EXTRACTED]
- [[generate_cover_letter_markdown()]] - `contains` [EXTRACTED]
- [[get_provider()]] - `imports` [EXTRACTED]
- [[is_cover_letter_required()]] - `contains` [EXTRACTED]
- [[load_json()]] - `imports` [EXTRACTED]
- [[looks_like_norwegian_cover_letter()]] - `imports` [EXTRACTED]
- [[manual_cover_letter_prompt_path()]] - `contains` [EXTRACTED]
- [[manual_cover_letter_response_path()]] - `contains` [EXTRACTED]
- [[maybe_generate_cover_letter()]] - `contains` [EXTRACTED]
- [[pipeline_metrics.py]] - `imports_from` [EXTRACTED]
- [[read_apply_prompts()]] - `imports` [EXTRACTED]
- [[read_job_posting()]] - `contains` [EXTRACTED]
- [[render_cover_letter_pdf()]] - `contains` [EXTRACTED]
- [[resolve_output_language()]] - `contains` [EXTRACTED]
- [[resolve_role_company()]] - `contains` [EXTRACTED]
- [[resolve_track()]] - `contains` [EXTRACTED]
- [[run_agent_pipeline.py]] - `imports_from` [EXTRACTED]
- [[strip_markdown_response()]] - `imports` [EXTRACTED]
- [[supplementary_generator.py]] - `imports_from` [EXTRACTED]
- [[test_cover_letter_generator.py]] - `imports_from` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Cover_Letter_Generator