# Feature inventory — Reveal CV

Snapshot: **2026-10-13**. Python ≥3.10. Package name in `pyproject.toml`: `job-search-automation`. Public-facing name: **Reveal CV**.

Two products share one repo:

1. **Job search** — ingest Norwegian listings, score against CV profiles, browse in a local dashboard, start an Apply pipeline.
2. **CV generation** — tailor an anonymized markdown CV (and letters) for a saved posting, then **reveal** identity only on the user’s machine.

---

## 1. Privacy and identity boundary

| Feature | Where |
|---------|--------|
| Anonymized placeholders in-repo (`MITCH EVANS`, fictional employers, `cv-placeholder` URLs) | `shared/cv/*.demo.md`, generated `cv_runs/` |
| Real name/email/photo/mapping **outside git** | `~/private/cv/` (agents must not read) |
| Example mapping keys only | `cv_generation/cv_identity_mapping.example.json` |
| Private CLI: setup, edit, sync, apply, localize, pdf, audit, recover sources | `python -m cv_generation.private_cv` |
| Shortcut `~/private/cv/cv` | created by `private_cv setup` |
| Deanonymize markdown + PDF for a run | `private_cv apply <run_id>` (`--strict` leftover placeholders skip PDF) |
| Bulk apply | `private_cv apply id1 id2` or `scripts/bulk_apply_deanonymize.sh` |
| Git leak scanner | `scripts/check_safe_to_push.py` + optional `.privacy_patterns.local` |
| Gitignore of runs, jobs, sqlite, PDFs, real CVs, graphify-out | `.gitignore` |
| Agent rules: stay in repo | `AGENTS.md`, `.cursor/rules/project-boundary.mdc` |

CV load order (`shared/cv_loader.py`): `CV_SOURCE_DIR` → `~/private/cv/cv/` → gitignored `shared/cv/industry.md` / `academic.md` → committed `*.demo.md`. Dashboard registry (`shared/cv/cv_registry.json`, gitignored) can point each track at a saved user CV under `shared/cv/user/`.

---

## 2. Job discovery (ingest)

Phases: **ingest → score → dashboard**. Daily wrapper: `scripts/run_job_search_cycle.py`.

### Sources

| Source key | Module | Mechanism |
|------------|--------|-----------|
| `nav_arbeidsplassen` | `ingest_nav_jobs.py` + `nav_feed_client.py` | Official NAV PAM feed (JWT). Incremental `If-Modified-Since`. Feed state in SQLite. **Stale-marking off by default** (`--mark-stale` for full backfills only). |
| `finn_no` | `ingest_finn_jobs.py` + `finn_job_client.py` | Search scrape + JSON-LD / HTML detail. Multiple queries. Pace 1–2s. Max detail pages capped. Stale-mark after complete crawl. |
| `jobbnorge` | `ingest_jobbnorge_jobs.py` + `jobbnorge_client.py` | Public catalog API + PDF text for details. `--search-track academic`. Uncommitted as of this snapshot. |

HTTP helpers: `job_search/http_utils.py`. Shared ingest gates: `ingest_common.py`, `ingest_keywords.py`.

### Keep / drop gates (defaults for daily ingest)

- `--keyword-filter` on: CV keywords + skills (`--keyword-source keywords-and-skills`)
- `--require-tech`: ICT allowlist in `job_filters.py` (`DEFAULT_TECH_INCLUDE_TERMS`)
- `--exclude-noise`: blocklist (salons, etc.)
- Location does **not** keep an ad by itself
- Application-history keyword boosts (`role_search_config.py`) used for FINN **search queries** and demo-CV gates, not for keeping real-profile ads unless `--application-boosts`
- Bare `utvikler` / `utvikling` are not tech hits; compounds like `systemutvikler` are

Inspect keywords: `ingest_nav_jobs --list-keywords` (same for FINN).

### FINN extras

- Query lists: `finn_search_queries.py` re-exports `role_search_config.py` (`--search-track both|industry|academic`)
- Deadlines: `finn_deadlines.py`, `refresh_finn_deadlines.py` (`--mark-known-only` preferred; avoid large HTTP backfills)
- Opening a job in the UI does **not** refetch FINN

### TEK Rogaland

- `fetch_tek_rogaland_members.py` → CSV used as optional **score boost**, not an ingest keep-gate

### SQLite

- `job_search/job_db.py` — schema, upsert, ingest_state, applications
- Default DB: `job_search/data/jobs.sqlite` (gitignored). Override `--db` or `JOBS_DB`

### Dedup

- `job_dedup.py`: employer+title key; winner = highest `score_total` (NAV wins ties); dashboard default shows one row with `Sources` column

### Logging

- `logging_config.py` — `job_search/data/job_search.log`, rotate ~2MB × 3. `JOB_SEARCH_LOG_LEVEL=DEBUG`

### Noise audit and preferences

