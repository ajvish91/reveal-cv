#!/usr/bin/env bash
# Headless CV apply: prepare run folder + run agent pipeline (no Streamlit dashboard).
#
# Usage:
#   scripts/agent_apply_job.sh \
#     --job-file cv_generation/jobs/example.txt \
#     --company "Acme" \
#     --role "ML Engineer" \
#     [--provider anthropic|openai|cursor|manual] \
#     [--model MODEL_ID] \
#     [--apply-prompts "emphasize RAG experience"] \
#     [--language en|no] \
#     [--dry-run] [--no-pdf] [--overwrite]
#
# Environment: set ANTHROPIC_API_KEY, OPENAI_API_KEY, or CURSOR_API_KEY for the
# matching provider. Manual mode writes prompt/response files for external agents.
#
# See cv_generation/AGENT_INTEROP.md for the full contract and Claude workflow.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON=python3
fi

JOB_FILE=""
COMPANY=""
ROLE=""
PROVIDER="cursor"
MODEL=""
APPLY_PROMPTS=""
LANGUAGE="en"
DRY_RUN=""
NO_PDF=""
OVERWRITE=""
RUN_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --job-file) JOB_FILE="$2"; shift 2 ;;
    --company) COMPANY="$2"; shift 2 ;;
    --role) ROLE="$2"; shift 2 ;;
    --provider) PROVIDER="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --apply-prompts) APPLY_PROMPTS="$2"; shift 2 ;;
    --language) LANGUAGE="$2"; shift 2 ;;
    --run-dir) RUN_DIR="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    --no-pdf) NO_PDF=1; shift ;;
    --overwrite) OVERWRITE=1; shift ;;
    -h|--help)
      sed -n '2,18p' "$0"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$JOB_FILE" || -z "$COMPANY" || -z "$ROLE" ]]; then
  echo "Required: --job-file, --company, --role" >&2
  exit 1
fi

PREP=(
  "$PYTHON" -m cv_generation.run_cv_tailoring
  --job-file "$JOB_FILE"
  --company "$COMPANY"
  --role "$ROLE"
  --output-language "$LANGUAGE"
)
if [[ -n "$APPLY_PROMPTS" ]]; then
  PREP+=(--apply-prompts "$APPLY_PROMPTS")
fi
if [[ -n "$RUN_DIR" ]]; then
  PREP+=(--run-dir "$RUN_DIR" --force)
fi

echo "==> Preparing run folder"
RUN_DIR_OUT="$("${PREP[@]}")"
RUN_DIR_PATH="$(echo "$RUN_DIR_OUT" | head -n1)"
if [[ ! -d "$RUN_DIR_PATH" ]]; then
  echo "Expected run directory, got: $RUN_DIR_OUT" >&2
  exit 1
fi
echo "Run folder: $RUN_DIR_PATH"

PIPE=(
  "$PYTHON" -m cv_generation.run_agent_pipeline
  --run-dir "$RUN_DIR_PATH"
  --provider "$PROVIDER"
  --language "$LANGUAGE"
)
if [[ -n "$MODEL" ]]; then
  PIPE+=(--model "$MODEL")
fi
if [[ -n "$DRY_RUN" ]]; then
  PIPE+=(--dry-run)
fi
if [[ -n "$NO_PDF" ]]; then
  PIPE+=(--no-pdf)
fi
if [[ -n "$OVERWRITE" ]]; then
  PIPE+=(--overwrite)
fi

echo "==> Running agent pipeline (provider=$PROVIDER)"
"${PIPE[@]}"

echo "==> Done. Deanonymize locally:"
echo "    ~/private/cv/cv apply $(basename "$RUN_DIR_PATH")"
