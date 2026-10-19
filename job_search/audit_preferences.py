#!/usr/bin/env python3
"""
Collect preference labels from Skip/Reject vs positive applications.

Does not change scoring. Writes a feature snapshot under job_search/data/.

  .venv/bin/python -m job_search.audit_preferences
  .venv/bin/python -m job_search.audit_preferences --track industry
  .venv/bin/python -m job_search.audit_preferences --json --print-limit 30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from job_search.job_db import DEFAULT_DB_PATH, connect, init_schema
from job_search.logging_config import configure_logging, get_logger, log_json_summary
from job_search.preference_collect import collect_and_save

log = get_logger("job_search.audit_preferences")


def _print_term_block(label: str, rows: list[dict], *, limit: int) -> None:
    if not rows or limit <= 0:
        return
    print(f"\n--- {label} (top {min(limit, len(rows))}) ---")
    for row in rows[:limit]:
        print(
            f"  contrast={row['contrast']:4.0f}  "
            f"neg={row['neg']:3d} pos={row['pos']:3d}  {row['term']}"
        )


def _print_human(collection: dict, *, print_limit: int, out_path: Path) -> None:
    counts = collection.get("label_counts") or {}
    print(f"\n=== Preference label collection (track={collection.get('track')}) ===")
    print(
        f"negative={counts.get('negative', 0)}  "
        f"positive={counts.get('positive', 0)}  "
        f"ignored={counts.get('ignored', 0)}  "
        f"total={counts.get('total_labeled', 0)}"
    )
    status = collection.get("status_counts") or {}
    if status:
        print("status_counts:", ", ".join(f"{k}={v}" for k, v in status.items()))
    print(f"wrote {out_path}")

    titles = collection.get("title_stems") or {}
    employers = collection.get("employers") or {}
    matched = collection.get("matched_terms") or {}
    _print_term_block("title stems (negative-leaning)", titles.get("negative") or [], limit=print_limit)
    _print_term_block("title stems (positive-leaning)", titles.get("positive") or [], limit=print_limit)
    _print_term_block("employers (negative-leaning)", employers.get("negative") or [], limit=print_limit)
    _print_term_block("employers (positive-leaning)", employers.get("positive") or [], limit=print_limit)
    _print_term_block("matched CV terms (negative-leaning)", matched.get("negative") or [], limit=print_limit)
    _print_term_block("matched CV terms (positive-leaning)", matched.get("positive") or [], limit=print_limit)

    examples = collection.get("examples") or {}
    neg_ex = examples.get("negative") or []
    if neg_ex and print_limit > 0:
        print(f"\n--- negative examples (showing {min(print_limit, len(neg_ex))}) ---")
        for item in neg_ex[:print_limit]:
            print(
                f"  [{item.get('status')}] {item.get('title')} — {item.get('employer_name')}"
            )


def run(args: argparse.Namespace) -> int:
    configure_logging(console=True)
    db_path = Path(args.db).expanduser() if args.db else DEFAULT_DB_PATH
    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = connect(db_path)
    init_schema(conn)
    try:
        track = None if args.track == "all" else args.track
        out_path = Path(args.out).expanduser() if args.out else None
        collection, written = collect_and_save(
            conn,
            track=track,
            path=out_path,
            example_limit=max(0, args.print_limit),
            term_limit=max(1, args.term_limit),
            min_neg=max(1, args.min_count),
            min_pos=max(1, args.min_count),
        )
        counts = collection.get("label_counts") or {}
        log_json_summary(
            log,
            "preference collection",
            {
                "track": collection.get("track"),
                "negative": counts.get("negative", 0),
                "positive": counts.get("positive", 0),
                "ignored": counts.get("ignored", 0),
                "path": str(written),
            },
        )
        if args.json:
            print(json.dumps(collection, indent=2, ensure_ascii=False))
        else:
            _print_human(collection, print_limit=args.print_limit, out_path=written)
    finally:
        conn.close()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Collect Skip/Reject preference labels (no scoring changes)"
    )
    p.add_argument("--db", default="", help=f"SQLite path (default {DEFAULT_DB_PATH})")
    p.add_argument(
        "--track",
        choices=("industry", "academic", "all"),
        default="all",
        help="Limit to one CV track (default: all)",
    )
    p.add_argument(
        "--out",
        default="",
        help="Output JSON path (default: job_search/data/preference_features[_track].json)",
    )
    p.add_argument("--print-limit", type=int, default=20, help="Rows to show per section")
    p.add_argument("--term-limit", type=int, default=40, help="Max contrast terms stored per list")
    p.add_argument(
        "--min-count",
        type=int,
        default=1,
        help="Minimum label count for a term to appear in contrast lists",
    )
    p.add_argument("--json", action="store_true", help="Print full JSON snapshot")
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