- `audit_noisy_jobs.py` — zero-score / blocklist / weak-hit counts; optional `--mark-blocklist-inactive`
- `preference_collect.py` + `audit_preferences.py` — Skip/Reject labels → `job_search/data/preference_features*.json` (no score changes yet)

---

## 3. Scoring

`python -m job_search.score_jobs` (`--track industry|academic|both`)

- Two tracks share the ingested pool; scores stored per track
- `score_base` = count of distinct **strong** keyword/skill hits (word-boundary; short tokens like `ai`/`go` need tech context)
- `score_total` = hits + optional TEK / academic boosts
- Geographic boost is **always 0**; preferred locations (`location_preferences.py` + CV `locations_preferred`) are **filter/label only** (Rogaland-oriented UI)
- Profiles from `shared/cv_loader.py`

---

## 4. Dashboard (local web app)

`python -m job_search.webapp` → http://127.0.0.1:8765  
Stack: FastAPI + Bootstrap + `job_search/web/static/` (`index.html`, `cv.html`, `js/app.js`, `js/cv.js`)

Console script: `job-dashboard`.

### Pages

- `/` job explorer
- `/cv` anonymized CV editor (fake vs real fields; download mapping JSON; activate source per track)

### Explorer features

- Compact metrics: active jobs, apply soon, Rogaland matches, applications
- Collapsible: more stats, relevant (top by score), newest, Rogaland + profile match, applied roles
- Paginated explorer; hide applied/skipped; hide expired deadlines (unknown `expires` stay visible)
- Filters: source, dedup, PhD-student hide, academic-roles-only, apply-soon window, ICT allowlist, noise blocklist, preferred locations, sort (score / newest / location)
- Navbar CV track: industry vs academic
- Job actions (More): pin, mark applied/interested, skip, reject, withdraw, clear tracking
- Apply soon badge from `deadline_utils.py`
- Open job URL or offline posting text
- Sticky status bar for ingest + Apply pipeline
- Filters log tail (`/api/log`)

### Ingest from UI

- **Ingest & score** runs `scripts/run_job_search_cycle.py`
- Skip NAV / FINN / Jobbnorge; academic search only
- SSE/status: `/api/ingest`, `/api/ingest/stream`
- Disabled while Apply pipeline or another ingest is running

### Apply / Modify drawer

1. Export posting → `cv_generation/jobs/{source}_{uuid}_{slug}.txt`
2. `run_cv_tailoring` (optional `apply_prompts.txt`)
3. `run_agent_pipeline` with document flags
4. Upsert `applications` status **`drafted`** + run folder in notes

Fields: EN/NO language, custom prompts, checkboxes (cover letter / application letter / research proposal), overwrite on Modify, notes. Stages streamed via `/api/pipeline` and `/api/pipeline/stream`.

### Applied roles

- Status badges, Modify/Delete, bulk deanonymize command when multiple drafted runs exist
- `/api/deanonymize-link` helper text for `~/private/cv/cv apply <run_id>`

### CV page APIs

`/api/cv/sources`, `/blank`, `/document`, `/preview`, POST save, `/activate`, `/save-mapping` (mapping download; real values not stored for the AI)

### Other APIs

Health, meta, overview, jobs list/detail, apply-defaults, applications CRUD, job actions.

Runtime locking: `job_search/web/runtime.py`. Business logic: `web/services.py`. Periodic UI refresh: `dashboard_refresh.py`.

---

## 5. CV tailoring pipeline

### Prepare a run

`python -m cv_generation.run_cv_tailoring --job-file … [--company] [--role]`  
Naming: `run_naming.py` → `cv_runs/<UTC>_<CompanySlug>_<role-slug>/`

Run folder contract (`agent_contract.py`, `AGENT_INTEROP.md`):

- `job_posting.txt`, `agent_contract.json`, `subagent_specs.md`, `application_artifacts.md`
- `cv_industry_source.md`, `cv_academic_source.md` (snapshots; `cv_source_sync.py`)
- Steps 01–06 `*_task.json` / `*_output.json`
- Optional `apply_prompts.txt` (`apply_prompts.py`)

### Subagents (`cv_subagents.py`)

| Step | Role | LLM? |
|------|------|------|
| 01 jd_parser | Extract role needs | Yes |
| 02 keyword_ranker | Rank must-haves vs CV | **No** (Python) |
| 03 track_selector | industry vs academic | Yes |
| 04 bullet_tailor | Rewrite bullets truthfully | Yes |
| 05 ats_checker | Coverage / parseability | Yes |
| 06 assembler | Merge into markdown | **No** (`cv_assemble.py`) |

Preservation: keep every source role and bullet count (unless `--allow-fewer-bullets`); non-experience sections copied; industry `## Role` from JD title; academic omits Role section.

### Run all steps

`python -m cv_generation.run_agent_pipeline --run-dir … --provider cursor|anthropic|openai|manual`

