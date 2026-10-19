#!/usr/bin/env python3
"""
Refresh FINN application deadlines and inactivate expired listings.

Many FINN rows are ingested from search cards without a deadline; this pass
fetches detail pages so ``hide expired`` and SQL ACTIVE filters work.

  .venv/bin/python -m job_search.refresh_finn_deadlines
  .venv/bin/python -m job_search.refresh_finn_deadlines --limit 100 --mark-known-only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from job_search.deadline_utils import is_expired, row_expires
from job_search.finn_deadlines import (
    SOURCE,
    apply_expires_update,
    expires_and_status_from_finn_detail,
)
from job_search.finn_job_client import FinnJobSession
from job_search.job_db import DEFAULT_DB_PATH, connect, init_schema
from job_search.logging_config import configure_logging, get_logger, log_json_summary

log = get_logger("job_search.refresh_finn")


def mark_known_expired_inactive(conn) -> int:
    """Set status=INACTIVE for ACTIVE rows whose stored deadline is already past."""
    rows = conn.execute(
        """
        SELECT uuid, source, expires
        FROM job_postings
        WHERE (status IS NULL OR UPPER(status) = 'ACTIVE')
          AND expires IS NOT NULL
          AND TRIM(expires) != ''
        """
    ).fetchall()
    n = 0
    for row in rows:
        if not is_expired(row_expires(row)):
            continue
        conn.execute(
            "UPDATE job_postings SET status = 'INACTIVE' WHERE uuid = ? AND source = ?",
            (row["uuid"], row["source"]),
        )
        n += 1
    if n:
        conn.commit()
    return n


def refresh_one_finn_deadline(
    conn,
    finnkode: str,
    client: FinnJobSession | None = None,
) -> dict[str, Any]:
    """Fetch deadline for one FINN ad and update the DB. Used by detail API + CLI."""
    session = client or FinnJobSession(sleep_s=0)
    detail = session.fetch_deadline_only(finnkode, timeout=8, max_attempts=1)
    expires, status = expires_and_status_from_finn_detail(detail)
    apply_expires_update(
        conn,
        uuid=finnkode,
        expires=expires,
        status=status,
    )
    return {
        "uuid": finnkode,
        "expires": expires,
        "status": status,
        "listingExpired": bool(detail.get("listingExpired")),
    }


def refresh_missing_finn_deadlines(
    conn,
    client: FinnJobSession,
    *,
    limit: int,
) -> dict[str, Any]:
    """Fetch FINN deadline pages for ACTIVE rows missing ``expires``.

    Prefer high-scoring ads so explorer-visible jobs get fixed first.
    """
    rows = conn.execute(
        """
        SELECT j.uuid
        FROM job_postings j
        LEFT JOIN (
            SELECT uuid, source, MAX(score_total) AS score_total
            FROM job_scores
            GROUP BY uuid, source
        ) s ON s.uuid = j.uuid AND s.source = j.source
        WHERE j.source = ?
          AND (j.status IS NULL OR UPPER(j.status) = 'ACTIVE')
          AND (j.expires IS NULL OR TRIM(j.expires) = '')
        ORDER BY COALESCE(s.score_total, 0) DESC, j.fetched_at DESC
        LIMIT ?
        """,
        (SOURCE, int(limit)),
    ).fetchall()

    total = len(rows)
    if total:
        print(f"[job-search] refresh-finn-deadlines: fetching {total} detail pages", flush=True)
    refreshed = 0
    inactivated = 0
    errors = 0
    for idx, row in enumerate(rows, start=1):
        finnkode = str(row["uuid"])
        print(
            f"[job-search] refresh-finn-deadlines: {idx}/{total} fetching {finnkode}…",
            flush=True,
        )
        try:
            result = refresh_one_finn_deadline(conn, finnkode, client=client)
        except RuntimeError as exc:
            log.warning("skip refresh finnkode=%s: %s", finnkode, exc)
            errors += 1
            print(
                f"[job-search] refresh-finn-deadlines: {idx}/{total} "
                f"error on {finnkode}: {exc}",
                flush=True,
            )
            continue
        refreshed += 1
        if result["status"] == "INACTIVE":
            inactivated += 1
        print(
            f"[job-search] refresh-finn-deadlines: {idx}/{total} "
            f"{finnkode} → expires={result.get('expires')!r} status={result['status']} "
            f"(refreshed={refreshed} inactivated={inactivated} errors={errors})",
            flush=True,
        )
    return {
        "candidates": total,
        "refreshed": refreshed,
        "inactivated": inactivated,
        "errors": errors,
    }


def run(args: argparse.Namespace) -> int:
    configure_logging(console=True)
    db_path = Path(args.db).expanduser() if args.db else DEFAULT_DB_PATH
    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    if not args.mark_known_only:
        sleep_max = args.sleep_s_max if args.sleep_s_max is not None else args.sleep_s * 2.0
        print(
            "Note: FINN often throttles bulk detail fetches. Prefer small --limit "
            f"({args.limit}) and randomized sleep [{args.sleep_s}, {sleep_max}]s. "
            "For day-to-day ingest, use --mark-known-only (no HTTP).",
            flush=True,
        )

    conn = connect(db_path)
    init_schema(conn)
    try:
        marked = mark_known_expired_inactive(conn)
        refresh_summary: dict[str, Any] = {"candidates": 0, "refreshed": 0, "inactivated": 0, "errors": 0}
        if not args.mark_known_only:
            client = FinnJobSession(sleep_s=args.sleep_s, sleep_s_max=args.sleep_s_max)
            refresh_summary = refresh_missing_finn_deadlines(conn, client, limit=args.limit)
        summary = {
            "db": str(db_path),
            "marked_known_expired_inactive": marked,
            **refresh_summary,
        }
        log_json_summary(log, "FINN deadline refresh", summary)
        print(json.dumps(summary, indent=2))
    finally:
        conn.close()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Refresh FINN deadlines and inactivate expired listings. "
            "Avoid large --limit runs; FINN may throttle bulk requests."
        )
    )
    p.add_argument("--db", default="", help=f"SQLite path (default {DEFAULT_DB_PATH})")
    p.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max detail fetches for rows missing expires (default: 10; keep small)",
    )
    p.add_argument(
        "--sleep-s",
        type=float,
        default=2.0,
        help="Minimum pause between FINN HTTP requests (default: 2.0s; random up to --sleep-s-max)",
    )
    p.add_argument(
        "--sleep-s-max",
        type=float,
        default=None,
        help="Maximum pause between FINN requests (default: 2× --sleep-s)",
    )
    p.add_argument(
        "--mark-known-only",
        action="store_true",
        help="Only mark rows with a past stored deadline INACTIVE (no HTTP)",
    )
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
