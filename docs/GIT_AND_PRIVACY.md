# Git-ready project plan

This document describes how to publish the repo safely and evolve it as a maintainable open-source-style project.

## What is safe in git

| Commit | Do not commit |
|--------|----------------|
| `shared/cv/industry.demo.md`, `academic.demo.md` (demo fiction) | `shared/cv/industry.md`, `academic.md` (gitignored) or `~/private/cv/cv/` |
| `cv_generation/cv_identity_mapping.example.json` | `cv_identity_mapping.json` with real values |
| Python code, job posting samples in `cv_generation/jobs/` | `cv_generation/cv_runs/` (generated) |
| Subagent specs, tests, docs | PDFs, cover letters, deanonymized output |
| `.env.example` (no secrets) | `.env`, profile photos |

## Before every push

```bash
# 1. Scan code + shared for obvious leaks
.venv/bin/python scripts/check_safe_to_push.py

# 2. Confirm git only tracks intended files
git status
git diff --stat

# 3. Optional: ensure cv_runs never staged
git check-ignore -v cv_generation/cv_runs/some-run/final_cv.md
```

If you previously committed real CVs or runs, use `git rm --cached` and rotate any exposed secrets.

## One-time: move your real CV out of the repo

If `shared/cv/*.md` still had your profile:

```bash
.venv/bin/python -m cv_generation.private_cv export-cv-sources
# Copies current resolved CVs → ~/private/cv/cv/industry.md and academic.md
```

The repo now ships **demo** templates (`ALEX RIVERA`, fictional employers). Pipeline loads private copies when present.

Verify:

```bash
.venv/bin/python -m shared.cv_loader
# Should print: CV source dir: /Users/you/private/cv/cv
```

## Private workflow (unchanged)

```bash
~/private/cv/cv/                    # real industry.md + academic.md
~/private/cv/cv_identity_mapping.json
~/private/cv/deanonymized/<run>/
```

```bash
.venv/bin/python -m cv_generation.run_cv_tailoring --job-file cv_generation/jobs/example.txt
.venv/bin/python -m cv_generation.generate_cv_with_cursor --run-dir cv_generation/cv_runs/<id> --provider cursor
~/private/cv/cv apply <run_id>
```

## Agent providers

| Provider | Install | Env var | Notes |
|----------|---------|---------|--------|
| `cursor` (default) | `pip install cursor-sdk` | `CURSOR_API_KEY` | Uses Cursor agent in repo cwd |
| `anthropic` | `pip install anthropic` | `ANTHROPIC_API_KEY` | Claude via Messages API |
| `openai` | `pip install openai` | `OPENAI_API_KEY` | GPT via Chat Completions |
| `manual` | — | — | Writes `*_prompt.txt`; you paste JSON to `*_output.manual.json` |

```bash
.venv/bin/python -m cv_generation.generate_cv_with_cursor \
  --run-dir cv_generation/cv_runs/<id> \
  --provider anthropic \
  --model claude-sonnet-4-20250514
```

Optional extras in `pyproject.toml` (future):

```toml
[project.optional-dependencies]
agents-cursor = ["cursor-sdk"]
agents-anthropic = ["anthropic"]
agents-openai = ["openai"]
```

## Recommended repo structure (current)

```text
job-search-automation/
├── shared/cv/              # demo CV templates only
├── shared/cv_loader.py
├── cv_generation/          # tailoring, PDF, private CLI
├── job_search/             # NAV ingest + dashboard
├── scripts/check_safe_to_push.py
├── docs/GIT_AND_PRIVACY.md
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Roadmap for a “viable” git project

### Phase 1 — Hygiene (now)

- [x] Demo CV templates in repo; private override via `CV_SOURCE_DIR`
- [x] `.gitignore` for runs, PDFs, mapping, DB, private folder
- [x] Pre-push scanner script
- [x] Pluggable agent providers

### Phase 2 — Contributor experience

- [ ] `LICENSE` (MIT or Apache-2.0)
- [ ] `CONTRIBUTING.md` + issue templates
- [ ] `requirements-dev.txt` with optional agent deps
- [ ] GitHub Actions: `check_safe_to_push.py` + `pip install -e .` smoke test on demo CV
- [ ] One anonymized sample run folder (only `*.sample.json`, no `final_cv.md`)

### Phase 3 — Product shape

- [ ] Rename entrypoint: `generate_cv` module alias (keep `generate_cv_with_cursor` as backward compat)
- [ ] Config file `cv_generation/config.yaml` for default provider/model
- [ ] Cover letter pipeline behind same privacy rules
- [ ] Document job_search DB schema; ship empty `job_search/data/.gitkeep` only

### Phase 4 — Optional publish

- [ ] Remove machine-specific paths from docs (use `$REPO_ROOT` placeholders only)
- [ ] Add `CHANGELOG.md` and semver tags
- [ ] Separate public demo repo vs private dotfiles repo (optional)

## Cursor agents in this repo

`.cursor/rules` should keep agents **inside the repo** and never read `~/private/cv/`. Users run private commands locally; paste errors into chat if debugging.

## Files to delete locally (not in git)

If present in your working tree but not needed in repo:

- `rough CV.docx`, `rough CV academic.docx` (add to `.gitignore` — done)
- `teknorge_*.csv` if personal research exports
- Any copied `cv_identity_mapping.json` at repo root

Do not delete `~/private/cv/` — that is your source of truth.
