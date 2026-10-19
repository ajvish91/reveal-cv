# Pipeline environmental impact (approximate)

Each CV application run can write **`pipeline_metrics.json`** into
`cv_generation/cv_runs/<run_id>/` when `run_agent_pipeline` completes (not on
`--dry-run`).

This is a **v1 honesty-first** estimate: measured wall time where possible,
API token counts when providers expose them, char-based token guesses otherwise,
and a very rough kWh / CO₂ extrapolation. **Not suitable for carbon accounting.**

## What is measured vs estimated

| Metric | Status | Source |
|--------|--------|--------|
| Wall-clock time (total + per stage) | **Measured** | `time.monotonic()` in `run_agent_pipeline` / localization |
| API tokens (input/output) | **Measured** (Anthropic, OpenAI) | Response `usage` metadata in `agent_providers.py` |
| API tokens (Cursor default) | **Not exposed** | Cursor SDK `RunResult` has `duration_ms` only via `Agent.prompt()` |
| API tokens (Cursor, fallback) | **Estimated** | `(len(prompt) + len(response)) / 4` chars-per-token heuristic |
| API tokens (manual provider) | **None** | Human/agent outside repo; no metering |
| Local process memory (peak RSS) | **Measured** (approx.) | Stdlib `resource.getrusage` on the Python runner only |
| Remote datacenter memory / GPU | **Not measured** | Opaque for Cursor cloud/local agents |
| Energy (kWh) | **Estimated** | Token-based formula (see below) |
| CO₂ (kg) | **Estimated** | kWh × global-average grid factor |

## Output file

`pipeline_metrics.json` includes:

- `started_at`, `ended_at`, `duration_sec`
- `stages[]` — one entry per agent step, assembler (deterministic), and optional Norwegian localization
- `totals.tokens_*` and `totals.tokens_source`: `measured_api`, `estimated_chars`, or `none`
- `process.peak_rss_mb` — runner process only
- `energy_estimate` — kWh / CO₂ with disclaimer

## Energy estimation formula (v1)

When token totals are available (measured or char-estimated):

```
tokens_total = tokens_input + tokens_output
kWh ≈ (tokens_total / 1000) × 0.0005
CO₂_kg ≈ kWh × 0.4
```

Constants (documented in JSON under `energy_estimate.constants`):

- **0.0005 kWh per 1k tokens** — mid-range order-of-magnitude for cloud GPU
  **inference** (not training). Real values vary widely by model size, batching,
  hardware, and datacenter PUE. Inspired by ballpark figures discussed in
  Patterson et al. (*Carbon Emissions and Large Neural Network Training*, 2021)
  and Luccioni et al. (*Estimating the Carbon Footprint of BLOOM*, 2023); this
  repo uses a single simplified factor, not model-specific life-cycle analysis.
- **0.4 kg CO₂ per kWh** — very rough global-average grid intensity; actual
  datacenter regions differ (e.g. hydro-heavy Norway vs coal-heavy grids).

**Caveats:**

- Cursor agents may run many internal tool calls; char-based estimates count
  only the final prompt/response strings passed through this pipeline.
- PDF rendering, SQLite export, and dashboard subprocess overhead are included
  in wall time but not in token-based energy.
- Cover letters and supplementary docs created manually in the IDE are **not**
  included unless they go through `run_agent_pipeline` / localization.

## Provider notes

| Provider | Tokens | Duration | Notes |
|----------|--------|----------|-------|
| **anthropic** | API usage | Per-step wall time | Best metering in-repo |
| **openai** | API usage | Per-step wall time | Best metering in-repo |
| **cursor** | Char estimate | `duration_ms` on result + wall time | Default dashboard Apply provider |
| **manual** | None | Wall time if re-run in pipeline | External agent opaque |

## Dashboard integration

After Apply completes, the status line may show:

`Pipeline: 4m 12s · ~42k tokens · est. 0.02 kWh (approx.)`

Applied roles → expand a row → same line under the CV run id when
`pipeline_metrics.json` exists.

No SQLite column in v1; metrics live in the run folder.

## CLI

Metrics are written automatically at the end of:

```bash
.venv/bin/python -m cv_generation.run_agent_pipeline --run-dir "cv_generation/cv_runs/<run_id>"
```

Inspect:

```bash
cat cv_generation/cv_runs/<run_id>/pipeline_metrics.json
```

## Future improvements (not implemented)

- Cursor SDK streaming / `turn-ended` usage events if exposed on batch `prompt()`
- Optional `psutil` for finer local memory (avoided in v1 — stdlib only)
- Model-specific energy factors
- Aggregate rollup across applications in dashboard metrics

See also `AGENT_INTEROP.md` → Dashboard vs external agents.
