#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/graphify ]]; then
  echo "error: .venv/bin/graphify not found; install graphifyy==0.9.35 into .venv" >&2
  exit 1
fi

exec .venv/bin/graphify update .
