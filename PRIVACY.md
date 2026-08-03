# Privacy model

This project is built around one promise: **AI-assisted CV tailoring without exposing your real identity inside the repository.**

It does not claim that no data ever leaves your machine. It claims something narrower and more useful: **your name, email, phone, links, photo, and deanonymized outputs stay outside the project in `~/private/cv/`.**

## The short version

```text
Repo and AI side: anonymized placeholders only
Private side:     your real identity and final files
Bridge:           one local apply command
```

In practice, that means:

- The repo stores and processes anonymized CV content.
- The AI works on placeholders such as `MITCH EVANS`, fictional employers, and `cv-placeholder` URLs.
- Your real values live in `~/private/cv/cv_identity_mapping.json`.
- Deanonymized markdown and PDFs are written to `~/private/cv/deanonymized/`.

## What the AI sees

The AI can see:

- your anonymized work history and project descriptions
- skills, technologies, and role descriptions
- the job posting text you want to tailor against
- any generated tailored bullets, cover letters, or supplementary documents in anonymized form

The AI does not need to see:

- your real name
- your personal email or phone number
- your real LinkedIn, GitHub, Google Scholar, or ORCID URLs
- your profile photo
- your final deanonymized PDFs

## What stays outside the repo

The private folder is the identity boundary:

```text
~/private/cv/
├── cv_identity_mapping.json
├── config.env
├── cv/                    # optional real source CVs
├── profile_photo.jpg
└── deanonymized/<run_id>/
```

Files in that folder are intentionally outside the repository. Agents working in this repo are instructed not to read them.

## What is safe to commit

Safe in git:

- Python code and docs
- demo CVs such as `shared/cv/demo_only/`
- job posting samples in `cv_generation/jobs/`
- the example mapping file `cv_generation/cv_identity_mapping.example.json`

Do not commit:

- `~/private/cv/cv_identity_mapping.json`
- deanonymized output under `~/private/cv/deanonymized/`
- real `shared/cv/industry.md` or `shared/cv/academic.md`
- generated run outputs under `cv_generation/cv_runs/`
- profile photos or secrets

For the full maintainer checklist, see [`docs/GIT_AND_PRIVACY.md`](docs/GIT_AND_PRIVACY.md).

## The three commands that matter

### 1. Set up the private boundary once

```bash
.venv/bin/python -m cv_generation.private_cv setup
.venv/bin/python -m cv_generation.private_cv edit
```

This creates `~/private/cv/`, copies the example mapping, and installs the `~/private/cv/cv` helper.

### 2. Tailor inside the repo

```bash
.venv/bin/python -m cv_generation.run_cv_tailoring \
  --job-file cv_generation/jobs/finn_465089104_ml_ai_engineer.txt

.venv/bin/python -m cv_generation.run_agent_pipeline \
  --run-dir cv_generation/cv_runs/<run_id> \
  --provider cursor
```

At this stage, the output is still anonymized.

### 3. Reveal locally

```bash
~/private/cv/cv apply <run_id>
```

That command combines the anonymized run with your private mapping and renders the real application files outside the repo.

## Honest caveat

This is a **privacy-first workflow**, not a zero-knowledge system.

If you use `cursor`, `anthropic`, or `openai` as the provider, anonymized career content is still sent to that provider. The key difference is that the provider does not need your real identity or your final submission files.

If that distinction matters to you, this project is for you. If you need a fully offline CV tailoring pipeline, that would be a separate future mode.

## Try it without real data

The repo includes a safe demo using the fictional candidate **ALEX RIVERA**.

```bash
.venv/bin/python scripts/run_demo.py
.venv/bin/python scripts/run_demo.py --assemble
.venv/bin/python scripts/run_demo.py --pdf
```

See [`docs/DEMO.md`](docs/DEMO.md) for the walkthrough.

## FAQ

### Why not just paste my full CV into a chatbot?

Because the most sensitive part of a CV is often the identity layer: your name, direct contact details, public profile URLs, and the final submission artifacts. This workflow keeps that layer local.

### Why use a mapping file at all?

It gives you a repeatable split between anonymized generation and private reveal. You fill your real values once, then reuse them across runs.

### Why keep the private folder outside the repo?

So you can fork, back up, or publish the repository without dragging your personal data along with it.

### Is this only for Norway?

No. The CV tailoring core works on any job posting text. The Norway-specific parts today are the NAV job search module and the Norwegian localization helpers.
