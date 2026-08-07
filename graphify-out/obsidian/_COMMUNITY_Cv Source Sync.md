---
type: community
members: 9
---

# Cv Source Sync

**Members:** 9 nodes

## Members
- [[Apply languages and hobbies from YAML front matter into markdown sections.]] - rationale - cv_generation/cv_source_sync.py
- [[Rebuild file text with front matter + enriched body for run sync.]] - rationale - cv_generation/cv_source_sync.py
- [[Replace bullet list under  Section until the next  heading.]] - rationale - cv_generation/cv_source_sync.py
- [[_hobby_bullets()]] - code - cv_generation/cv_source_sync.py
- [[_language_bullets()]] - code - cv_generation/cv_source_sync.py
- [[_replace_section_bullets()]] - code - cv_generation/cv_source_sync.py
- [[cv_source_sync.py]] - code - cv_generation/cv_source_sync.py
- [[enrich_body_from_front_matter()]] - code - cv_generation/cv_source_sync.py
- [[full_cv_markdown()]] - code - cv_generation/cv_source_sync.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Cv_Source_Sync
SORT file.name ASC
```

## Connections to other communities
- 3 edges to [[_COMMUNITY_Agent Pipeline Runner]]

## Top bridge nodes
- [[cv_source_sync.py]] - degree 6, connects to 1 community
- [[full_cv_markdown()]] - degree 5, connects to 1 community