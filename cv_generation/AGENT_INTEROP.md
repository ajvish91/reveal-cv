# Agent Interoperability

The CV pipeline is designed around a provider-neutral run-folder contract so it
can work with Cursor, Claude, OpenAI, and manual copy/paste workflows.

## Core idea

The run folder is the API boundary.

- `run_cv_tailoring.py` prepares a run folder with source inputs and per-step task files.
- An agent backend reads `*_task.json` and writes `*_output.json`.
- Deterministic Python code assembles `final_cv.md` and renders PDF output.

This keeps the CV structure stable even when the agent runtime changes.

## Contract files

Every run directory contains:

- `agent_contract.json` - versioned contract metadata
- `job_posting.txt` - raw job text
- `subagent_specs.md` - human-readable step overview
- `application_artifacts.md` - supplementary document requirements
- `cv_industry_source.md` and `cv_academic_source.md` - source templates
- `01_*_task.json` through `06_*_task.json` - machine-readable step contracts
- `01_*_output.json` through `06_*_output.json` - step outputs

## Step order

1. `01_jd_parser_task.json`
2. `02_keyword_ranker_task.json`
3. `03_track_selector_task.json`
4. `04_bullet_tailor_task.json`
5. `05_ats_checker_task.json`
6. `06_assembler_task.json`

Step 6 is deterministic in practice: the final markdown is assembled in Python,
and the agent output is metadata/validation only.

## Response rules

Each agent step must return a strict JSON object.

- No prose
- No markdown
- No code fences
- Include all required top-level keys from `expected_output_schema`

## Generic CLI

Use the provider-neutral CLI:

```bash
.venv/bin/python -m cv_generation.agent_cli show-contract
.venv/bin/python -m cv_generation.agent_cli prepare-run --job-file "cv_generation/jobs/example.txt" --company "Acme" --role "ML Engineer"
.venv/bin/python -m cv_generation.agent_cli build-step-prompt --run-dir "cv_generation/cv_runs/<run_id>" --step 01_jd_parser_output.json
.venv/bin/python -m cv_generation.agent_cli validate-step-output --run-dir "cv_generation/cv_runs/<run_id>" --step 01_jd_parser_output.json --input "response.json"
.venv/bin/python -m cv_generation.agent_cli run-step --run-dir "cv_generation/cv_runs/<run_id>" --step 01_jd_parser_output.json --provider anthropic
.venv/bin/python -m cv_generation.agent_cli run-pipeline --run-dir "cv_generation/cv_runs/<run_id>" --provider openai
```

## Manual bridge workflow

Manual mode is the generic bridge for external agent UIs.

```bash
.venv/bin/python -m cv_generation.agent_cli run-step \
  --run-dir "cv_generation/cv_runs/<run_id>" \
  --step 01_jd_parser_output.json \
  --provider manual
```

This writes:

- `<step>_prompt.txt`
- `<step>_output.manual.json` (expected response path)

Workflow:

1. Open the prompt file.
2. Paste it into Claude Desktop, Codex, or another agent.
3. Save the strict JSON reply into the matching `*_output.manual.json`.
4. Re-run the command or continue with `run-pipeline --provider manual`.

## Providers

Built-in providers today:

- `cursor`
- `anthropic`
- `openai`
- `manual`

These are transport adapters. The run-folder contract is the stable interface.

## Compatibility note

`python -m cv_generation.generate_cv_with_cursor` still works, but it is now a
compatibility alias for the generic runner:

```bash
.venv/bin/python -m cv_generation.run_agent_pipeline --run-dir "cv_generation/cv_runs/<run_id>" --provider anthropic
```

## Future MCP direction

If an MCP server is added later, it should remain a thin wrapper over the same
contract and CLI operations:

- `prepare_run`
- `get_step_prompt`
- `submit_step_output`
- `validate_step_output`
- `assemble_run`

MCP should be an optional transport, not the core architecture.

## Dashboard vs external agents

The Streamlit dashboard (`job_search/dashboard.py`) is a **human UI**, not an agent
API. External agents (Claude Desktop, Codex, custom MCP wrappers) do **not** drive
the dashboard directly.

