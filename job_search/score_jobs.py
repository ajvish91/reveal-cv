#!/usr/bin/env python3
"""
Phase C: Score job_postings against CV profiles with Rogaland + TEK Norge (Rogaland) boosts.

Reads merged keywords/skills from cv/*.md and optional TEK member CSV from fetch_tek_rogaland_members.py.

  .venv/bin/python -m job_search.score_jobs
  .venv/bin/python -m job_search.score_jobs --track industry --print-top 20
  .venv/bin/python -m job_search.score_jobs --no-tek        # disable TEK member boost
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import argparse
import csv
import difflib
import json
import re
import sqlite3
from pathlib import Path

from shared.cv_loader import JobProfile, load_default_profiles
from job_search.job_db import DEFAULT_DB_PATH, connect, init_schema, upsert_score, utc_now_iso
from job_search.job_filters import (
    ACADEMIC_ROLE_TITLE_TERMS,
    haystack_for_filter,
    matches_academic_research_employer,
    matches_any_include_term,
    matching_terms,
)
from job_search.location_preferences import match_preferred_location
from job_search.logging_config import configure_logging, get_logger, log_json_summary

log = get_logger("job_search.score")

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_TEK_CSV = PROJECT_ROOT / "teknorge_medlemmer_rogaland.csv"

BOOST_LOCATION_PREFERRED = 5.0
BOOST_TEK = 25.0
BOOST_UNIVERSITY_ACADEMIC = 12.0
BOOST_ACADEMIC_TITLE = 8.0
FUZZY_RATIO_OK = 0.88
SUBSTRING_MIN_LEN = 8


def norm_company(name: str) -> str:
    s = (name or "").strip().casefold()
    if not s:
        return ""
    for suffix in (
        " as",
        " asa",
        " ans",
        " da",
        " norsk avdeling av utenlandsk foretak",
        " norge",
        " norway",
    ):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    s = re.sub(r"[^a-z0-9æøå]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_tek_by_norm(csv_path: Path | None) -> dict[str, str]:
    """Map normalized company name -> display name from CSV."""
    if csv_path is None or not csv_path.is_file():
        return {}
    out: dict[str, str] = {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw = (row.get("company_name") or "").strip()
            if not raw:
                continue
            key = norm_company(raw)
            if key and key not in out:
                out[key] = raw
    return out


def find_tek_match(employer_name: str | None, tek_by_norm: dict[str, str]) -> str | None:
    if not employer_name or not tek_by_norm:
        return None
    n = norm_company(employer_name)
    if not n or len(n) < 2:
        return None
    if n in tek_by_norm:
        return tek_by_norm[n]
    best_display: str | None = None
    best_r = 0.0
    for tnorm, display in tek_by_norm.items():
        if len(tnorm) < 3:
            continue
        r = difflib.SequenceMatcher(None, n, tnorm).ratio()
        if r > best_r:
            best_r = r
            best_display = display
    if best_r >= FUZZY_RATIO_OK and best_display:
        return best_display
    for tnorm, display in tek_by_norm.items():
        if len(n) >= SUBSTRING_MIN_LEN and len(tnorm) >= SUBSTRING_MIN_LEN and (n in tnorm or tnorm in n):
            return display
    return None


def haystack_for_job(row: sqlite3.Row) -> str:
    return haystack_for_filter(
        row["title"],
        row["jobtitle"],
        row["description_text"],
        row["employer_name"],
    )


def score_profile(
    profile: JobProfile,
    row: sqlite3.Row,
    tek_by_norm: dict[str, str],
) -> dict:
    hay = haystack_for_job(row)
    kw = profile.keywords
    sk = profile.skills

    matched_kw = matching_terms(hay, kw)
    matched_sk = matching_terms(hay, sk)

    n_kw, n_sk = len(kw), len(sk)
    if n_kw == 0 and n_sk == 0:
        base = 0.0
    elif n_kw == 0:
        base = 100.0 * len(matched_sk) / n_sk
    elif n_sk == 0:
        base = 100.0 * len(matched_kw) / n_kw
    else:
        base = 50.0 * (len(matched_kw) / n_kw) + 50.0 * (len(matched_sk) / n_sk)

    location_match = match_preferred_location(
        profile.locations_preferred,
        municipal=row["municipal"],
        county=row["county"],
        feed_municipal=row["feed_municipal"],
    )
    boost_location = BOOST_LOCATION_PREFERRED if location_match.matched else 0.0

    tek_name = find_tek_match(row["employer_name"], tek_by_norm)
    boost_t = BOOST_TEK if tek_name else 0.0

    boost_academic = 0.0
    if profile.track == "academic":
        title_hay = haystack_for_filter(row["title"], row["jobtitle"], None, None)
        if matches_academic_research_employer(row["employer_name"]):
            boost_academic += BOOST_UNIVERSITY_ACADEMIC
        if matches_any_include_term(title_hay, ACADEMIC_ROLE_TITLE_TERMS):
            boost_academic += BOOST_ACADEMIC_TITLE

    total = base + boost_location + boost_t + boost_academic

    return {
        "score_base": round(base, 3),
        "boost_rogaland": boost_location,
        "boost_tek": boost_t,
        "score_total": round(total, 3),
        "matched_keywords": ", ".join(matched_kw) if matched_kw else None,
        "matched_skills": ", ".join(matched_sk) if matched_sk else None,
        "tek_match_name": tek_name,
    }


def run(args: argparse.Namespace) -> int:
    configure_logging(console=True)
    if getattr(args, "no_tek", False):
        tek_by_norm = {}
    else:
        tek_path = Path(args.tek_csv).expanduser()
        tek_by_norm = load_tek_by_norm(tek_path)
        if not tek_by_norm:
            print(f"Note: TEK CSV missing or empty ({tek_path}); TEK boost skipped.", file=sys.stderr)

    profiles = load_default_profiles()
    if not profiles:
        print("No CV profiles in cv/; cannot score.", file=sys.stderr)
        return 1

    tracks = [args.track] if args.track != "both" else [p.track for p in profiles]
    prof_by_track = {p.track: p for p in profiles}
    missing = [t for t in tracks if t not in prof_by_track]
    if missing:
        print(f"Missing CV for track(s): {missing}", file=sys.stderr)
        return 1

    conn = connect(Path(args.db) if args.db else None)
    init_schema(conn)

    cur = conn.execute(
        """
        SELECT
            uuid,
            source,
            status,
            title,
            jobtitle,
            employer_name,
            description_text,
            in_rogaland,
            municipal,
            county,
            feed_municipal
        FROM job_postings
        WHERE status IS NULL OR UPPER(status) = 'ACTIVE'
        """
    )
    rows = cur.fetchall()
    if not rows:
        print("No job rows to score (ingest NAV jobs first).", file=sys.stderr)
        log.warning("no active job rows to score")
        conn.close()
        return 1

    log.info("scoring %d active jobs for tracks=%s", len(rows), tracks)
    scored_at = utc_now_iso()
    n = 0
    per_track: dict[str, int] = {track: 0 for track in tracks}
    for row in rows:
        for track in tracks:
            profile = prof_by_track[track]
            out = score_profile(profile, row, tek_by_norm)
            upsert_score(
                conn,
                {
                    "uuid": row["uuid"],
                    "source": row["source"],
                    "track": track,
                    "scored_at": scored_at,
                    **out,
                },
            )
            n += 1
            per_track[track] = per_track.get(track, 0) + 1
    conn.commit()

    for track, count in per_track.items():
        log.info("scored track=%s jobs=%d score_rows=%d", track, len(rows), count)

    summary = {"jobs": len(rows), "score_rows": n, "tracks": tracks, "db": str(Path(args.db) if args.db else DEFAULT_DB_PATH)}
    log_json_summary(log, "score summary", summary)
    print(json.dumps(summary, indent=2))

    if args.print_top > 0:
        for track in tracks:
            q = """
            SELECT j.title, j.employer_name, j.county, j.in_rogaland, j.link,
                   s.score_total, s.score_base, s.boost_rogaland, s.boost_tek,
                   s.matched_keywords, s.tek_match_name
            FROM job_scores s
            JOIN job_postings j ON j.uuid = s.uuid AND j.source = s.source
            WHERE s.track = ?
            ORDER BY s.score_total DESC, s.score_base DESC, s.boost_tek DESC, j.title
            LIMIT ?
            """
            top = conn.execute(q, (track, args.print_top)).fetchall()
            print(f"\n--- Top {args.print_top} ({track}) ---")
            for r in top:
                loc = "Rogaland" if r["in_rogaland"] else (r["county"] or "—")
                tek = f" TEK:{r['tek_match_name']}" if r["tek_match_name"] else ""
                print(
                    f"  {r['score_total']:.1f} (base {r['score_base']:.1f} +loc{r['boost_rogaland']:.0f} +tek{r['boost_tek']:.0f}) | {loc}{tek}\n"
                    f"    {r['title'][:80]} — {r['employer_name']}\n"
                    f"    {r['link'] or '—'}"
                )
    conn.close()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Score jobs vs CV profiles + preferred-location + TEK boosts")
    p.add_argument("--db", default="", help=f"SQLite DB (default {DEFAULT_DB_PATH})")
    p.add_argument("--track", choices=("academic", "industry", "both"), default="both")
    p.add_argument(
        "--tek-csv",
        default=str(DEFAULT_TEK_CSV),
        metavar="PATH",
        help=f"TEK Rogaland members CSV (default: {DEFAULT_TEK_CSV.name})",
    )
    p.add_argument("--no-tek", action="store_true", help="Do not apply TEK member employer boost")
    p.add_argument("--print-top", type=int, default=15, help="Print top N per track (0 to skip)")
    args = p.parse_args()
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