- Alias: `generate_cv_with_cursor`
- Flags: `--overwrite`, `--refresh-tasks`, `--allow-fewer-bullets`, `--model`, `--dry-run`, `--pdf`, `--render-only`, `--profile-photo`
- Generic CLI: `python -m cv_generation.agent_cli` (show-contract, prepare-run, build-step-prompt, validate-step-output, run-step, run-pipeline)
- Manual provider writes `*_prompt.txt` + `*_output.manual.json` for paste into other UIs
- Providers: `agent_providers.py`

### Supplementary documents (`cv_application_artifacts.py`)

Detected from posting + track:

| File | Typical use |
|------|-------------|
| `cover_letter.md` | Industry |
| `application_letter.md` | Academic motivation |
| `research_proposal.md` | Postdoc/researcher plan |
| `reference_projects.md` | Extra |
| `recruiter_outreach.md` | Extra |

Generators: `cover_letter_generator.py` (industry; optional `cover_letter_no.md`), `supplementary_generator.py` (academic letter + proposal). Dashboard checkboxes map to `--generate-*` / `--overwrite-*`.

Voice/style: `cv_style.py` (`COVER_LETTER_VOICE`, chronology, 4-skill sidebar, no Profile keyword walls). Cursor rule: `.cursor/rules/cv-tailoring-style.mdc`.

### Norwegian localization

`cv_norwegian.py` + `private_cv localize`. Pairs: `final_cv_no.md`, `cover_letter_no.md`, `reference_projects_no.md`. Writing samples under `cv_generation/reference/`.

### PDF

- Styled CV: `cv_pdf_renderer.py` / `render_cv_pdf.py` (sidebar by track, inline `**bold**`/`*italic*` in Profile + bullets)
- Plain letters: `plain_markdown_pdf.py`
- ATS-ish PDF check: `ats_check_pdf.py`
- Import existing PDF to markdown: `import_cv_pdf.py`
- Strict leftover-placeholder gate: `private_cv pdf` / apply `--strict`

### Metrics

`pipeline_metrics.py` → `pipeline_metrics.json` (wall time, token usage when exposed, rough kWh/CO₂). See `PIPELINE_IMPACT.md`.

### Tracks

`cv_tracks.py` — industry vs academic PDF/contact/sidebar differences (Scholar/ORCID academic-only).

---

## 6. Demo (no API key)

```bash
python scripts/run_demo.py
python scripts/run_demo.py --assemble
python scripts/run_demo.py --pdf
```

Fictional candidate **Alex Rivera**. Sample run: `cv_generation/demo/northline_ml_engineer/`. Walkthrough: `docs/DEMO.md`, `docs/DEMO_VIDEO_SCRIPT.md`. Launch draft: `docs/SHOW_HN.md`.

---

## 7. Shared CV utilities

| Module | Role |
|--------|------|
| `shared/cv_loader.py` | Resolve markdown + keyword/skill profiles |
| `shared/cv_registry.py` | Multi-CV registry, slugs, user vs demo paths |
| `shared/cv_form.py` | Fake/real field form, strip real values, assemble markdown |
| `shared/cv/*.demo.md` | Committed fiction |
| `repo_paths.py` | `REPO_ROOT` |

---

## 8. Console entry points (`pyproject.toml`)

- `ingest-nav-jobs`, `ingest-finn-jobs`, `score-jobs`, `job-dashboard`, `run-cv-tailoring`

Additional modules (no console_scripts): Jobbnorge ingest, FINN deadlines, audits, `private_cv`, `run_agent_pipeline`, `agent_cli`, cycle script, demo, safe-to-push, bulk deanonymize, `scripts/agent_apply_job.sh`.

---

## 9. Tests

Under `job_search/tests/`, `cv_generation/tests/`, `shared/tests/`, `scripts/test_check_safe_to_push.py`. Fixtures include FINN HTML/JSON-LD variants, Jobbnorge HTML, legacy run folders without company in the id.

---

## 10. Agent / Cursor integration in this repo

- `AGENTS.md` — layout, private data, supplementary docs, cover letter voice
- Rules: project boundary, CV style, graphify (CLI currently missing)
- Chat backup: `scripts/backup_agent_exchanges.py` → `review_pack/` (gitignored JSONL)

---

## 11. Known gaps / doc drift (for reviewers)

- `CV_AUTOMATION.md` “How to run” still says academic `application_letter.md` / `research_proposal.md` are not auto-generated; pipeline + dashboard now can generate them
- Graphify output stale (built `56e18d61`, 2026-09-09); `graphify` binary not installed
- Preference JSON is collected, not yet used in `score_jobs`
- FINN has no official API; throttling is a product risk
- Jobbnorge + related dashboard flags were **uncommitted** when this inventory was written
- `cover_letter_generator.py` module docstring still says academic docs are not generated there (true for that file; they live in `supplementary_generator.py`)

---

## 12. Typical end-to-end path

```text
NAV/FINN/Jobbnorge ingest → SQLite → score_jobs
  → dashboard browse / pin / skip
  → Apply drawer → cv_runs/<id> anonymized markdown
  → ~/private/cv/cv apply <id> → deanonymized PDF (user machine only)
```
