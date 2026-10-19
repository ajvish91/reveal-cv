# Job search pipeline

Phases: **ingest** (NAV feed + FINN.no scrape + Jobbnorge catalog) → **score** (vs CV profiles) → **dashboard** (browse and track applications).

Profiles are loaded from [`../shared/cv/`](../shared/cv/) (`academic.md`, `industry.md`).

## Commands

From the repository root (with `.venv` active):

```bash
# Optional: refresh TEK Rogaland employer list
.venv/bin/python -m job_search.fetch_tek_rogaland_members

# Daily ingest with filtered defaults (keywords + tech allowlist; preferred locations for labels/filters only)
.venv/bin/python -m job_search.ingest_nav_jobs
.venv/bin/python -m job_search.ingest_finn_jobs
.venv/bin/python -m job_search.ingest_jobbnorge_jobs

# Score postings by strong keyword/skill hit count (+ optional TEK boost)
.venv/bin/python -m job_search.score_jobs
.venv/bin/python -m job_search.score_jobs --track industry --print-top 20

# Audit ACTIVE rows for noise / weak profile overlap (also runs at end of the daily cycle)
.venv/bin/python -m job_search.audit_noisy_jobs
.venv/bin/python -m job_search.audit_noisy_jobs --mark-blocklist-inactive

# Collect Skip/Reject preference labels (writes job_search/data/preference_features*.json; no score changes yet)
.venv/bin/python -m job_search.audit_preferences
.venv/bin/python -m job_search.audit_preferences --track industry --print-limit 30

# One-shot automation wrapper for scheduled runs (NAV + FINN ingest, then score)
.venv/bin/python scripts/run_job_search_cycle.py
.venv/bin/python scripts/run_job_search_cycle.py --ingest-arg=--max-pages --ingest-arg=4
.venv/bin/python scripts/run_job_search_cycle.py --skip-finn-ingest
.venv/bin/python scripts/run_job_search_cycle.py --finn-ingest-arg=--max-pages --finn-ingest-arg=5

# Explorer UI
.venv/bin/python -m job_search.webapp
```

Opens http://127.0.0.1:8765 (Bootstrap + FastAPI). Override bind address with `--host` / `--port`.

Use **Filters** in the UI to run the same cycle from the browser (no shell):

- **Ingest & score** — runs `scripts/run_job_search_cycle.py` (NAV + FINN + Jobbnorge ingest, then score both tracks).
- Optional: **Skip NAV**, **Skip FINN**, **Skip Jobbnorge**, **Academic search only** (FINN + Jobbnorge `--search-track academic`).
- Shows a live status panel (typically 1–5 minutes), then JSON step summaries and active counts (NAV, FINN, academic track).
- Disabled while an Apply pipeline or another ingest is running.

Defaults match the daily automation: both sources, FINN `--search-track both`, NAV without `--mark-stale`.

### Dashboard overview

The dashboard opens with a **compact metrics row** (active jobs, apply soon, applications) and **collapsible overview sections** so the first screen stays quiet. Content is centred in a Bootstrap `container-xl`.

| Area | Default state | Contents |
|------|---------------|----------|
| Top metrics | Visible | Active jobs, apply-soon count, applications logged |
| More stats | Collapsed | Score rows, DB totals, source split, track split |
| **Relevant positions (N)** | Collapsed | Top 5 by `score_total` with CV keyword/skill overlap (`score_base` = strong hit count); TEK-only boosts alone do not qualify (min-score slider inside) |
| **Newest positions (N)** | Collapsed | Top 5 by `published` descending |
| **Applied roles (N)** | Collapsed | Applications for the selected CV track: status badge, score, **Modify**, Delete |
| Charts | — | Not in the Bootstrap UI (metrics cover the same counts) |

Each overview job row shows **title · company · status (when logged) · score · Apply/Modify** on one line. Open **Details** for deadline, keyword hits, score breakdown, and job link.

**Applied roles** (below overview, same page) lists logged applications for the navbar **CV track**. Default status filter: `drafted`, `applied`, `interested`. Each row shows **title · company · status · score** with **Modify**, **More** (pin / mark applied / skip / reject / clear tracking), and **Delete**. **Details** shows the same quick actions plus run folder basename, `~/private/cv/cv apply <run_id>`, and notes. When two or more **drafted** rows have runs, a bulk deanonymize command is shown. Use **Show all applications** or the status multiselect to widen the list (includes `skipped`).

