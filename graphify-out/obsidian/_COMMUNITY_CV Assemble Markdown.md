---
type: community
members: 44
---

# CV Assemble Markdown

**Members:** 44 nodes

## Members
- [[dot-test_assemble_emits_no_institution_warnings_for_consistent_source()]] - code - cv_generation/tests/test_institution_validation.py
- [[dot-test_consistent_source_has_no_warnings()]] - code - cv_generation/tests/test_institution_validation.py
- [[dot-test_detects_bullet_tailor_employer_relabel()]] - code - cv_generation/tests/test_institution_validation.py
- [[dot-test_detects_phd_education_experience_mismatch_in_source()]] - code - cv_generation/tests/test_institution_validation.py
- [[dot-test_select_tailored_skills_caps_at_four()]] - code - cv_generation/tests/test_cv_tracks.py
- [[dot-test_select_tailored_skills_keeps_short_lists()]] - code - cv_generation/tests/test_cv_tracks.py
- [[Any_2]] - code
- [[Best-effort parse 'Company — Role bullet' lines from legacy bullet_tailor…]] - rationale - cv_generation/cv_assemble.py
- [[Cross-check degree institutions, experience employers, and teaching hosts.…]] - rationale - cv_generation/cv_assemble.py
- [[Detect track from markdown H1 (e.g. `` Industry CV``, `` Academic CV``).…]] - rationale - cv_generation/cv_tracks.py
- [[Enforce preservation rules and return canonical experience_roles for…]] - rationale - cv_generation/cv_assemble.py
- [[ExperienceItem]] - code - cv_generation/cv_pdf_renderer.py
- [[Headline under the name on the CVPDF (e.g. MLAI Engineer - MLAI ENGINEER).]] - rationale - cv_generation/cv_assemble.py
- [[Keep at most max_count skills, preferring terms that match ranked JD keywords.]] - rationale - cv_generation/cv_assemble.py
- [[Merge bullet_tailor output into the source CV. By default the source template…]] - rationale - cv_generation/cv_assemble.py
- [[Merge tailored bullets into source roles (same order as source). Never drop a…]] - rationale - cv_generation/cv_assemble.py
- [[TestInstitutionValidation]] - code - cv_generation/tests/test_institution_validation.py
- [[TestTailoredSkills]] - code - cv_generation/tests/test_cv_tracks.py
- [[Tests for institution cross-checks in CV assembly.]] - rationale - cv_generation/tests/test_institution_validation.py
- [[Track]] - code
- [[_coerce_bullets()]] - code - cv_generation/cv_assemble.py
- [[_collect_institution_names()]] - code - cv_generation/cv_assemble.py
- [[_degree_kind()]] - code - cv_generation/cv_assemble.py
- [[_education_institutions_by_degree()]] - code - cv_generation/cv_assemble.py
- [[_match_tailored_role()]] - code - cv_generation/cv_assemble.py
- [[_norm()]] - code - cv_generation/cv_assemble.py
- [[_parse_legacy_tailored_bullets()]] - code - cv_generation/cv_assemble.py
- [[_phd_experience_employer()]] - code - cv_generation/cv_assemble.py
- [[_skill_relevance_score()]] - code - cv_generation/cv_assemble.py
- [[_teaching_institution_suffix()]] - code - cv_generation/cv_assemble.py
- [[apply_bullet_tailor()]] - code - cv_generation/cv_assemble.py
- [[assemble_final_cv_markdown()]] - code - cv_generation/cv_assemble.py
- [[cv_assemble.py]] - code - cv_generation/cv_assemble.py
- [[cv_track_from_title()]] - code - cv_generation/cv_tracks.py
- [[designation_from_job_role()]] - code - cv_generation/cv_assemble.py
- [[experience_inventory()]] - code - cv_generation/run_agent_pipeline.py
- [[experience_role_key()]] - code - cv_generation/cv_assemble.py
- [[extract_experience_roles()]] - code - cv_generation/cv_assemble.py
- [[merge_experience_bullets()]] - code - cv_generation/cv_assemble.py
- [[normalize_bullet_tailor_output()]] - code - cv_generation/cv_assemble.py
- [[render_cv_markdown()]] - code - cv_generation/cv_assemble.py
- [[select_tailored_skills()]] - code - cv_generation/cv_assemble.py
- [[test_institution_validation.py]] - code - cv_generation/tests/test_institution_validation.py
- [[validate_institution_consistency()]] - code - cv_generation/cv_assemble.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/CV_Assemble_Markdown
SORT file.name ASC
```

## Connections to other communities
- 19 edges to [[_COMMUNITY_CV PDF Renderer]]
- 10 edges to [[_COMMUNITY_Agent Pipeline Runner]]
- 8 edges to [[_COMMUNITY_CV Style Profile Limits]]
- 6 edges to [[_COMMUNITY_PDF Layout Flowables]]
- 2 edges to [[_COMMUNITY_Test Agent Interop]]
- 2 edges to [[_COMMUNITY_Plain Markdown PDF]]
- 1 edge to [[_COMMUNITY_Agent Contract]]
- 1 edge to [[_COMMUNITY_CV Sidebar Layout]]

## Top bridge nodes
- [[cv_assemble.py]] - degree 38, connects to 6 communities
- [[assemble_final_cv_markdown()]] - degree 18, connects to 5 communities
- [[apply_bullet_tailor()]] - degree 11, connects to 3 communities
- [[ExperienceItem]] - degree 8, connects to 2 communities
- [[experience_inventory()]] - degree 5, connects to 2 communities