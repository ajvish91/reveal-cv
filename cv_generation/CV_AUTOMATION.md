# CV Automation Workflow (Subagent-Based)

This setup keeps your process ATS-safe, removes Canva-style manual edits for each role, and keeps the identity layer outside the repo until the final local reveal.

The tailoring core in `cv_generation/` is designed to be portable across locales. The repository currently includes Norwegian localization and a Norway-first job-search stack, but the CV workflow itself operates on any job posting text you save as a `.txt` file.

## Two tracks: industry (corporate) vs academic

| | **Industry (corporate)** | **Academic (research)** |
|---|--------------------------|-------------------------|
| Source | `shared/cv/industry.md` | `shared/cv/academic.md` |
| Run copy | `cv_industry_source.md` | `cv_academic_source.md` |
| Selected by | `track_selector` → `industry` | `track_selector` → `academic` |
| PDF title | `# Industry CV` | `# Academic CV` |
| Contact extras | GitHub, LinkedIn, email, phone, location, work permit | Above + Google Scholar, ORCID |
| Sidebar page 1 | Contact + skills (spread when tall) | Contact + skills + **languages** (compact) |
| Sidebar page 2 | Languages + hobbies (canvas) | Hobbies only (if any) |
| Deanonymize URLs | `_github_url`, `_linkedin_url` | Same + optional `_google_scholar_url`, `_orcid_url` |

Pipeline steps (`run_cv_tailoring`, `run_agent_pipeline`, `private_cv apply`) are **the same** for both tracks. Track-specific behavior is driven by:

1. Which source file the selector chooses (`03_track_selector_output.json`).
2. Markdown H1 title (`Industry CV` vs `Academic CV`) for PDF sidebar rules in `cv_pdf_renderer.py`.
3. Contact lines present in that track’s source (industry has no Scholar/ORCID placeholders).

Corporate/industry runs are **not** changed when you edit academic-only contact fields or academic sidebar layout.

## Recommended tweaks to your proposal

- Keep Canva only for networking/event CVs; use markdown for all ATS submissions.
- Preserve one factual source CV per track (`shared/cv/industry.md`, `shared/cv/academic.md`).
- Tailor by prioritization and phrasing, not by inventing new claims.
- Add a QA gate: if ATS checker score is low, do not export PDF yet.

## Subagents in this repo

Defined in `cv_generation/cv_subagents.py`:

1. `jd_parser` -> extracts role needs from job posting.
2. `keyword_ranker` -> prioritizes must-have terms and computes overlap.
3. `track_selector` -> picks `industry` vs `academic`.
4. `bullet_tailor` -> rewrites bullets truthfully for relevance.
5. `ats_checker` -> checks parseability and keyword coverage.
6. `assembler` -> creates final markdown artifact and metadata.

## How to run

1. Save a job posting as text:
   - Example: `cv_generation/jobs/acme_ml_engineer.txt`
2. Generate a run workspace (from repo root):

```bash
.venv/bin/python -m cv_generation.run_cv_tailoring \
  --job-file "cv_generation/jobs/acme_ml_engineer.txt" --company "Acme" --role "ML Engineer"
```

3. The script creates `cv_generation/cv_runs/<timestamp>_<CompanySlug>_<role-slug>/` with:
   - `job_posting.txt`
   - `subagent_specs.md`
   - `application_artifacts.md` (which supplementary docs to create; deanonymize paths)
   - per-agent `*_task.json` and output placeholders
   - source CV markdown copies for both tracks

4. Execute each subagent task in order and fill `*_output.json`.
5. Use assembler output as the final CV markdown, then export to PDF/docx.
6. Supplementary markdown is auto-generated when flagged: `run_agent_pipeline` writes `cover_letter.md` (and PDF) for industry postings after `final_cv.md`. Create `application_letter.md` / `research_proposal.md` manually when required for academic calls (automation planned).
7. Deanonymize privately: `~/private/cv/cv apply <run_id>` (all present artifacts).

