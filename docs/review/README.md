# Review pack (for another agent)

This folder is the handoff for a **codebase + conversation review**. It does not replace `AGENTS.md` or `README.md`.

| Document | Purpose |
|----------|---------|
| [AGENT_HANDOFF.md](AGENT_HANDOFF.md) | How to review: constraints, WIP, suggested questions |
| [FEATURES.md](FEATURES.md) | Feature inventory of the whole repo |

## Chat backups (local only)

Cursor transcripts for this project were copied on 2026-10-13 into:

- `review_pack/agent-transcripts/` — full `.jsonl` copies
- `review_pack/transcript_index.md` — dated index with first user message per chat

Those paths are **gitignored**. They can contain job titles, companies, and other application details. Do not commit or push them.

Refresh the backup:

```bash
.venv/bin/python scripts/backup_agent_exchanges.py
```

Cite chats as `[short title](<uuid>)` using the folder UUID (no `.jsonl`). Originals remain under Cursor’s project store.

## What is already on GitHub

Remote: `https://github.com/ajvish91/reveal-cv.git` (branch `main`). Uncommitted local work (Jobbnorge ingest, dashboard ingest UI, CV deanonymize tweaks) is **not** on that remote until someone commits and pushes.