| Layer | What it does | Agent-accessible? |
|-------|----------------|-------------------|
| Dashboard Apply | Export job from SQLite → `run_cv_tailoring` → `run_agent_pipeline` (default provider: **cursor**) | No (UI only) |
| `run_agent_pipeline` | Full pipeline with `--provider anthropic\|openai\|cursor\|manual` | Yes (CLI) |
| `agent_cli` | Step-by-step contract ops (`prepare-run`, `build-step-prompt`, `run-step`, …) | Yes (CLI) |
| Run folder (`*_task.json`, `*_output.json`) | Stable file-based contract | Yes (read/write files) |
| SQLite `data/jobs.sqlite` | Job ingest + application tracking | Yes (parallel to dashboard) |

The dashboard and external agents can **share the same database and run folders**
without conflict. Typical split:

- **Dashboard:** browse/score jobs, click Apply, track `drafted` applications.
- **Claude / headless:** save or export a job `.txt`, run `scripts/agent_apply_job.sh`
  or `agent_cli` with `--provider anthropic` or `--provider manual`.

### Headless workflow (Claude or any external agent)

From repo root, with a saved job posting:

```bash
scripts/agent_apply_job.sh \
  --job-file "cv_generation/jobs/acme_ml_engineer.txt" \
  --company "Acme" \
  --role "ML Engineer" \
  --provider anthropic
```

Equivalent manual steps: `agent_cli prepare-run` then `run_agent_pipeline` (or `agent_cli run-pipeline`).

Or step-by-step with manual bridge (paste prompts into Claude Desktop):

```bash
.venv/bin/python -m cv_generation.agent_cli prepare-run \
  --job-file "cv_generation/jobs/acme_ml_engineer.txt" \
  --company "Acme" --role "ML Engineer"

RUN="cv_generation/cv_runs/<run_id>"

# For each step 01 … 05:
.venv/bin/python -m cv_generation.agent_cli run-step \
  --run-dir "$RUN" --step 01_jd_parser_output.json --provider manual
# → open 01_jd_parser_prompt.txt in Claude, save JSON to 01_jd_parser_output.manual.json, re-run

.venv/bin/python -m cv_generation.agent_cli run-pipeline \
  --run-dir "$RUN" --provider manual --no-pdf
```

Step 6 (`assembler`) is deterministic Python; no LLM call is required.

### Compatibility assessment

| Question | Answer |
|----------|--------|
| Can Claude run the full pipeline without Cursor? | **Yes** — `--provider anthropic` or `--provider manual` |
| Does the pipeline require Cursor-specific APIs? | **No** — Cursor is the default provider only |
| Can an external agent skip the dashboard? | **Yes** — job `.txt` + CLI is sufficient |
| Is there an in-repo MCP server? | **No** — future thin wrapper over `agent_cli` (see above) |
| Does the dashboard support choosing provider? | **Not yet** — Apply always uses default (`cursor`); use CLI for other providers |

**Overall:** **partial** for dashboard-driven Apply (Cursor-default, subprocess-only),
**yes** for headless/agent-portable workflows via run-folder contract and CLI.

### Job ingest without dashboard

1. Save posting text to `cv_generation/jobs/<slug>.txt`, or export from SQLite
   (dashboard writes `cv_generation/jobs/{nav\|finn}_{uuid}_{slug}.txt` on Apply).
2. Run `scripts/agent_apply_job.sh` or `agent_cli prepare-run` + `run-pipeline`.
3. Optionally upsert `applications` in SQLite manually; the dashboard will show
   runs referenced in `app_notes` if you log them yourself.

See also `job_search/JOB_SEARCH.md` → Apply flow for the dashboard-side equivalent.

## Pipeline impact metrics

After `run_agent_pipeline` completes, see `pipeline_metrics.json` in the run
folder and **`PIPELINE_IMPACT.md`** for what is measured vs estimated (wall
time, API tokens, rough kWh / CO₂, Cursor opacity).