## Fully automated run with agent providers

If you want one command that runs all steps and builds `final_cv.md`, use the
provider-neutral runner:

1. Install the package for your chosen provider:

```bash
.venv/bin/pip install cursor-sdk
# or:
.venv/bin/pip install anthropic
.venv/bin/pip install openai
```

2. Set the matching API key:

```bash
export CURSOR_API_KEY="cursor_..."
# or:
export ANTHROPIC_API_KEY="..."
export OPENAI_API_KEY="..."
```

3. Run automation:

```bash
.venv/bin/python -m cv_generation.run_agent_pipeline \
  --run-dir "cv_generation/cv_runs/<your_run_folder>" \
  --provider anthropic
```

Optional flags:
- `--overwrite` to regenerate existing output JSON files
- `--refresh-tasks` to sync task JSON schemas/prompts and `cv_*_source.md` from `shared/cv/`
- `--allow-fewer-bullets` to permit the bullet_tailor agent to return fewer bullets per role (default: pad from source)
- `--model <provider-model-id>` to choose model
- `--dry-run` to preview prompts only
- `--render-only` to rebuild PDF from existing `final_cv.md`
- `--profile-photo PATH` to use a private headshot when rendering PDF (see below)

After step 6 assembles `final_cv.md`, the pipeline runs optional step **07_cover_letter**
when `application_artifacts.md` / `detect_supplementary_artifacts()` flags `cover_letter.md`
for an **industry** track. It writes `cover_letter.md` and renders `cover_letter.pdf`
(plain layout). Skips when the file already exists unless `--overwrite`. Academic
`application_letter.md` / `research_proposal.md` are not auto-generated yet.

The old module name `cv_generation.generate_cv_with_cursor` still works as a
compatibility alias, but `run_agent_pipeline` is the preferred entry point.

## Agent-portable contract and manual flow

See **`cv_generation/AGENT_INTEROP.md`** for the full compatibility guide (Claude,
OpenAI, manual bridge, dashboard vs headless). Summary:

Every run folder is a portable contract:

- `*_task.json` files are the machine-readable prompts/contracts
- `*_output.json` files are the normalized responses
- `agent_contract.json` records the contract version and step order
- deterministic Python code assembles `final_cv.md` from structured outputs

For external agent UIs such as Claude Desktop or Codex, use the generic CLI:

```bash
.venv/bin/python -m cv_generation.agent_cli show-contract
.venv/bin/python -m cv_generation.agent_cli build-step-prompt \
  --run-dir "cv_generation/cv_runs/<run_id>" \
  --step 01_jd_parser_output.json
```

Or use the built-in manual bridge:

```bash
.venv/bin/python -m cv_generation.agent_cli run-step \
  --run-dir "cv_generation/cv_runs/<run_id>" \
  --step 01_jd_parser_output.json \
  --provider manual
```

That writes a `<step>_prompt.txt` file plus the expected
`<step>_output.manual.json` response path. Paste the prompt into your preferred
agent, save strict JSON to the manual output file, then continue.

## Preservation rules (deterministic assembly)

After `bullet_tailor`, `cv_assemble.py` merges agent output into the source CV template:

- Every experience role from the source is kept (same order).
- **Profile and experience bullets default to `shared/cv/industry.md`** (or the synced `cv_*_source.md`). Agent rewrites apply only with `--apply-tailored-bullets`.
- Bullet count per role is never reduced unless `--allow-fewer-bullets` is set; missing tailored bullets are restored from source.
- Non-experience sections (Name, Date of birth, Contact, Education, Publications, Hobbies, etc.) are copied from the source unchanged.
- **`## Role` (PDF designation)** is generated from the job’s `role_title` for **industry** CVs only (`01_jd_parser_output.json` or `job_posting.txt`), uppercased (e.g. `ML/AI Engineer` → `ML/AI ENGINEER`). Academic CVs omit this section.
- `tailored_cv.md` is written for the ATS checker; `final_cv.md` is built programmatically (step 6 does not use an LLM to rewrite markdown).

