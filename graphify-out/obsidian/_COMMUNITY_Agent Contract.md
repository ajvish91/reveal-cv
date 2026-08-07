---
type: community
members: 10
---

# Agent Contract

**Members:** 10 nodes

## Members
- [[Any]] - code
- [[Path_1]] - code
- [[Tests for the agent-portable CV pipeline surface.]] - rationale - cv_generation/tests/test_agent_interop.py
- [[agent_contract.py]] - code - cv_generation/agent_contract.py
- [[manual_prompt_path()]] - code - cv_generation/agent_contract.py
- [[manual_response_path()]] - code - cv_generation/agent_contract.py
- [[required_top_level_keys()]] - code - cv_generation/agent_contract.py
- [[test_agent_interop.py]] - code - cv_generation/tests/test_agent_interop.py
- [[validate_output_against_task()]] - code - cv_generation/agent_contract.py
- [[write_json()]] - code - cv_generation/agent_contract.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Agent_Contract
SORT file.name ASC
```

## Connections to other communities
- 14 edges to [[_COMMUNITY_Agent Pipeline Runner]]
- 10 edges to [[_COMMUNITY_Agent Cli]]
- 7 edges to [[_COMMUNITY_Agent Providers]]
- 7 edges to [[_COMMUNITY_Test Agent Interop]]
- 6 edges to [[_COMMUNITY_Run Cv Tailoring]]
- 3 edges to [[_COMMUNITY_Apply Prompts Config]]
- 1 edge to [[_COMMUNITY_Cover Letter Generator]]
- 1 edge to [[_COMMUNITY_CV Assemble Markdown]]

## Top bridge nodes
- [[agent_contract.py]] - degree 17, connects to 6 communities
- [[test_agent_interop.py]] - degree 16, connects to 5 communities
- [[validate_output_against_task()]] - degree 9, connects to 3 communities
- [[manual_response_path()]] - degree 9, connects to 3 communities
- [[manual_prompt_path()]] - degree 8, connects to 3 communities