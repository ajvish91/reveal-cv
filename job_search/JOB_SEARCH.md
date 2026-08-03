# Job search pipeline

Phases: **ingest** (NAV feed + FINN.no scrape) → **score** (vs CV profiles) → **dashboard** (browse and track applications).

Profiles are loaded from [`../shared/cv/`](../shared/cv/) (`academic.md`, `industry.md`).

## Commands

From the repository root (with `.venv` active):

```bash
# Optional: refresh TEK Rogaland employer list
.venv/bin/python -m job_search.fetch_tek_rogaland_members

# Daily ingest with filtered defaults (keywords + preferred locations + tech allowlist)
.venv/bin/python -m job_search.ingest_nav_jobs
.venv/bin/python -m job_search.ingest_finn_jobs

# Score postings against CV keywords/skills
.venv/bin/python -m job_search.score_jobs
.venv/bin/python -m job_search.score_jobs --track industry --print-top 20

# One-shot automation wrapper for scheduled runs (NAV + FINN ingest, then score)
.venv/bin/python scripts/run_job_search_cycle.py
.venv/bin/python scripts/run_job_search_cycle.py --ingest-arg=--max-pages --ingest-arg=4
.venv/bin/python scripts/run_job_search_cycle.py --skip-finn-ingest
.venv/bin/python scripts/run_job_search_cycle.py --finn-ingest-arg=--max-pages --finn-ingest-arg=5

# Explorer UI
.venv/bin/streamlit run job_search/dashboard.py
```

The repo includes `job_search/.streamlit/config.toml` with `runOnSave = true` so the app reloads when you edit dashboard code. Override from the shell:

```bash
.venv/bin/streamlit run job_search/dashboard.py --server.runOnSave true
```

### Auto-refresh (dashboard)

The dashboard refreshes data without a manual browser reload in three cases:

| Trigger | What happens |
|---------|----------------|
| **Ingest & score** completes | `st.cache_data.clear()` then `st.rerun()` — job lists and metrics reload from SQLite |
| **Apply / Modify** pipeline completes | Main page reruns (applied roles, status badges); the dialog stays open with a **Close** button until you dismiss it |
| **Sidebar auto-refresh** (optional, default off) | **Refresh cached data** → Off / Every 2 / 5 / 10 min — clears cached queries and reruns on the interval (does **not** run NAV/FINN ingest) |

Periodic refresh is skipped while ingest or an Apply pipeline is running.

Use the sidebar **Refresh jobs** section to run the same cycle from the browser (no shell):

- **Ingest & score** — runs `scripts/run_job_search_cycle.py` (NAV + FINN ingest, then score both tracks).
- Optional: **Skip NAV**, **Skip FINN**, **FINN: academic queries only** (FINN `--search-track academic`).
- Shows a live status panel (typically 1–5 minutes), then JSON step summaries and active counts (NAV, FINN, academic track).
- Disabled while an Apply pipeline or another ingest is running.

Defaults match the daily automation: both sources, FINN `--search-track both`, NAV without `--mark-stale`.

### Dashboard overview

The dashboard opens with a **compact metrics row** (active jobs, apply soon, Rogaland matches, applications) and **collapsible overview sections** so the first screen stays quiet.

| Area | Default state | Contents |
|------|---------------|----------|
| Top metrics | Visible | Active jobs, apply-soon count, Rogaland matches, applications logged |
| More stats | Collapsed | Score rows, DB totals, source split, track split |
| **Relevant positions (N)** | Collapsed | Top 5 by `score_total` with CV keyword/skill overlap (`score_base > 0` or matched terms); location/TEK-only boosts alone do not qualify (min-score slider inside) |
| **Newest positions (N)** | Collapsed | Top 5 by `published` descending |
| **Rogaland + profile match (N)** | Collapsed | Top 5 Rogaland matches for the current track |
| **Applied roles (N)** | Collapsed | Applications for the selected CV track: status badge, score, **Modify**, Delete |
| Charts | Collapsed | Location, application status, score bands |

Each overview job row shows **title · company · status (when logged) · score · Apply/Modify** on one line. Open **Details** for deadline, keyword hits, score breakdown, and job link.

**Applied roles** (below overview, same page) lists logged applications for the sidebar **CV track**. Default status filter: `drafted`, `applied`, `interested`. Each row shows **title · company · status · score** with **Modify** (re-run pipeline on the existing CV run with overwrite options), and **Delete** (removes the SQLite application row only; `cv_generation/cv_runs/` folders stay on disk). **Details** shows run folder basename, `~/private/cv/cv apply <run_id>`, notes, and cover letter path. When two or more **drafted** rows have runs, a bulk deanonymize command is shown. Use **Show all applications** or the status multiselect to widen the list; **All rows (table)** is inside the section.