## Deanonymize privately (outside this repo)

Generated CVs use anonymized placeholders. **Real PII lives only in `~/private/cv/`** — not in this git repo.

Agents for this project are configured to stay inside the repo (see `AGENTS.md`
and `.cursor/rules/project-boundary.mdc`). They must not read `~/private/cv/`.
You run `~/private/cv/cv` locally; paste error output into chat if you need
help debugging.

| Location | What |
|----------|------|
| Repo | `cv_generation/private_cv.py`, `cv_generation/cv_identity_mapping.example.json` (template keys only) |
| `~/private/cv/cv_identity_mapping.json` | **Your** replacements (edit this file only) |
| `~/private/cv/config.env` | Paths (project dir, output dir, photo) |
| `~/private/cv/deanonymized/<run>/` | Application-ready markdown + PDF (folder name includes company when metadata is available) |

You do **not** copy shell scripts into `~/private/cv/` when the pipeline changes — run `cv_generation/private_cv.py` from the repo (or the `~/private/cv/cv` shortcut created by setup). `CV_PROJECT_DIR` in config should point at the **repository root** (not `cv_generation/`).

### One-time setup

```bash
.venv/bin/python -m cv_generation.private_cv setup
.venv/bin/python -m cv_generation.private_cv edit          # fill ~/private/cv/cv_identity_mapping.json
```

### After each CV generation run

```bash
.venv/bin/python -m cv_generation.private_cv apply 20260528T113852Z_ml-ai-engineer
# or: ~/private/cv/cv apply 20260528T113852Z_ml-ai-engineer
# Legacy cv_runs/ ids without Company still apply; deanonymized output is enriched, e.g.:
#   ~/private/cv/deanonymized/20260528T113852Z_PianoSoftwareNorway_ml-ai-engineer/

# Bulk (multiple run folder basenames from cv_runs/):
.venv/bin/python -m cv_generation.private_cv apply run_id1 run_id2
~/private/cv/cv apply run_id1 run_id2
scripts/bulk_apply_deanonymize.sh run_id1 run_id2
```

| Command | Purpose |
|---------|---------|
| `private_cv apply <run> [<run> …]` | Deanonymize `final_cv.md` + supplementary docs when present + PDF; output folder includes company when run metadata has it (legacy repo run ids without company are enriched on output) |
| `private_cv apply --md-only <run>` | Markdown only |
| `private_cv apply --dry-run <run>` | Preview replacements |
| `private_cv pdf ~/private/cv/deanonymized/<run>/final_cv.md` | Re-render PDF after hand-edits |
| `private_cv audit <run>` | Which mapping keys match / are missing |
| `private_cv sync` or `~/private/cv/sync` | Merge new keys from repo template (never overwrites your values) |
| `private_cv all-runs` | Process every run under `cv_generation/cv_runs/` |

When the repo layout or template changes:

```bash
cd ~/private/cv
./cv refresh    # after renovation: updates config, shortcuts, and new mapping keys
./cv edit       # fill only new placeholders
```

For template-only updates (no path changes):

```bash
./sync          # adds new keys; keeps your existing values
```

`./sync` reads `cv_identity_mapping.example.json` from the project (via `CV_PROJECT_DIR` in `config.env`). It never overwrites keys you already have.

**Degree titles in mapping:** use partial keys `M.Sc., Computing` and `B.Eng.` (not `### M.Sc., Computing`). Replacing the whole `### …` line often removes master’s/bachelor’s from the PDF. After `./cv apply`, open the deanonymized PDF on **page 2** for the EDUCATION section.

Do not submit `cv_generation/cv_runs/*/final_cv.pdf` from the project.

### Supplementary application documents

Beyond `final_cv.md`, create markdown in the run folder when the posting requires it. Each new run includes `application_artifacts.md` (heuristic checklist from the job text).

