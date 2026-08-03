"""Shared helpers for job ingest scripts (NAV, FINN, …)."""
from __future__ import annotations

from typing import Any


def mark_stale_jobs_inactive(
    conn: Any,
    *,
    source: str,
    fetched_at: str,
    seen_uuids: set[str],
) -> int:
    """Mark ACTIVE rows for *source* not seen in the current ingest run as INACTIVE."""
    conn.execute("DROP TABLE IF EXISTS current_ingest_seen")
    conn.execute("CREATE TEMP TABLE current_ingest_seen (uuid TEXT PRIMARY KEY)")
    if seen_uuids:
        conn.executemany(
            "INSERT OR IGNORE INTO current_ingest_seen (uuid) VALUES (?)",
            [(uuid,) for uuid in seen_uuids],
        )
    cur = conn.execute(
        """
        UPDATE job_postings
        SET status = 'INACTIVE',
            fetched_at = ?
        WHERE source = ?
          AND UPPER(COALESCE(status, 'ACTIVE')) = 'ACTIVE'
          AND fetched_at < ?
          AND NOT EXISTS (
              SELECT 1 FROM current_ingest_seen s WHERE s.uuid = job_postings.uuid
          )
        """,
        (fetched_at, source, fetched_at),
    )
    return cur.rowcount