Explorer and overview job rows have a **More** menu: **Pin** (stays visible and sorts to the top), **Mark applied**, **Mark interested**, **Skip / trash** (hidden when “Hide applied / skipped…” is on), **Reject**, **Withdraw**, and **Clear tracking**.

**Job explorer** uses the same compact row pattern (paginated). By default it hides jobs with an application (drafted+) and **expired** deadlines (past `expires`; unknown deadlines stay visible). Uncheck **Hide expired positions** to show them.

**Filters** (left drawer):

- **Refresh jobs** — **Ingest & score** (NAV + FINN + score via `run_job_search_cycle.py`); optional Skip NAV / Skip FINN / FINN: academic queries only.
- **CV track** stays visible in the top bar.
- Source, dedup, PhD hide, **Show academic roles only** (display filter; default on for academic track), apply-soon window, ICT allowlist, noise blocklist.
- **Apply defaults** — pre-fills application language and default tailoring instructions in the Apply/Modify drawer.

A sticky status bar shows ingest and Apply pipeline progress so you can keep scrolling the list.

**CVs** (navbar) opens `/cv`: add or edit anonymized industry/academic CVs, download the fake→real mapping JSON, and check which saved CV each track uses. Fake markdown is stored in-repo; real values stay in the downloaded JSON / `~/private/cv/`.

### Apply / Modify workflow (CV pipeline)

Each role row has a single **Apply** or **Modify** button. **Apply** appears when there is no application yet or status is `interested`. **Modify** appears once an application is `drafted`, `applied`, or at a later stage.

Clicking **Apply** / **Modify** opens a right-hand drawer (not a modal) with:

| Field | Behavior |
|-------|----------|
| Application language | English or Norwegian (Bokmål); pre-filled from sidebar defaults |
| Custom prompts | Per-role tailoring notes merged with sidebar defaults |
| Document checkboxes | Industry: cover letter (pre-checked from posting detection). Academic: application letter (default on), research proposal (on when posting mentions it). CV is always generated. |
| Overwrite checkboxes | **Modify** only, when the artifact already exists: CV, cover letter, application letter, research proposal |
| Application notes | **Modify** only; editable notes stored on the application row |
| Start / Modify | Queues the pipeline; live status appears in the sticky status bar |
| Close | Closes the drawer without stopping a running pipeline |

**Apply defaults** in Filters pre-fill language and tailoring instructions.

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

After a successful run the application row is upserted with status **`drafted`** and the row button changes to **Modify**. Job lists refresh in place; the drawer can be closed without jumping the explorer scroll.

Rows with a deadline inside the sidebar apply-soon window show a red **Apply soon** badge on the compact row.

Flow:

1. Exports the posting to `cv_generation/jobs/{finn|nav}_{uuid}_{slug}.txt`
2. Runs `python -m cv_generation.run_cv_tailoring --job-file … --company … --role …` (writes `apply_prompts.txt` when instructions are present)
3. Runs `python -m cv_generation.run_agent_pipeline --run-dir <run_dir>` with document flags from the drawer (`--generate-cover-letter`, `--generate-application-letter`, `--generate-research-proposal`, and overwrite flags on Modify)
4. Upserts `applications` with status **`drafted`** and the run path in `notes`
5. Shows the **run folder basename** (e.g. `20260713T120000Z_Falkor_software-ai-engineer`) for deanonymization

The navbar **CV track** (`industry` / `academic`) is stored on the application row.

**Job links:** each row has an **Open job** link. It prefers `link` (the public ad/listing) and falls back to `application_url`; Jobbnorge and some NAV rows store a login-gated `application_url`, which is why `link` wins. When no URL is stored, use **View posting (offline)** to read `description_text`.

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
| `jobbnorge` | `ingest_jobbnorge_jobs.py` | Public catalog API (`publicapi.jobbnorge.no`) + PDF text for detail |