| File | Typical use | PDF layout |
|------|-------------|------------|
| `cover_letter.md` | Industry / corporate applications | Plain one-column |
| `application_letter.md` | Academic motivation / qualifications letter | Plain one-column |
| `research_proposal.md` | Postdoc / researcher project plan | Plain one-column |

Use the same anonymized placeholders as the CV (`MITCH EVANS`, `master_cv@gmail.com`, etc.). Prefer **`MITCH EVANS`** (all caps) for the applicant name so `cv_identity_mapping.json` keys match; title-case aliases are expanded automatically at deanonymize time.

`private_cv apply <run>` processes every file above that exists in the run folder (non-strict deanonymize, then plain PDF). Norwegian `*_no.md` variants are handled when present.

Re-render a single deanonymized doc after hand-edits:

```bash
.venv/bin/python -m cv_generation.render_cv_pdf \
  ~/private/cv/deanonymized/<run_id>/research_proposal.md --plain
```

`private_cv audit <run>` reports mapping coverage for the CV and any supplementary files in the run.

### Profile photo

`~/private/cv/profile_photo.jpg`, or `CV_PROFILE_PHOTO` / `_profile_photo_path` in your mapping JSON.

### Profile URLs (GitHub, LinkedIn, Google Scholar, ORCID)

Template CVs use placeholder URLs. In `~/private/cv/cv_identity_mapping.json` set your real URLs once:

```json
"_github_url": "https://github.com/yourusername",
"_linkedin_url": "https://www.linkedin.com/in/your-profile",
"_google_scholar_url": "https://scholar.google.com/citations?user=YOUR_ID",
"_orcid_url": "https://orcid.org/0000-0000-0000-0000"
```

`./cv apply` replaces both the bare URLs and the labeled contact lines (`GitHub:`, `LinkedIn:`, `Google Scholar:`, `ORCID:`). Run `./cv sync` first if those `_…_url` keys are missing from your private mapping file.

## ATS check on PDF (text extraction)

Markdown ATS checks do not reflect what recruiters' systems read from your styled PDF. After private render:

```bash
.venv/bin/python -m cv_generation.ats_check_pdf \
  --pdf ~/private/cv/deanonymized/<run_id>/final_cv.pdf \
  --run-dir cv_generation/cv_runs/<run_id>
```

Writes `ats_pdf_report.json` with extracted character count, must-have keyword coverage in the PDF text layer, weighted ATS score, and format warnings (column order, missing URLs, etc.).

## Tailoring style

Shared constants: `cv_generation/cv_style.py` (also injected into new run task JSON via `run_cv_tailoring`).

### Profile

- **Two short paragraphs**, plain language, human-readable first.
- Avoid jargon walls and keyword stuffing in Profile.
- Role-specific ATS terms belong mainly in **experience bullets** and **Skills** (at most four semicolon-separated terms in the sidebar).

### Skills

- Keep the sidebar to **four role-relevant terms** from the source CV (semicolon-separated).
- Automated assembly ranks source skills against JD keywords and trims to four; manual edits should follow the same cap.
- Do not use Skills as a keyword laundry list; weave additional terms into experience bullets.

### Experience bullets

- Truthful rewrites only; preserve all roles and bullet counts unless `--allow-fewer-bullets`.
- Weave must-have terms into natural sentences (e.g. data pipelines, observability, CI/CD, cloud infrastructure).
- Optional inline markdown emphasis for PDF scanability (see below).

### Cover letter

- Lead with strengths, role fit, and ability to learn quickly.
- Do not list tools the candidate has not used; avoid overly defensive gap statements.
- Reuse the candidate’s preferred tone (calm/structured, curious, collaborative; Ph.D. resilience when relevant).

### Inline emphasis (markdown → PDF)

CV markdown may use lightweight inline markers in **Profile** and **experience bullets**:

| Markdown | PDF |
|----------|-----|
| `**phrase**` | bold |
| `*phrase*` | italic |

