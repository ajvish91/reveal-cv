---
type: community
members: 16
---

# CV Style Profile Limits

**Members:** 16 nodes

## Members
- [[dot-test_assemble_trims_long_source_profile()]] - code - cv_generation/tests/test_cv_pdf_layout.py
- [[dot-test_normalize_profile_paragraphs_caps_count_and_chars()]] - code - cv_generation/tests/test_cv_pdf_layout.py
- [[dot-test_normalize_summary_bullets_caps_length()]] - code - cv_generation/tests/test_cv_pdf_layout.py
- [[Enforce Profile length for PDF layout. Returns (trimmed paragraphs, warnings).]] - rationale - cv_generation/cv_style.py
- [[Enforce academic Summary bullet count and length.]] - rationale - cv_generation/cv_style.py
- [[PDF layout sidebar continuation pages and profile length limits.]] - rationale - cv_generation/tests/test_cv_pdf_layout.py
- [[Shared CV tailoring style rules for agents and run scaffolding. See…]] - rationale - cv_generation/cv_style.py
- [[TestProfileLengthLimits]] - code - cv_generation/tests/test_cv_pdf_layout.py
- [[Trim Profile  Summary so PDF main column stays within a practical page budget.]] - rationale - cv_generation/cv_assemble.py
- [[Trim to max_chars, preferring a word boundary and a closing period.]] - rationale - cv_generation/cv_style.py
- [[_apply_profile_length_limits()]] - code - cv_generation/cv_assemble.py
- [[_truncate_at_word_boundary()]] - code - cv_generation/cv_style.py
- [[cv_style.py]] - code - cv_generation/cv_style.py
- [[normalize_profile_paragraphs()]] - code - cv_generation/cv_style.py
- [[normalize_summary_bullets()]] - code - cv_generation/cv_style.py
- [[test_cv_pdf_layout.py]] - code - cv_generation/tests/test_cv_pdf_layout.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/CV_Style_Profile_Limits
SORT file.name ASC
```

## Connections to other communities
- 8 edges to [[_COMMUNITY_CV Assemble Markdown]]
- 5 edges to [[_COMMUNITY_CV PDF Renderer]]
- 3 edges to [[_COMMUNITY_PDF Layout Flowables]]
- 3 edges to [[_COMMUNITY_CV Sidebar Layout]]
- 2 edges to [[_COMMUNITY_Norwegian CV Localization]]
- 2 edges to [[_COMMUNITY_Run Cv Tailoring]]
- 1 edge to [[_COMMUNITY_Cover Letter Generator]]
- 1 edge to [[_COMMUNITY_Supplementary Generator]]

## Top bridge nodes
- [[cv_style.py]] - degree 12, connects to 5 communities
- [[test_cv_pdf_layout.py]] - degree 12, connects to 3 communities
- [[normalize_profile_paragraphs()]] - degree 9, connects to 3 communities
- [[normalize_summary_bullets()]] - degree 9, connects to 3 communities
- [[_apply_profile_length_limits()]] - degree 6, connects to 2 communities