**Job explorer** uses the same compact row pattern (paginated). The full dataframe lives in a collapsed **Full data table** expander.

Sidebar:

- **Refresh jobs** — **Ingest & score** button (NAV + FINN + score via `run_job_search_cycle.py`); optional Skip NAV / Skip FINN / FINN: academic queries only.
- **Auto-refresh** — optional **Refresh cached data** interval (Off, 2, 5, or 10 minutes); reloads lists from SQLite without ingest.
- **CV track** stays visible at the top.
- **Filters** (collapsed): source, dedup, PhD hide, **Show academic roles only** (display filter; default on for academic track), apply-soon window, ICT allowlist, noise blocklist.
- **Apply defaults** (collapsed): pre-fills application language and default tailoring instructions in the Apply/Modify dialog.

### Apply / Modify workflow (CV pipeline)

Each role row has a single **Apply** or **Modify** button. **Apply** appears when there is no application yet or status is `interested`. **Modify** appears once an application is `drafted`, `applied`, or at a later stage.

Clicking the button opens an **Apply / Modify** dialog (`st.dialog` on Streamlit ≥ 1.33) with:

| Field | Behavior |
|-------|----------|
| Application language | English or Norwegian (Bokmål); pre-filled from sidebar defaults |
| Custom prompts | Per-role tailoring notes merged with sidebar defaults |
| Document checkboxes | Industry: cover letter (pre-checked from posting detection). Academic: application letter (default on), research proposal (on when posting mentions it). CV is always generated. |
| Overwrite checkboxes | **Modify** only, when the artifact already exists: CV, cover letter, application letter, research proposal |
| Application notes | **Modify** only; editable notes stored on the application row |
| Start / Modify | Queues the pipeline; live status appears in the same dialog |
| Cancel | Closes without running |

Sidebar **Apply defaults** pre-fill language and tailoring instructions; they are not removed from the sidebar.

Pipeline stages shown in the dialog:

1. Export job posting
2. Prepare CV run
3. Parse job description
4. Rank keywords
5. Select track
6. Tailor bullets
7. ATS check
8. Assemble CV
9. Cover letter / application letter / research proposal (only if checked)
10. Norwegian localization (when language is Norwegian)
11. Complete

After a successful run the application row is upserted with status **`drafted`** and the row button changes to **Modify**. The main page refreshes automatically; use **Close** in the dialog when you are done reviewing the run summary.

Rows with a deadline inside the sidebar apply-soon window show a red **Apply soon** badge on the compact row.

Flow:

1. Exports the posting to `cv_generation/jobs/{finn|nav}_{uuid}_{slug}.txt`
2. Runs `python -m cv_generation.run_cv_tailoring --job-file … --company … --role …` (writes `apply_prompts.txt` when instructions are present)
3. Runs `python -m cv_generation.run_agent_pipeline --run-dir <run_dir>` with document flags from the dialog (`--generate-cover-letter`, `--generate-application-letter`, `--generate-research-proposal`, and overwrite flags on Modify)
4. Upserts `applications` with status **`drafted`** and the run path in `notes`
5. Shows the **run folder basename** (e.g. `20260713T120000Z_Falkor_software-ai-engineer`) for deanonymization

The sidebar **CV track** (`industry` / `academic`) is stored on the application row.

**Job links:** each row has an **Open job** link (`application_url` or `link`). When no URL is stored, use **View posting (offline)** to read `description_text`.

**Deanonymize after Apply:**

```bash
~/private/cv/cv apply 20260713T120000Z_Falkor_software-ai-engineer
# bulk:
~/private/cv/cv apply run_id1 run_id2
# or:
scripts/bulk_apply_deanonymize.sh run_id1 run_id2
```

The old **Prepare CV run** section is replaced by **Apply / Modify** (tailoring + full pipeline + `drafted` status).

### Legacy: manual CV prep

You can still run tailoring and the agent pipeline from the shell:

```bash
.venv/bin/python -m cv_generation.run_cv_tailoring --job-file cv_generation/jobs/nav_….txt --company "…" --role "…"
.venv/bin/python -m cv_generation.run_agent_pipeline --run-dir cv_generation/cv_runs/<run_id>
```

