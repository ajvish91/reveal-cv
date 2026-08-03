"""SQLite persistence for job postings (Phase B+)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "jobs.sqlite"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS job_postings (
            uuid TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'nav_arbeidsplassen',
            status TEXT,
            title TEXT,
            jobtitle TEXT,
            employer_name TEXT,
            employer_orgnr TEXT,
            municipal TEXT,
            county TEXT,
            application_url TEXT,
            link TEXT,
            published TEXT,
            expires TEXT,
            updated TEXT,
            description_text TEXT,
            raw_json TEXT,
            fetched_at TEXT NOT NULL,
            in_rogaland INTEGER NOT NULL DEFAULT 0,
            location_matched INTEGER NOT NULL DEFAULT 0,
            location_label TEXT,
            keyword_hits TEXT,
            feed_municipal TEXT,
            PRIMARY KEY (uuid, source)
        );
        CREATE INDEX IF NOT EXISTS idx_job_postings_rogaland ON job_postings (in_rogaland);
        CREATE INDEX IF NOT EXISTS idx_job_postings_county ON job_postings (county);
        CREATE INDEX IF NOT EXISTS idx_job_postings_fetched ON job_postings (fetched_at);

        CREATE TABLE IF NOT EXISTS job_scores (
            uuid TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'nav_arbeidsplassen',
            track TEXT NOT NULL,
            score_base REAL NOT NULL,
            boost_rogaland REAL NOT NULL DEFAULT 0,
            boost_tek REAL NOT NULL DEFAULT 0,
            score_total REAL NOT NULL,
            matched_keywords TEXT,
            matched_skills TEXT,
            tek_match_name TEXT,
            scored_at TEXT NOT NULL,
            PRIMARY KEY (uuid, source, track)
        );
        CREATE INDEX IF NOT EXISTS idx_job_scores_total ON job_scores (score_total DESC);
        CREATE INDEX IF NOT EXISTS idx_job_scores_track ON job_scores (track);

        CREATE TABLE IF NOT EXISTS applications (
            uuid TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'nav_arbeidsplassen',
            track TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'interested',
            notes TEXT,
            cover_letter_path TEXT,
            applied_at TEXT,
            follow_up_at TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (uuid, source, track)
        );
        CREATE INDEX IF NOT EXISTS idx_applications_status ON applications (status);
        CREATE INDEX IF NOT EXISTS idx_applications_track ON applications (track);

        CREATE TABLE IF NOT EXISTS ingest_state (
            state_key TEXT PRIMARY KEY,
            state_value TEXT,
            updated_at TEXT NOT NULL
        );
        """
    )
    _ensure_column(conn, "job_postings", "location_matched", "INTEGER NOT NULL DEFAULT 0")
    _ensure_column(conn, "job_postings", "location_label", "TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_job_postings_location_matched "
        "ON job_postings (location_matched)"
    )
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def upsert_job(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    keys = [
        "uuid",
        "source",
        "status",
        "title",
        "jobtitle",
        "employer_name",
        "employer_orgnr",
        "municipal",
        "county",
        "application_url",
        "link",
        "published",
        "expires",
        "updated",
        "description_text",
        "raw_json",
        "fetched_at",
        "in_rogaland",
        "location_matched",
        "location_label",
        "keyword_hits",
        "feed_municipal",
    ]
    for k in keys:
        if k not in row:
            if k in {"in_rogaland", "location_matched"}:
                row[k] = 0
            else:
                row[k] = None
    if row.get("raw_json") is not None and not isinstance(row["raw_json"], str):
        row["raw_json"] = json.dumps(row["raw_json"], ensure_ascii=False)

    # Search-card-only re-ingests must not wipe a previously fetched full description.
    existing = conn.execute(
        "SELECT description_text, raw_json FROM job_postings WHERE uuid = ? AND source = ?",
        (row["uuid"], row["source"]),
    ).fetchone()
    if existing is not None:
        new_desc = (row.get("description_text") or "").strip()
        old_desc = (existing["description_text"] or "").strip()
        if not new_desc and old_desc:
            row["description_text"] = existing["description_text"]
        if existing["raw_json"] and row.get("raw_json"):
            try:
                new_raw = (
                    json.loads(row["raw_json"])
                    if isinstance(row["raw_json"], str)
                    else row["raw_json"]
                )
                old_raw = (
                    json.loads(existing["raw_json"])
                    if isinstance(existing["raw_json"], str)
                    else existing["raw_json"]
                )
                if (
                    isinstance(new_raw, dict)
                    and isinstance(old_raw, dict)
                    and "detail" not in new_raw
                    and "detail" in old_raw
                ):
                    row["raw_json"] = existing["raw_json"]
            except (TypeError, json.JSONDecodeError, ValueError):
                pass

    cols = ", ".join(keys)
    placeholders = ", ".join(f":{k}" for k in keys)
    updates = ", ".join(f"{k} = excluded.{k}" for k in keys if k not in ("uuid", "source"))
    conn.execute(
        f"""
        INSERT INTO job_postings ({cols})
        VALUES ({placeholders})
        ON CONFLICT(uuid, source) DO UPDATE SET {updates}
        """,
        row,
    )


def upsert_score(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    keys = [
        "uuid",
        "source",
        "track",
        "score_base",
        "boost_rogaland",
        "boost_tek",
        "score_total",
        "matched_keywords",
        "matched_skills",
        "tek_match_name",
        "scored_at",
    ]
    for k in keys:
        if k not in row:
            row[k] = None
    cols = ", ".join(keys)
    placeholders = ", ".join(f":{k}" for k in keys)
    updates = ", ".join(f"{k} = excluded.{k}" for k in keys if k not in ("uuid", "source", "track"))
    conn.execute(
        f"""
        INSERT INTO job_scores ({cols})
        VALUES ({placeholders})
        ON CONFLICT(uuid, source, track) DO UPDATE SET {updates}
        """,
        row,
    )


def upsert_application(conn: sqlite3.Connection, row: dict[str, Any]) -> None:
    keys = [
        "uuid",
        "source",
        "track",
        "status",
        "notes",
        "cover_letter_path",
        "applied_at",
        "follow_up_at",
        "updated_at",
    ]
    for k in keys:
        if k not in row:
            row[k] = None
    cols = ", ".join(keys)
    placeholders = ", ".join(f":{k}" for k in keys)
    updates = ", ".join(f"{k} = excluded.{k}" for k in keys if k not in ("uuid", "source", "track"))
    conn.execute(
        f"""
        INSERT INTO applications ({cols})
        VALUES ({placeholders})
        ON CONFLICT(uuid, source, track) DO UPDATE SET {updates}
        """,
        row,
    )


def delete_application(conn: sqlite3.Connection, uuid: str, source: str, track: str) -> None:
    conn.execute(
        "DELETE FROM applications WHERE uuid = ? AND source = ? AND track = ?",
        (uuid, source, track),
    )


def get_state(conn: sqlite3.Connection, key: str) -> str | None:
    row = conn.execute(
        "SELECT state_value FROM ingest_state WHERE state_key = ?",
        (key,),
    ).fetchone()
    return None if row is None else row["state_value"]


def set_state(conn: sqlite3.Connection, key: str, value: str | None) -> None:
    conn.execute(
        """
        INSERT INTO ingest_state (state_key, state_value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(state_key) DO UPDATE SET
            state_value = excluded.state_value,
            updated_at = excluded.updated_at
        """,
        (key, value, utc_now_iso()),
    )
