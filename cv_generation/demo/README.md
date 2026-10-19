# Reveal CV demo run (fictional)

| Path | Description |
|------|-------------|
| [`northline_ml_engineer/`](northline_ml_engineer/) | Full sample workspace for Northline Labs × ML Engineer |
| [`seed/`](seed/) | Pre-written `*_output.json` files (no API keys) |

**Candidate:** ALEX RIVERA (`shared/cv/demo_only/`)  
**Job:** `cv_generation/jobs/demo_northline_ml_engineer.txt`

```bash
.venv/bin/python scripts/run_demo.py
.venv/bin/python scripts/run_demo.py --assemble
.venv/bin/python scripts/run_demo.py --pdf   # writes final_cv.pdf locally (gitignored)
```

See [`docs/DEMO.md`](../../docs/DEMO.md) for a presenter walkthrough and [`docs/DEMO_VIDEO_SCRIPT.md`](../../docs/DEMO_VIDEO_SCRIPT.md) for the 60-second public demo.

This demo showcases the portable CV-generation core. The Norway-specific NAV job-search module lives elsewhere in the repo and is optional.