## Data files

| Path | Role |
|------|------|
| `data/jobs.sqlite` | Postings, scores, application status |
| `teknorge_medlemmer_rogaland.csv` | TEK members with Rogaland evidence (scoring boost) |

Override DB path: `--db` on ingest/score/automation, or `JOBS_DB` env var for the dashboard.

## Sources

| Source key | Ingest module | Notes |
|------------|---------------|-------|
| `nav_arbeidsplassen` | `ingest_nav_jobs.py` | Official NAV PAM feed (JWT) |
| `finn_no` | `ingest_finn_jobs.py` | Search + JSON-LD detail scrape (no public API) |

FINN ingest runs **multiple search queries** (see `finn_search_queries.py`) and dedupes by `finnkode`. Default rate limit: **0.3s** between requests (`--sleep-s`). There is no official FINN API; use polite scraping for personal job search and review FINN terms periodically.

Example FINN-only commands:

```bash
.venv/bin/python -m job_search.ingest_finn_jobs
.venv/bin/python -m job_search.ingest_finn_jobs --max-pages 5 --max-results-per-query 80
.venv/bin/python -m job_search.ingest_finn_jobs --queries "data engineer,AI engineer" --no-require-tech
.venv/bin/python -m job_search.ingest_finn_jobs --search-only
.venv/bin/python -m job_search.ingest_finn_jobs --search-track academic
```

After updating FINN academic queries in `role_search_config.py`, re-run **ingest** (and **score**) so new university postings enter the database. The dashboard filter only affects which stored rows are shown; it does not fetch new ads.

### Academic CV track (dashboard)

The sidebar **CV track** selects which `job_scores.track` column is used (`industry` vs `academic`). Scoring uses the matching CV profile keywords/skills, but both tracks share the same ingested job pool.

When **CV track** is **academic**, enable **Show academic roles only** (default **on** under **Filters**) to prioritize university and research postings:

- Kept: postdoc, researcher, førstelektor, førsteamanuensis, universitetslektor, associate professor, vitenskapelig stilling, employers such as universities and research institutes.
- Hidden while the toggle is on: pure industry titles (e.g. Senior Data Engineer at Capgemini) even if they score on shared AI/data keywords on the academic profile.

Turn **Show academic roles only** off to browse all scored jobs on the academic track (useful when you also apply to industry roles with the academic CV).

Overview sections (**Relevant**, **Newest**, **Rogaland + profile match**) and **Job explorer** respect this filter when it is on.

## Filtering

ICT/tech allowlist and noise blocklist live in `job_filters.py`. Ingest keyword matching uses CV profiles plus curated application-history boosts in `role_search_config.py` (merged by `ingest_keywords.py`).

### Keyword sources (ingest `--keyword-filter`)

| Layer | Module | What it does |
|-------|--------|----------------|
| CV profiles | `shared/cv_loader.py` | `keywords` and (by default) `skills` from `industry.md` / `academic.md` (or `*.demo.md` in CI) |
| Application boosts | `role_search_config.py` → `DEFAULT_INGEST_KEYWORD_BOOSTS` | Curated from `cv_generation/cv_runs/` (agentic AI, RAG, platform engineer, postdoc, research scientist, …) |
| FINN search | `role_search_config.py` → `DEFAULT_FINN_SEARCH_QUERIES` + `DEFAULT_ACADEMIC_FINN_SEARCH_QUERIES` | Re-exported by `finn_search_queries.py`; default ingest merges industry + academic queries (`--search-track both`) |
| Academic role filter | `job_filters.py` → `ACADEMIC_ROLE_INCLUDE_TERMS` | Dashboard **Show academic roles only** (default on when CV track is academic) |
| Tech allowlist | `job_filters.py` → `DEFAULT_TECH_INCLUDE_TERMS` | `--require-tech` on ingest; dashboard “ICT / tech filter” uses the same list |
| Noise blocklist | `job_filters.py` → `DEFAULT_EXCLUDE_TERMS` | Optional `--exclude-noise` on ingest; dashboard blocklist is off by default |

Inspect merged ingest keywords:

```bash
.venv/bin/python -m job_search.ingest_nav_jobs --list-keywords
.venv/bin/python -m job_search.ingest_finn_jobs --list-keywords
```

Defaults:

