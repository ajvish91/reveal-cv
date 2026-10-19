# 60-second demo script

Use this script to record a fast product demo for GitHub, Show HN, or social posts. It is intentionally short, privacy-first, and built around the fictional candidate **ALEX RIVERA**.

## Goal

Show that:

1. the repo workflow is real and runnable
2. the AI-facing material is anonymized
3. the real-name reveal happens later, locally, outside the project

## Recording setup

- Use the demo data only
- Keep your terminal and editor zoom large
- Do not open `~/private/cv/` during the recording
- End on a run artifact that still shows placeholder identity

## Shot list

### 0:00-0:08 - Open on the promise

Show `README.md` or a title slide with this line:

> Privacy-first CV tailoring where AI never learns your real identity.

Voiceover:

> This CV generator keeps the identity layer private. The AI sees placeholders, and the real reveal happens later on your machine.

### 0:08-0:18 - Show the fictional source

Open `shared/cv/demo_only/industry.md`.

Pause on:

- `ALEX RIVERA`
- the demo email
- the `DEMO CV` marker if visible

Voiceover:

> The demo uses a fictional candidate, so the whole workflow is safe to show and safe to commit.

### 0:18-0:32 - Run the demo

Run:

```bash
.venv/bin/python scripts/run_demo.py --assemble
```

If you want one extra beat afterward, also run:

```bash
.venv/bin/python scripts/run_demo.py --pdf
```

Voiceover:

> The pipeline builds a tailored CV run from a saved job posting and assembles the final markdown without needing any real personal data.

### 0:32-0:46 - Open the output

Open `cv_generation/demo/northline_ml_engineer/final_cv.md`.

Scroll just enough to show:

- the role title
- tailored CV structure
- the placeholder identity still present

Voiceover:

> This is the application-ready draft inside the repo. It is tailored, but still anonymized.

### 0:46-0:57 - Explain the private reveal

Switch to `PRIVACY.md` or the README quickstart and highlight:

```bash
~/private/cv/cv apply <run_id>
```

Voiceover:

> When you want the real version, one local command applies your private mapping outside the repository and writes the final PDF to your own private folder.

### 0:57-1:00 - End frame

End on a static frame with this line:

> Tailor in public. Reveal in private.

Optional sub-line:

> The real name never appeared.

## Suggested caption

> A privacy-first CV workflow: AI tailors an anonymized resume in the repo, then one local command reveals the real application outside the project.
