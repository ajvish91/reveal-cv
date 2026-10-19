#!/usr/bin/env python3
"""
Backward-compatible wrapper for the generic agent pipeline runner.

Use `python -m cv_generation.run_agent_pipeline` for provider-neutral wording.
This module remains as a compatibility alias for existing scripts and docs.
"""
from __future__ import annotations

from cv_generation.run_agent_pipeline import main


if __name__ == "__main__":
    raise SystemExit(main())