FINN ingest runs **multiple search queries** (see `finn_search_queries.py`) and dedupes by `finnkode`. Default pacing: random pause between **1.0–2.0s** (`--sleep-s` / `--sleep-s-max`), max **40** detail pages per run (`--max-details`). Detail budget prefers **new** `finnkode`s first, then active rows missing `expires` (card teasers are too sparse for keyword/tech gates). There is no official FINN API; FINN may throttle or stall bulk detail fetches, so avoid large deadline backfills.

**Deadlines / expired ads:** Prefer `--mark-known-only` (no HTTP). Do not run large `refresh_finn_deadlines --limit N` batches; if you must backfill, use small limits and randomized sleep, e.g.:

```bash
.venv/bin/python -m job_search.refresh_finn_deadlines --mark-known-only
.venv/bin/python -m job_search.refresh_finn_deadlines --limit 5 --sleep-s 2 --sleep-s-max 5
```

Ingest cycle only marks already-known past deadlines inactive. Opening a job in the UI does **not** fetch FINN.

Example FINN-only commands:

```bash
.venv/bin/python -m job_search.ingest_finn_jobs
.venv/bin/python -m job_search.ingest_finn_jobs --max-pages 5 --max-results-per-query 80
.venv/bin/python -m job_search.ingest_finn_jobs --queries "data engineer,AI engineer" --no-require-tech
.venv/bin/python -m job_search.ingest_finn_jobs --search-only
.venv/bin/python -m job_search.ingest_finn_jobs --search-track academic
```

Jobbnorge-only examples:

```bash
.venv/bin/python -m job_search.ingest_jobbnorge_jobs
.venv/bin/python -m job_search.ingest_jobbnorge_jobs --search-track academic --max-details 60
.venv/bin/python -m job_search.ingest_jobbnorge_jobs --search-only
```

After updating FINN academic queries in `role_search_config.py`, re-run **ingest** (and **score**) so new university postings enter the database. The dashboard filter only affects which stored rows are shown; it does not fetch new ads.

### Academic CV track (dashboard)

The navbar **CV track** selects which `job_scores.track` column is used (`industry` vs `academic`). Scoring uses the matching CV profile keywords/skills, but both tracks share the same ingested job pool.

When **CV track** is **academic**, enable **Show academic roles only** (default **on** under **Filters**) to prioritize university and research postings:

- Kept: postdoc, researcher, førstelektor, førsteamanuensis, universitetslektor, associate professor, vitenskapelig stilling, employers such as universities and research institutes.
- Hidden while the toggle is on: pure industry titles (e.g. Senior Data Engineer at Capgemini) even if they score on shared AI/data keywords on the academic profile.

Turn **Show academic roles only** off to browse all scored jobs on the academic track (useful when you also apply to industry roles with the academic CV).

