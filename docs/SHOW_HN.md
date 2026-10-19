# Show HN draft

## Title options

- Show HN: Reveal CV - tailor your CV with AI without giving it your real name
- Show HN: A privacy-first CV generator that reveals your identity only on your machine
- Show HN: Open-source CV tailoring where the AI never sees your real contact details

## Post body

I built an open-source CV workflow for people who want AI help tailoring applications, but do not want to upload their real identity to a cloud resume service.

The core idea is simple:

- the repo and AI workflow use anonymized placeholders
- the real name, email, links, photo, and final PDFs live outside the project in `~/private/cv/`
- one local command reveals the final application on your own machine

So the workflow is not "nothing ever leaves your machine." If you use Cursor, Anthropic, or OpenAI, anonymized career content still goes to that provider. The privacy win is that the provider never needs your real identity layer or your final deanonymized files.

The project also includes a fictional demo candidate, so anyone can try it without API keys or personal data:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
.venv/bin/python scripts/run_demo.py --assemble
```

Today the repo has two parts:

- a privacy-first CV tailoring pipeline
- a Norway-first job-search module built around NAV

I am deliberately treating the Norway-specific parts as the first locale module rather than the whole product. The CV core works on any pasted job posting text.

I would especially love feedback on:

1. whether the privacy model is easy to understand
2. whether the Tailor -> Reveal workflow feels meaningfully different from existing CV SaaS tools
3. whether you would prefer this as a pure OSS workflow or eventually as a polished local app

## Short version for social reposts

I built an open-source CV generator for people who do not want to upload their real resume to a cloud service. The AI works on anonymized placeholders in the repo, and one local command reveals the real PDF on your machine.
