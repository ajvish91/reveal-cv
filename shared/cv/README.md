# CV sources

## Committed (safe for git)

- `industry.demo.md` — fictional demo template (ALEX RIVERA)
- `academic.demo.md` — fictional demo template

## Your real CV (never commit)

These filenames are **gitignored** in this folder:

```text
shared/cv/industry.md
shared/cv/academic.md
```

Copy your real markdown here for local work, or use the private directory:

```text
~/private/cv/cv/industry.md
~/private/cv/cv/academic.md
```

```bash
export CV_SOURCE_DIR=~/private/cv/cv   # optional explicit override
```

**Load order:** `CV_SOURCE_DIR` → `~/private/cv/cv/` (personal `.md`) → `shared/cv/industry.md` / `academic.md` (gitignored) → `*.demo.md` templates.

## Recover after demo templates replaced your repo copies

If your real files were overwritten in git prep and you never ran `export-cv-sources`, restore from the latest tailoring run snapshot:

```bash
.venv/bin/python -m cv_generation.private_cv recover-cv-sources
```

That copies `cv_runs/<latest>/cv_industry_source.md` and `cv_academic_source.md` into `~/private/cv/cv/` and `shared/cv/` (anonymized master CV — same as the pipeline used before `apply`).

One-time export (when your real files are loaded):

```bash
.venv/bin/python -m cv_generation.private_cv export-cv-sources
```
