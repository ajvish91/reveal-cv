#!/usr/bin/env bash
# Backward-compatible wrapper — logic lives in cv_generation/private_cv.py (update-safe).
#
# Prefer:
#   .venv/bin/python -m cv_generation.private_cv setup    # once
#   .venv/bin/python -m cv_generation.private_cv apply <run_id>
#
# Or after setup:
#   ~/private/cv/cv apply <run_id>

set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
exec "$REPO/.venv/bin/python" -m cv_generation.private_cv apply "$@"
