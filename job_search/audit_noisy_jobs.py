#!/usr/bin/env python3
"""
Audit active job_postings for noise and weak profile overlap.

Run after ingest/score (also wired into ``scripts/run_job_search_cycle.py``):

  .venv/bin/python -m job_search.audit_noisy_jobs
  .venv/bin/python -m job_search.audit_noisy_jobs --print-limit 30
  .venv/bin/python -m job_search.audit_noisy_jobs --mark-blocklist-inactive
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from shared.cv_loader import load_default_profiles
from job_search.ingest_keywords import (
    WEAK_ALONE_INGEST_TERMS,
    collect_ingest_keywords,
    profile_terms_from_loaded,
)
from job_search.job_db import DEFAULT_DB_PATH, connect, init_schema
from job_search.job_filters import (
    DEFAULT_EXCLUDE_TERMS,
    DEFAULT_TECH_INCLUDE_TERMS,
    haystack_for_filter,
    matching_terms,
    matches_any_include_term,
    matches_exclude_terms,
)
from job_search.logging_config import configure_logging, get_logger, log_json_summary
from job_search.role_search_config import DEFAULT_INGEST_KEYWORD_BOOSTS

log = get_logger("job_search.audit")


def _as_float(value: Any) -> float:
    try:
        return float(value) if value is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def audit_active_jobs(
    conn,
    *,
    track: str = "industry",
    print_limit: int = 25,
) -> dict[str, Any]:
    """
    Scan ACTIVE postings joined to ``track`` scores.

    Flags:
      - blocklist: matches DEFAULT_EXCLUDE_TERMS
      - zero_score: score_base == 0 (no strong CV keyword/skill hit at score time)
      - no_profile_hit: text has no current strong profile keep-term
      - boost_only_hits: ingest keyword_hits only from application boosts / weak alone terms
      - legacy_location: score_base == 0 and empty keyword_hits (pre-fix location keep)
    """
    profiles = load_default_profiles()
    profile_all = profile_terms_from_loaded(profiles, include_skills=True)
    strong_keep = collect_ingest_keywords(
        [],
        include_skills=True,
        include_application_boosts=False,
        drop_weak_alone=True,
    )
    boost_set = {t.casefold() for t in DEFAULT_INGEST_KEYWORD_BOOSTS}
    weak_set = set(WEAK_ALONE_INGEST_TERMS)
    boost_or_weak = boost_set | weak_set

    rows = conn.execute(
        """
        SELECT
            j.uuid,
            j.source,
            j.title,
            j.employer_name,
            j.jobtitle,
            j.description_text,
            j.keyword_hits,
            j.municipal,
            j.county,
            s.score_base,
            s.score_total,
            s.matched_keywords,
            s.matched_skills
        FROM job_postings j
        LEFT JOIN job_scores s
            ON s.uuid = j.uuid AND s.source = j.source AND s.track = ?
        WHERE j.status IS NULL OR UPPER(j.status) = 'ACTIVE'
        ORDER BY COALESCE(s.score_base, 0) ASC, j.title
        """,
        (track,),
    ).fetchall()

    blocklist_rows: list[dict[str, Any]] = []
    zero_score_rows: list[dict[str, Any]] = []
    no_profile_rows: list[dict[str, Any]] = []
    boost_only_rows: list[dict[str, Any]] = []
    legacy_rows: list[dict[str, Any]] = []
    false_hit_terms: Counter[str] = Counter()
    title_noise_stems: Counter[str] = Counter()

    extra_title_stems = (
        "lege",
        "sykepleier",
        "psykolog",
        "terapeut",
        "lærer",
        "laerer",
        "pedagog",
        "salgs",
        "selger",
        "butikk",
        "sekretær",
        "sekretar",
        "regnskapsfører",
        "regnskapsforer",
        "controller",
        "jordmor",
        "tannpleier",
        "miljøterapeut",
        "miljoterapeut",
        "bofellesskap",
        "hjemmetjeneste",
        "stipendiat",
    )

    for r in rows:
        hay = haystack_for_filter(r["title"], r["jobtitle"], r["description_text"], r["employer_name"])
        title_hay = haystack_for_filter(r["title"], r["jobtitle"], None, None)
        score_base = _as_float(r["score_base"])
        hits_raw = [h.strip() for h in (r["keyword_hits"] or "").split(",") if h.strip()]
        hits_cf = [h.casefold() for h in hits_raw]
        strong_hits = matching_terms(hay, strong_keep)
        blocklist = matches_exclude_terms(hay, DEFAULT_EXCLUDE_TERMS)
        tech_ok = matches_any_include_term(hay, DEFAULT_TECH_INCLUDE_TERMS)

        item = {
            "uuid": r["uuid"],
            "source": r["source"],
            "title": (r["title"] or "")[:120],
            "employer_name": (r["employer_name"] or "")[:80],
            "score_base": score_base,
            "score_total": _as_float(r["score_total"]),
            "keyword_hits": r["keyword_hits"],
            "matched_keywords": r["matched_keywords"],
            "matched_skills": r["matched_skills"],
            "strong_profile_hits": ", ".join(strong_hits) if strong_hits else None,
            "tech_allowlist": tech_ok,
            "blocklist": blocklist,
            "location": r["municipal"] or r["county"],
        }

        if blocklist:
            blocklist_rows.append(item)
        if score_base <= 0:
            zero_score_rows.append(item)
            for h in hits_cf:
                false_hit_terms[h] += 1
        if not strong_hits:
            no_profile_rows.append(item)
        if hits_cf and all(h in boost_or_weak for h in hits_cf) and score_base <= 0:
            boost_only_rows.append(item)
        if score_base <= 0 and not hits_raw:
            legacy_rows.append(item)

        for stem in extra_title_stems:
            if stem in title_hay:
                title_noise_stems[stem] += 1

    summary: dict[str, Any] = {
        "track": track,
        "active": len(rows),
        "profile_terms": len(profile_all),
        "strong_keep_terms": len(strong_keep),
        "blocklist_active": len(blocklist_rows),
        "zero_score": len(zero_score_rows),
        "no_strong_profile_hit": len(no_profile_rows),
        "boost_or_weak_only_hits": len(boost_only_rows),
        "legacy_no_keyword_hits": len(legacy_rows),
        "top_false_ingest_terms": [
            {"term": t, "count": c} for t, c in false_hit_terms.most_common(20)
        ],
        "title_noise_stems": [
            {"term": t, "count": c} for t, c in title_noise_stems.most_common(20)
        ],
        "samples": {
            "blocklist": blocklist_rows[:print_limit],
            "zero_score": zero_score_rows[:print_limit],
            "boost_or_weak_only": boost_only_rows[:print_limit],
            "legacy_no_keyword_hits": legacy_rows[:print_limit],
        },
    }
    return summary


def mark_blocklist_inactive(conn, *, track: str = "industry") -> int:
    """Set status=INACTIVE for ACTIVE rows that match the noise blocklist."""
    _ = track  # reserved for future track-scoped cleanup
    rows = conn.execute(
        """
        SELECT uuid, source, title, jobtitle, description_text, employer_name
        FROM job_postings
        WHERE status IS NULL OR UPPER(status) = 'ACTIVE'
        """
    ).fetchall()
    n = 0
    for r in rows:
        hay = haystack_for_filter(r["title"], r["jobtitle"], r["description_text"], r["employer_name"])
        if matches_exclude_terms(hay, DEFAULT_EXCLUDE_TERMS):
            conn.execute(
                "UPDATE job_postings SET status = ? WHERE uuid = ? AND source = ?",
                ("INACTIVE", r["uuid"], r["source"]),
            )
            n += 1
    if n:
        conn.commit()
    return n


def _print_human(summary: dict[str, Any], *, print_limit: int) -> None:
    print(f"\n=== Noisy jobs audit (track={summary['track']}) ===")
    print(f"active={summary['active']}  strong_keep_terms={summary['strong_keep_terms']}")
    print(
        f"blocklist_active={summary['blocklist_active']}  "
        f"zero_score={summary['zero_score']}  "
        f"no_strong_profile_hit={summary['no_strong_profile_hit']}  "
        f"boost/weak-only={summary['boost_or_weak_only_hits']}  "
        f"legacy={summary['legacy_no_keyword_hits']}"
    )
    if summary["top_false_ingest_terms"]:
        print("\nTop terms on zero-score rows (ingest keyword_hits):")
        for row in summary["top_false_ingest_terms"][:15]:
            print(f"  {row['count']:4d}  {row['term']}")
    if summary["title_noise_stems"]:
        print("\nTitle noise stems:")
        for row in summary["title_noise_stems"][:15]:
            print(f"  {row['count']:4d}  {row['term']}")

    def _dump(label: str, items: list[dict[str, Any]]) -> None:
        if not items or print_limit <= 0:
            return
        print(f"\n--- {label} (showing {min(print_limit, len(items))}) ---")
        for item in items[:print_limit]:
            print(
                f"  [{item['score_base']:.0f}] {item['title']} — {item['employer_name']}"
            )
            if item.get("keyword_hits"):
                print(f"       ingest_hits={item['keyword_hits']}")

    samples = summary.get("samples") or {}
    _dump("blocklist", samples.get("blocklist") or [])
    _dump("zero_score", samples.get("zero_score") or [])
    _dump("boost/weak-only keeps", samples.get("boost_or_weak_only") or [])
    _dump("legacy (no keyword_hits)", samples.get("legacy_no_keyword_hits") or [])


def run(args: argparse.Namespace) -> int:
    configure_logging(console=True)
    db_path = Path(args.db).expanduser() if args.db else DEFAULT_DB_PATH
    if not db_path.is_file():
        print(f"Database not found: {db_path}", file=sys.stderr)
        return 1

    conn = connect(db_path)
    init_schema(conn)
    try:
        marked = 0
        if args.mark_blocklist_inactive:
            marked = mark_blocklist_inactive(conn, track=args.track)
            log.info("marked %d blocklist rows INACTIVE", marked)

        summary = audit_active_jobs(conn, track=args.track, print_limit=args.print_limit)
        summary["marked_blocklist_inactive"] = marked
        log_json_summary(log, "noisy jobs audit", {
            k: summary[k]
            for k in (
                "track",
                "active",
                "blocklist_active",
                "zero_score",
                "no_strong_profile_hit",
                "boost_or_weak_only_hits",
                "legacy_no_keyword_hits",
                "marked_blocklist_inactive",
            )
        })
        if args.json:
            # Compact JSON for cycle parsers (omit large samples unless --print-limit).
            out = {k: v for k, v in summary.items() if k != "samples"}
            if args.print_limit > 0:
                out["samples"] = summary["samples"]
            print(json.dumps(out, indent=2, ensure_ascii=False))
        else:
            _print_human(summary, print_limit=args.print_limit)
            print(json.dumps({
                "track": summary["track"],
                "active": summary["active"],
                "blocklist_active": summary["blocklist_active"],
                "zero_score": summary["zero_score"],
                "no_strong_profile_hit": summary["no_strong_profile_hit"],
                "boost_or_weak_only_hits": summary["boost_or_weak_only_hits"],
                "legacy_no_keyword_hits": summary["legacy_no_keyword_hits"],
                "marked_blocklist_inactive": marked,
            }, indent=2))
    finally:
        conn.close()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Audit ACTIVE jobs for noise / weak profile overlap")
    p.add_argument("--db", default="", help=f"SQLite path (default {DEFAULT_DB_PATH})")
    p.add_argument("--track", choices=("industry", "academic"), default="industry")
    p.add_argument("--print-limit", type=int, default=20, help="Sample rows per bucket (0 = counts only)")
    p.add_argument("--json", action="store_true", help="Print full JSON report")
    p.add_argument(
        "--mark-blocklist-inactive",
        action="store_true",
        help="Mark ACTIVE rows matching the noise blocklist as INACTIVE",
    )
    return run(p.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