Overview sections (**Relevant**, **Newest**) and **Job explorer** respect this filter when it is on.

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
- Application-history boosts (`DEFAULT_INGEST_KEYWORD_BOOSTS`) are used for **FINN search discovery** and for **demo CV** keep-gates only. Real profiles gate keep/drop with strong CV keywords/skills alone; bare `research` / `innovation` / `philosophy` / `forskning` cannot keep an ad. Opt in with `--application-boosts` on ingest if needed.
- After each daily cycle, `job_search.audit_noisy_jobs` prints zero-score / blocklist / weak-hit counts (override with `--skip-audit` / `--audit-arg`).
- The cycle then runs `job_search.dedupe_jobs`, which marks cross-source duplicates INACTIVE (same normalized employer + title on NAV / Jobbnorge / FINN, keeping the preferred source). Multiple ads from a single source are left untouched. Override with `--skip-dedupe`.
- **Thin FINN search cards are always hidden** from the explorer and overview: a `finn_no` row whose description is shorter than `MIN_FINN_DESCRIPTION_CHARS` (280) stays in the DB for detail backfill but never appears as a job. A FINN ad that 404/410s (or has no job content) is stored as an `INACTIVE` tombstone rather than a thin card, and search cards now require a real CV keyword hit to be stored.
- Preferred-location matching uses `locations_preferred` from the loaded CV profiles for dashboard **Rogaland / preferred** filtering and location labels. It does **not** add score points. Location alone no longer keeps an ad during ingest when `--keyword-filter` is on.
- **Explorer location controls:** filter with **Preferred locations only**; sort with **Sort by → Location** (also Score / Newest).
- **Scoring:** `score_base` is the count of distinct strong keyword/skill hits (word-boundary match; short tokens like `go`/`ai` need tech context so brands such as Cut'n Go do not match). `score_total` = hit count + relevance-gated boosts (TEK employer +1; academic employer +2 / academic title +1). In the **academic track only**, ads with academic context also get **postdoc +3**, **AI/KI in the title +2**, or **AI/KI only in the description +1.5** (Norwegian and English terms). Boosts apply **only when `score_base > 0`**, so an off-target ad at a boosted employer can no longer outrank a genuine match. Geographic boost is always 0.
- **Ingest noise:** bare Norwegian `utvikler`/`utvikling` are not tech-allowlist hits (they match salon “teamutvikling” / “utvikler deg”). Use compounds like `systemutvikler`, `softwareutvikler`, `digital utvikling`. Noise blocklist includes frisør/salong/hair terms.
- **Deadlines:** `expires` is parsed from NAV feed data or FINN (`validThrough` when present, else the page **Søknadsfrist** / expired badge). Dashboard urgency uses `job_search/deadline_utils.py`.
- **PhD student filter:** dashboard default hides PhD fellowship / stipendiat openings via `job_filters.matches_phd_student_opening`. It classifies on the **title first** (`PhD/Ph.D Research Fellow`, `PhD Candidate`, `stipendiat`, `doktorgradsstipendiat`, …), so postdocs that merely mention supervising PhD candidates in the description are kept. Postdoc and researcher roles stay visible.
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
- Use `--score-arg=--no-tek` if you want pure keyword-hit scoring.
- Use `--skip-ingest` or `--skip-score` when rerunning only one stage.

## Logging

Structured logging is configured via `job_search/logging_config.py`. All modules under the `job_search` namespace write to the same file.

| Setting | Value |
|---------|--------|
| Default log file | `job_search/data/job_search.log` (append, rotated at ~2 MB, 3 backups) |
| Format | `%(asctime)s %(levelname)s [%(name)s] %(message)s` |
| Logger names | `job_search.ingest_nav`, `job_search.ingest_finn`, `job_search.web`, `job_search.score` |

**Enable DEBUG** (HTTP retries, FINN parse details, per-page ingest progress):

```bash
JOB_SEARCH_LOG_LEVEL=DEBUG .venv/bin/python -m job_search.ingest_finn_jobs
JOB_SEARCH_LOG_LEVEL=DEBUG .venv/bin/python -m job_search.webapp
```

**What gets logged**

- **NAV / FINN ingest:** pages fetched, cards/items seen, stored/skipped (noise, tech allowlist), detail fetches, stale rows marked; JSON summary at end.
- **FINN HTTP client:** retryable HTTP/URL errors (warning), final failures (error); JSON-LD parse skips (debug).
- **Score:** active job count and score rows per track; JSON summary.
- **Cycle script:** each step command and completion (`scripts/run_job_search_cycle.py`).
- **Dashboard:** ingest button + command, subprocess stdout lines, exit code and stderr on failure; apply pipeline start/complete/errors; academic filter state (track, `academic_roles_only`, row counts before/after filter).

The dashboard **Filters** pane shows recent log lines. Ingest subprocess output is mirrored to the log file while still appearing in the sticky status bar.

Private paths under `~/private/` are not logged. Repo paths and job UUIDs are fine.

## Cross-source deduplication

The same role often appears on both NAV and FINN. Logic lives in `job_dedup.py`:

- **Key:** normalized lowercase employer (legal suffixes such as AS/Norge stripped) + title (punctuation stripped, whitespace collapsed).
- **Winner:** highest `score_total` (NAV wins ties).
- **Apply URL:** when duplicates exist, prefer NAV `application_url`; alternate links go in `duplicate_note`.

The dashboard **Job explorer** enables deduplication by default (`Deduplicate cross-source listings`). The table shows a `Sources` column (`nav_arbeidsplassen, jobbnorge, finn_no`) and `Also listed at` for secondary links. Turn dedup off to see every DB row per source.
