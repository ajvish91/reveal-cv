# Agent instructions

## Scope

Work **only** inside this repository. Do not read or write files under `~/private/cv/` or other paths outside the project.

## Layout

| Folder | Contents |
|--------|----------|
| `shared/` | Demo `cv/*.md` (fictional); `cv_loader.py` prefers `~/private/cv/cv/` |
| `job_search/` | NAV ingest, scoring, dashboard |
| `cv_generation/demo/` | Committed fictional demo run (presentations) |
| `scripts/run_demo.py` | No-API demo driver |
| `cv_generation/` | Tailoring, PDF, `cv_runs/`, private CV CLI |

## Private CV data

| In repo | Outside repo (user only) |
|---------|---------------------------|
| `cv_generation/cv_identity_mapping.example.json` | `~/private/cv/cv_identity_mapping.json` |
| `cv_generation/private_cv.py`, `deanonymize_cvs.py` | `~/private/cv/deanonymized/` |
| Demo `shared/cv/`, `cv_generation/cv_runs/` (gitignored) | Real CV sources, mapping JSON, profile photo |

To debug private mapping or apply errors, tell the user which shell commands to run; do not open their private JSON.

See `cv_generation/CV_AUTOMATION.md` → “Deanonymize privately”.

## Supplementary application documents

When a posting requires more than a CV, add markdown to the run folder (see `application_artifacts.md` in each run):

| File | When |
|------|------|
| `cover_letter.md` | Industry roles; motivation/fit letter |
| `application_letter.md` | Academic calls asking for motivation or qualifications letter |
| `research_proposal.md` | Postdoc/researcher calls requiring a project plan |

Use CV placeholders (`MITCH EVANS`, etc.). `private_cv apply` deanonymizes every present file. Voice rules: `COVER_LETTER_VOICE` in `cv_style.py` (application letters follow the same style as cover letters).

## CV tailoring style

When generating or editing tailored CVs and cover letters, follow `cv_generation/cv_style.py` and `.cursor/rules/cv-tailoring-style.mdc`:

- **Profile:** two short plain paragraphs; no keyword wall.
- **Keywords:** mainly in experience bullets + Skills (four terms max in sidebar), not stuffed into Profile.
- **Chronology:** do not apply post-2023 buzzwords (agentic AI, coding agents, LLM fine-tuning, GenAI) to pre-2023 roles unless the source CV already does; use period-accurate terms for older work.
- **Emphasis:** optional `**bold**` / `*italic*` in Profile and bullets (sparingly); PDF renderer supports it.

## Cover letter voice

Use this prose style for **all** cover letters (see `cv_generation/cv_style.py` → `COVER_LETTER_VOICE`):

- **Tone:** clear, explanatory, calm. Academic but readable. Build each point in full sentences rather than punchy fragments. Open with a compelling link between the role and what matters to the candidate (mission, team, type of work), not generic enthusiasm.
- **Connectors:** prefer *since*, *when*, *however*, *at the same time*, *for example* to link ideas.
- **Avoid:** em-dashes; casual or marketing phrasing (*rhythm*, *get-it-done*, *from day one* as filler); colon-led slogan lists; bold in the body (only `**Re: Role title**` in the heading).
- **First person:** use *I* where it carries weight (motivation, key ownership, logistics). Mix in work-led sentences (*"Postdoctoral work focused on…"*, *"Completing the degree after… meant…"*) so the letter is not a wall of *I*. When asked to “tone down” something, **moderate** it; do not remove the point entirely or over-correct to impersonal prose.
- **Length:** four substantive body paragraphs plus a brief closing. Trim repetition, not whole arguments.
- **Fit without gap confessions:** map the role’s tasks to transferable skills already in the CV (e.g. agent setup, integrations, prototyping, enablement). Do **not** write “I have not used [tool]” unless the user asks for explicit disclosure. Do **not** invent production experience with tools absent from the source CV.
- **Ph.D. arc:** when relevant, connect doctoral self-direction (*explore, test, seek people who unblock progress*) with completing after a supervisor left midway, rather than listing independence as a separate industry trait.
- **Cloud platforms (Azure, AWS, etc.):** mention **once** in the CV (one dated experience bullet) and **once** in the cover letter. Frame as earlier production deployments, not a headline skill or current specialty; note ability to pick up new platform tooling when the work is connect/configure/adopt. Do **not** put cloud platforms in Profile or Skills as a main strength unless the user confirms up-to-date expertise.
- **Content:** Norwegian work permit / language / location only when the posting cares.
