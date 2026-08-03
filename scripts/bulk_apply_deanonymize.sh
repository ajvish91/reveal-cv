#!/usr/bin/env bash
# Bulk-deanonymize multiple CV run folders (PII stays in ~/private/cv/).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PRIVATE_CV="${HOME}/private/cv/cv"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <run_id1> [run_id2 ...]" >&2
  echo "Example: $0 20260713T120000Z_Falkor_software-ai-engineer 20260713T070700Z_SimulaUiB_research-scientist" >&2
  exit 1
fi

if [[ -x "${PRIVATE_CV}" ]]; then
  exec "${PRIVATE_CV}" apply "$@"
fi

cd "${REPO_ROOT}"
exec .venv/bin/python -m cv_generation.private_cv apply "$@"
