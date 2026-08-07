---
type: community
members: 23
---

# Deadline Urgency Utils

**Members:** 23 nodes

## Members
- [[dot-test_days_until_and_apply_soon()]] - code - job_search/tests/test_deadline_utils.py
- [[dot-test_parse_dotted_date()]] - code - job_search/tests/test_deadline_utils.py
- [[dot-test_parse_iso_date()]] - code - job_search/tests/test_deadline_utils.py
- [[dot-test_parse_norwegian_month_name()]] - code - job_search/tests/test_deadline_utils.py
- [[dot-test_place_garbage_deadline()]] - code - job_search/tests/test_deadline_utils.py
- [[dot-test_unknown_deadline()]] - code - job_search/tests/test_deadline_utils.py
- [[Days from today until deadline (0 = today). None if unknown or past parsing.]] - rationale - job_search/deadline_utils.py
- [[DeadlineUtilsTests]] - code - job_search/tests/test_deadline_utils.py
- [[Parse ISO or Norwegian deadline text into a calendar date.]] - rationale - job_search/deadline_utils.py
- [[Parse job application deadlines and compute urgency.]] - rationale - job_search/deadline_utils.py
- [[Return urgency badge text or empty string.]] - rationale - job_search/deadline_utils.py
- [[Tests for deadline_utils.]] - rationale - job_search/tests/test_deadline_utils.py
- [[True when deadline is today or within the next ``within_days`` days.]] - rationale - job_search/deadline_utils.py
- [[_normalize_year()]] - code - job_search/deadline_utils.py
- [[_safe_date()]] - code - job_search/deadline_utils.py
- [[apply_soon_badge()]] - code - job_search/deadline_utils.py
- [[date]] - code
- [[days_until_deadline()]] - code - job_search/deadline_utils.py
- [[deadline_utils.py]] - code - job_search/deadline_utils.py
- [[is_apply_soon()]] - code - job_search/deadline_utils.py
- [[parse_deadline()]] - code - job_search/deadline_utils.py
- [[reference_today()]] - code - job_search/deadline_utils.py
- [[test_deadline_utils.py]] - code - job_search/tests/test_deadline_utils.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Deadline_Urgency_Utils
SORT file.name ASC
```

## Connections to other communities
- 11 edges to [[_COMMUNITY_Dashboard Job Export]]
- 5 edges to [[_COMMUNITY_FINN Search Queries]]
- 1 edge to [[_COMMUNITY_Dashboard DB Loaders]]
- 1 edge to [[_COMMUNITY_NAV Job Ingest]]

## Top bridge nodes
- [[deadline_utils.py]] - degree 15, connects to 3 communities
- [[parse_deadline()]] - degree 12, connects to 2 communities
- [[test_deadline_utils.py]] - degree 9, connects to 2 communities
- [[is_apply_soon()]] - degree 8, connects to 2 communities
- [[dot-test_place_garbage_deadline()]] - degree 3, connects to 2 communities