- Implemented in `cv_pdf_renderer.markdown_inline_to_reportlab` (Profile + main-column bullets).
- **Do not** use in Contact, Skills, Languages, Education, publications, or role headers.
- Use sparingly: **0–1 emphasized phrase per bullet**; Profile mostly unbolded.
- ATS parsers still see the words; emphasis helps human readers on the styled PDF.

Example bullet:

```markdown
- Built **Python data pipelines** for document workflows with batch processing, clearer **observability**, and stronger data control.
```

Regenerate PDF after emphasis edits:

```bash
.venv/bin/python -m cv_generation.run_agent_pipeline \
  --run-dir "cv_generation/cv_runs/<run>" --render-only
```

## Suggested quality guardrails

- No fabricated metrics, tools, dates, or titles.
- Keep one-column plain layout and standard section headers.
- Ensure at least 70% must-have term coverage (contextual usage only).
- Keep summary short and role-specific; avoid keyword stuffing in Profile.
- Prefer contextual keywords in experience bullets over dense Profile jargon.

## Norwegian B1 localization (optional first locale)

English artifacts remain canonical for ATS checks and deanonymize mapping keys. When a posting or personal goal calls for a Norwegian CV, run a **post-tailoring localization pass** after `final_cv.md` exists.

Think of this as the first locale module, not a separate product. The same workflow can support other locales later by swapping the language-specific prompt and label rules while keeping the anonymized tailoring and private reveal steps unchanged.

Style rules: `cv_generation/cv_style.py` → `NORWEGIAN_B1_CV_VOICE`, `NORWEGIAN_B1_COVER_LETTER_VOICE`, `SECTION_LABELS_NO`.

Reference prose samples (tone only): `cv_generation/reference/norwegian_b1_writing_samples.md` (Norwegian), `cv_generation/reference/english_writing_samples.md` (English letters).

Optional role context (use when relevant): `cv_generation/reference/forwardmedia_boston_context.md` (ForwardMedia / Democracy base postdoc at University of Boston).

### Commands

After a normal English run:

```bash
.venv/bin/python -m cv_generation.run_agent_pipeline \
  --run-dir "cv_generation/cv_runs/<run_id>" \
  --localize-only --language no
```

Or localize during a full regenerate:

```bash
.venv/bin/python -m cv_generation.run_agent_pipeline \
  --run-dir "cv_generation/cv_runs/<run_id>" \
  --language no
```

Standalone module:

```bash
.venv/bin/python -m cv_generation.cv_norwegian \
  --run-dir "cv_generation/cv_runs/<run_id>" \
  --artifact both
```

Requires the API key for the chosen provider, for example `CURSOR_API_KEY`,
`ANTHROPIC_API_KEY`, or `OPENAI_API_KEY`.

### Output files

| English | Norwegian |
|---------|-------------|
| `final_cv.md` | `final_cv_no.md`, `final_cv_no.pdf` |
| `cover_letter.md` | `cover_letter_no.md`, `cover_letter_no.pdf` |

`application_letter.md` and `research_proposal.md` are English-only today (no `_no` localization pass).

`private_cv apply <run>` deanonymizes and renders `*_no.md` when those files exist in the run folder (same mapping JSON as English).

**Note:** Norwegian `_no` CVs use Norwegian contact labels (`E-post`, `Telefon`, `Sted`) and Norwegian dates (`mars 2026 – nå`). Work permit appears as plain text at the end of the contact sidebar (no icon). Education year ranges use an en-dash (`2022 – 2025`); the PDF parser accepts both `-` and `–`. For `private_cv apply` on `_no` files, add Norwegian mapping keys (e.g. `Gyldig norsk arbeidstillatelse`, `15. mars 1992`) to your private JSON if needed.

Scaffold new runs with language hint in task JSON:

```bash
.venv/bin/python -m cv_generation.run_cv_tailoring \
  --job-file "cv_generation/jobs/example.txt" \
  --output-language no
```

Localization is still triggered by `run_agent_pipeline --language no` (or `--localize-only`).

