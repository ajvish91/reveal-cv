# Agent handoff: review this codebase

You are reviewing **Reveal CV** (`job-search-automation`), a local Norwegian job-search + anonymized CV tailoring tool. Work **only** inside this repository.

## Hard constraints

- Do **not** read `~/private/cv/` or any identity mapping JSON with real values.
- Do **not** treat gitignored `shared/cv/industry.md` / `academic.md` as demo data if they exist locally; demo templates are `*.demo.md`.
- Do **not** commit `cv_generation/cv_runs/`, PDFs, job posting `.txt` files (except `demo_northline_ml_engineer.txt`), or `review_pack/agent-transcripts/`.
- Follow `AGENTS.md`, `.cursor/rules/project-boundary.mdc`, and `.cursor/rules/cv-tailoring-style.mdc`.
- Graphify CLI is **not** on PATH here. `graphify-out/` exists but is gitignored and last built 2026-09-09 (stale vs current code). Use docs + tests instead of assuming the graph is current.

## Read first

1. `README.md` — product surface
2. `PRIVACY.md` + `docs/GIT_AND_PRIVACY.md`
3. `job_search/JOB_SEARCH.md`
4. `cv_generation/CV_AUTOMATION.md` + `cv_generation/AGENT_INTEROP.md`
5. `docs/review/FEATURES.md` — this inventory
6. `review_pack/transcript_index.md` — conversation history (local)

## Current git state (as of 2026-10-13)

- Branch: `main`, remote `origin` = GitHub `ajvish91/reveal-cv`
- **Uncommitted work** includes Jobbnorge ingest (`job_search/jobbnorge_client.py`, `ingest_jobbnorge_jobs.py`), NAV feed fetch tests, dashboard ingest skip-Jobbnorge, job dedup across three sources, and CV/private-cv / cover-letter generator edits
- `README.md` already documents Jobbnorge in the committed-doc sense locally; confirm tests vs docs if you review ingest

## Suggested review questions

1. Privacy: can an agent or a git push leak real identity? (`scripts/check_safe_to_push.py`, gitignore, dashboard mapping download)
2. Ingest honesty: NAV incremental feed vs stale-marking; FINN scrape ethics/rate limits; Jobbnorge PDF detail quality
3. Scoring: strong-hit `score_base` vs TEK boosts; academic vs industry tracks; PhD-student hide vs postdoc keep
4. Apply pipeline: dashboard drawer → run folder → providers → `drafted` status; overwrite flags; Norwegian localization
5. Assembly honesty: `cv_assemble.py` must not invent roles or drop bullets; chronology rules in `cv_style.py`
6. Doc drift: `CV_AUTOMATION.md` still says academic letters are not auto-generated; `supplementary_generator.py` + `run_agent_pipeline.py` now generate them
7. Test coverage vs uncommitted Jobbnorge / dashboard ingest paths

## How to cite prior chats

Index: `review_pack/transcript_index.md`. Full JSONL: `review_pack/agent-transcripts/<uuid>/<uuid>.jsonl`. When referring to a chat in a reply, use `[title](<uuid without .jsonl>)`.