- Ingest now defaults to a daily-use posture: `--keyword-filter`, `--require-tech`, and `--exclude-noise` are on by default.
- `--keyword-source` defaults to **`keywords-and-skills`** (broader recall than keywords alone).
- Application-history boosts are always merged so demo CV templates and sparse keyword lists still match roles you apply to.
- Preferred-location matching uses `locations_preferred` from the loaded CV profiles. This drives ingest retention, dashboard filtering, and scoring boosts; the older Rogaland flag is still stored for backward compatibility.
- **Deadlines:** `expires` is parsed from NAV feed data or FINN `validThrough` (ISO or Norwegian text). Dashboard urgency uses `job_search/deadline_utils.py`.
- **PhD student filter:** dashboard default hides PhD fellowship / stipendiat openings via `job_filters.matches_phd_student_opening` (postdoc and researcher roles are kept).
- When a full ingest walk completes, postings not seen in the current run are marked `INACTIVE` so stale ads do not stay active forever (per source).
- **NAV:** the feed is incremental (`If-Modified-Since`); stale marking is **off by default** (`--mark-stale` only for full backfills). Using stale marking on daily NAV runs incorrectly inactivated most NAV rows.
- **FINN:** stale marking stays on after a complete search crawl (expected for query-based ingest).
- NAV feed state (`ETag` plus last successful ingest timestamp) is persisted in the SQLite DB and reused across runs unless you pass `--no-use-feed-state`.
- FINN persists `finn_no:last_success_at` in `ingest_state` unless you pass `--no-use-ingest-state`.

## Automation

For a cron-style scheduled run:

```bash
cd /path/to/reveal-cv   # repository root
.venv/bin/python scripts/run_job_search_cycle.py >> job_search/data/job_search_cycle.log 2>&1
```

Typical customizations:

- Use `--ingest-arg=--since-days --ingest-arg=7` for a wider NAV recovery window.
- Use `--finn-ingest-arg=--max-pages --finn-ingest-arg=5` for deeper FINN backfills.
- Use `--skip-finn-ingest` if you only want NAV on a given run.
- Use `--skip-nav-ingest` if you only want FINN on a given run.
- Use `--score-arg=--no-tek` if you want pure CV/location scoring.
- Use `--skip-ingest` or `--skip-score` when rerunning only one stage.

## Logging

Structured logging is configured via `job_search/logging_config.py`. All modules under the `job_search` namespace write to the same file.

| Setting | Value |
|---------|--------|
| Default log file | `job_search/data/job_search.log` (append, rotated at ~2 MB, 3 backups) |
| Format | `%(asctime)s %(levelname)s [%(name)s] %(message)s` |
| Logger names | `job_search.ingest_nav`, `job_search.ingest_finn`, `job_search.dashboard`, `job_search.score` |

**Enable DEBUG** (HTTP retries, FINN parse details, per-page ingest progress):

```bash
JOB_SEARCH_LOG_LEVEL=DEBUG .venv/bin/python -m job_search.ingest_finn_jobs
JOB_SEARCH_LOG_LEVEL=DEBUG .venv/bin/streamlit run job_search/dashboard.py
```

**What gets logged**

- **NAV / FINN ingest:** pages fetched, cards/items seen, stored/skipped (noise, tech allowlist), detail fetches, stale rows marked; JSON summary at end.
- **FINN HTTP client:** retryable HTTP/URL errors (warning), final failures (error); JSON-LD parse skips (debug).
- **Score:** active job count and score rows per track; JSON summary.
- **Cycle script:** each step command and completion (`scripts/run_job_search_cycle.py`).
- **Dashboard:** ingest button + command, subprocess stdout lines, exit code and stderr on failure; apply pipeline start/complete/errors; academic filter state (track, `academic_roles_only`, row counts before/after filter).

The dashboard sidebar **Recent log** expander shows the last 50 lines of `job_search.log` (read-only). Ingest subprocess output is mirrored to the log file while still appearing in the UI status panel.

Private paths under `~/private/` are not logged. Repo paths and job UUIDs are fine.

## Cross-source deduplication

The same role often appears on both NAV and FINN. Logic lives in `job_dedup.py`:

- **Key:** normalized lowercase employer + title (punctuation stripped, whitespace collapsed).
- **Winner:** highest `score_total` (NAV wins ties).
- **Apply URL:** when duplicates exist, prefer NAV `application_url`; alternate links go in `duplicate_note`.

The dashboard **Job explorer** enables deduplication by default (`Deduplicate cross-source listings`). The table shows a `Sources` column (`nav_arbeidsplassen, finn_no`) and `Also listed at` for secondary links. Turn dedup off to see every DB row per source.
