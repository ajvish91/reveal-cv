#!/usr/bin/env python3
"""Mark cross-source duplicate job postings INACTIVE.

The same ad syndicated across NAV / FINN / Jobbnorge (same normalized employer +
title) is kept once, preferring NAV, then Jobbnorge, then FINN. Multiple ads from
a single source are left untouched.

  .venv/bin/python -m job_search.dedupe_jobs
  .venv/bin/python -m job_search.dedupe_jobs --db job_search/data/jobs.sqlite
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import argparse
import json

from job_search.job_db import DEFAULT_DB_PATH, connect, init_schema
from job_search.job_dedup import mark_cross_source_duplicates_inactive
from job_search.logging_config import configure_logging, get_logger, log_json_summary

log = get_logger("job_search.dedupe")


def run(args: argparse.Namespace) -> int:
    configure_logging(console=True)
    db_path = Path(args.db).expanduser() if args.db else DEFAULT_DB_PATH
    conn = connect(db_path)
    init_schema(conn)
    try:
        marked = mark_cross_source_duplicates_inactive(conn)
    finally:
        conn.close()
    summary = {"db": str(db_path), "marked_inactive": marked}
    log.info("dedupe done marked_inactive=%d", marked)
    log_json_summary(log, "dedupe summary", summary)
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Mark cross-source duplicate postings INACTIVE")
    p.add_argument("--db", default="", help=f"SQLite path (default {DEFAULT_DB_PATH})")
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
