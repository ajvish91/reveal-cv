"""Shared helpers for job ingest scripts (NAV, FINN, …)."""
from __future__ import annotations

import re
from typing import Any

# Work-location municipal codes used in feed (uppercase, as returned by NAV).
ROGALAND_MUNICIPAL: frozenset[str] = frozenset(
    {
        "STAVANGER",
        "SANDNES",
        "HAUGESUND",
        "EIGERSUND",
        "SOKNDAL",
        "BJERKREIM",
        "HÅ",
        "KLEPP",
        "TIME",
        "GJESDAL",
        "SOLA",
        "RANDABERG",
        "STRAND",
        "HJELMELAND",
        "SULDAL",
        "SAUDA",
        "KVITSØY",
        "TYSVÆR",
        "UTSIRA",
        "BOKN",
        "VINDAFJORD",
        "ETNE",
    }
)
ROGALAND_COUNTY = "ROGALAND"


def strip_html(html: str) -> str:
    t = re.sub(r"(?is)<script.*?>.*?</script>", " ", html or "")
    t = re.sub(r"(?is)<style.*?>.*?</style>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


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
