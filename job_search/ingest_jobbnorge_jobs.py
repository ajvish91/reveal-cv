#!/usr/bin/env python3
"""
Ingest job ads from Jobbnorge.no (public catalog API + optional PDF text).

Examples:
  .venv/bin/python -m job_search.ingest_jobbnorge_jobs
  .venv/bin/python -m job_search.ingest_jobbnorge_jobs --max-details 30 --no-require-tech
  .venv/bin/python -m job_search.ingest_jobbnorge_jobs --search-only
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from shared.cv_loader import load_default_profiles

from job_search.ingest_common import ROGALAND_COUNTY, ROGALAND_MUNICIPAL, mark_stale_jobs_inactive
from job_search.ingest_keywords import collect_ingest_keywords
from job_search.job_db import DEFAULT_DB_PATH, connect, init_schema, set_state, upsert_job, utc_now_iso
from job_search.job_filters import (
    ACADEMIC_RESEARCH_EMPLOYERS,
    ACADEMIC_ROLE_TITLE_TERMS,
    haystack_for_filter,
    matching_terms,
    matches_any_include_term,
    matches_exclude_terms,
    merge_exclude_terms,
    merge_include_terms,
)
from job_search.jobbnorge_client import (
    JobbnorgeClient,
    apply_url,
    deadline_from_pdf_text,
    listing_url,
    normalize_api_deadline,
)
from job_search.location_preferences import match_preferred_location, merged_preferred_locations
from job_search.logging_config import configure_logging, get_logger, log_json_summary
from job_search.role_search_config import finn_search_queries_for_track

SOURCE = "jobbnorge"
log = get_logger("job_search.ingest_jobbnorge")

_ROGALAND_CITY_NAMES = frozenset(
    {
        "stavanger",
        "sandnes",
        "haugesund",
        "egersund",
        "sola",
        "randaberg",
        "karmøy",
        "karmoy",
        "jørpeland",
        "jorpeland",
        "bryne",
        "hommersåk",
        "hommersak",
    }
)


def infer_location_flags(
    location: str | None,
    *,
    preferred_locations: list[str],
) -> tuple[bool, bool, str | None, str | None]:
    loc = (location or "").strip()
    municipal: str | None = loc.upper() if loc else None
    county: str | None = None
    low = loc.casefold()
    in_r = bool(municipal and municipal in ROGALAND_MUNICIPAL)
    if not in_r and low in _ROGALAND_CITY_NAMES:
        in_r = True
        county = ROGALAND_COUNTY
    if not in_r and "rogaland" in low:
        in_r = True
        county = ROGALAND_COUNTY
    location_match = match_preferred_location(
        preferred_locations,
        municipal=municipal,
        county=county,
    )
    location_matched = location_match.matched or in_r
    label = location_match.label or (loc if loc else None)
    if in_r and not label:
        label = ROGALAND_COUNTY.title()
    return in_r, location_matched, municipal, label


def card_passes_filters(
    card: dict[str, Any],
    *,
    keywords: list[str],
    keyword_filter: bool,
    rogaland_only: bool,
    require_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...],
    preferred_locations: list[str],
    search_track_terms: tuple[str, ...],
) -> tuple[bool, list[str], bool, bool, str | None]:
    title = (card.get("title") or "").strip()
    employer = (card.get("employer") or "").strip() or None
    summary = (card.get("summary") or "").strip()
    location = (card.get("location") or "").strip() or None
    in_r, location_matched, _muni, label = infer_location_flags(
        location,
        preferred_locations=preferred_locations,
    )
    hay = haystack_for_filter(title, None, summary, employer)
    hits = matching_terms(hay, keywords) if keywords else []
    sparse = len(summary) < 280

    if search_track_terms and not matches_any_include_term(hay, search_track_terms):
        return False, hits, in_r, location_matched, label
    if rogaland_only and not location_matched:
        return False, hits, in_r, location_matched, label
    if keyword_filter and not hits and not sparse:
        return False, hits, in_r, location_matched, label
    if require_terms and not matches_any_include_term(hay, require_terms):
        return False, hits, in_r, location_matched, label
    if exclude_terms and matches_exclude_terms(hay, exclude_terms):
        return False, hits, in_r, location_matched, label
    return True, hits, in_r, location_matched, label


def detail_priority(
    job_id: str,
    *,
    known_uuids: set[str],
    missing_description: set[str],
    rogaland_ids: set[str],
) -> tuple[int, str]:
    if job_id in rogaland_ids:
        base = 0
    elif job_id not in known_uuids:
        base = 1
    elif job_id in missing_description:
        base = 2
    else:
        base = 3
    return (base, job_id)


def run_ingest(args: argparse.Namespace) -> int:
    configure_logging(console=True)
    profiles = load_default_profiles()
    preferred_locations = merged_preferred_locations(profiles)
    keywords = collect_ingest_keywords(
        args.keyword,
        include_skills=args.keyword_source == "keywords-and-skills",
        include_application_boosts=getattr(args, "application_boosts", None),
    )

    search_track = getattr(args, "search_track", "both")
    search_track_terms: tuple[str, ...] = ()
    if search_track == "academic":
        # FINN academic queries plus title tokens (e.g. postdoc → postdoctoral).
        merged_academic = list(finn_search_queries_for_track("academic")) + list(
            ACADEMIC_ROLE_TITLE_TERMS
        )
        search_track_terms = tuple(dict.fromkeys(merged_academic))
    elif search_track == "industry":
        search_track_terms = tuple(finn_search_queries_for_track("industry"))

    require_terms: tuple[str, ...] = ()
    if search_track == "academic" and args.require_tech:
        require_terms = ACADEMIC_ROLE_TITLE_TERMS + ACADEMIC_RESEARCH_EMPLOYERS
    elif args.require_tech:
        require_terms = merge_include_terms(
            not getattr(args, "require_tech_no_defaults", False),
            "",
            args.include_tech or [],
        )

    exclude_terms: tuple[str, ...] = ()
    if getattr(args, "exclude_noise", False):
        exclude_terms = merge_exclude_terms(
            not getattr(args, "exclude_noise_no_defaults", False),
            "",
            args.exclude or [],
        )

    client = JobbnorgeClient(sleep_s=args.sleep_s)
    fetched_at = utc_now_iso()
    log.info("Jobbnorge ingest start db=%s search_track=%s", args.db or DEFAULT_DB_PATH, search_track)

    try:
        catalog = client.fetch_job_catalog()
    except Exception as e:
        print(f"Jobbnorge catalog error: {e}", file=sys.stderr)
        log.error("catalog fetch failed: %s", e)
        return 1

    conn = connect(Path(args.db) if args.db else None)
    init_schema(conn)
    known_rows = conn.execute(
        "SELECT uuid, description_text FROM job_postings WHERE source = ?",
        (SOURCE,),
    ).fetchall()
    known_uuids = {str(r["uuid"]) for r in known_rows}
    missing_description = {
        str(r["uuid"])
        for r in known_rows
        if not (r["description_text"] or "").strip()
    }

    candidates: list[dict[str, Any]] = []
    n_skipped = 0
    for card in catalog:
        job_id = card.get("id")
        if job_id is None:
            continue
        ok, hits, in_r, location_matched, label = card_passes_filters(
            card,
            keywords=keywords,
            keyword_filter=args.keyword_filter,
            rogaland_only=args.rogaland_only,
            require_terms=require_terms,
            exclude_terms=exclude_terms,
            preferred_locations=preferred_locations,
            search_track_terms=search_track_terms,
        )
        if not ok:
            n_skipped += 1
            continue
        candidates.append(
            {
                "card": card,
                "hits": hits,
                "in_r": in_r,
                "location_matched": location_matched,
                "label": label,
            }
        )

    rogaland_ids = {str(c["card"]["id"]) for c in candidates if c["in_r"]}
    candidates.sort(
        key=lambda c: detail_priority(
            str(c["card"]["id"]),
            known_uuids=known_uuids,
            missing_description=missing_description,
            rogaland_ids=rogaland_ids,
        )
    )

    seen_uuids: set[str] = set()
    n_stored = 0
    n_pdf = 0
    client_sleep = max(0.0, float(args.sleep_s))

    for item in candidates:
        card = item["card"]
        job_id = int(card["id"])
        uuid = str(job_id)
        seen_uuids.add(uuid)

        title = (card.get("title") or "").strip() or None
        employer = (card.get("employer") or "").strip() or None
        summary = (card.get("summary") or "").strip()
        expires = normalize_api_deadline(card.get("deadline"))

        description_text = summary
        if not args.search_only and n_pdf < args.max_details:
            try:
                pdf_text = client.fetch_pdf_text(job_id)
                n_pdf += 1
                if pdf_text:
                    description_text = pdf_text[:20000]
                    pdf_deadline = deadline_from_pdf_text(pdf_text)
                    if pdf_deadline:
                        expires = pdf_deadline
                if client_sleep:
                    time.sleep(client_sleep)
            except Exception as e:
                log.warning("PDF fetch failed id=%s: %s", job_id, e)

        row = {
            "uuid": uuid,
            "source": SOURCE,
            "status": "ACTIVE",
            "title": title,
            "jobtitle": None,
            "employer_name": employer,
            "employer_orgnr": None,
            "municipal": (card.get("location") or "").strip().upper() or None,
            "county": ROGALAND_COUNTY if item["in_r"] else None,
            "application_url": apply_url(job_id),
            "link": listing_url(job_id),
            "published": None,
            "expires": expires,
            "updated": None,
            "description_text": description_text or None,
            "raw_json": json.dumps(card, ensure_ascii=False),
            "fetched_at": fetched_at,
            "in_rogaland": 1 if item["in_r"] else 0,
            "location_matched": 1 if item["location_matched"] else 0,
            "location_label": item["label"],
            "keyword_hits": ", ".join(item["hits"]) if item["hits"] else None,
            "feed_municipal": None,
        }
        upsert_job(conn, row)
        n_stored += 1

    n_stale = 0
    if seen_uuids and args.mark_stale:
        n_stale = mark_stale_jobs_inactive(
            conn,
            source=SOURCE,
            fetched_at=fetched_at,
            seen_uuids=seen_uuids,
        )
    if seen_uuids and args.use_ingest_state:
        set_state(conn, "jobbnorge:last_success_at", fetched_at)
    conn.commit()
    conn.close()

    summary = {
        "source": SOURCE,
        "catalog_rows": len(catalog),
        "stored_rows": n_stored,
        "pdf_fetches": n_pdf,
        "skipped_filters": n_skipped,
        "stale_inactivated": n_stale,
    }
    log.info(
        "Jobbnorge ingest done stored=%d pdf=%d skipped=%d stale=%d",
        n_stored,
        n_pdf,
        n_skipped,
        n_stale,
    )
    log_json_summary(log, "Jobbnorge ingest summary", summary)
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Ingest Jobbnorge.no jobs (public API + PDF)")
    p.add_argument("--db", default="", help=f"SQLite path (default: {DEFAULT_DB_PATH})")
    p.add_argument("--keyword", action="append", default=[], help="Extra keyword (repeatable)")
    p.add_argument(
        "--keyword-source",
        choices=("keywords", "keywords-and-skills"),
        default="keywords-and-skills",
    )
    p.add_argument(
        "--keyword-filter",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    p.add_argument(
        "--application-boosts",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    p.add_argument("--rogaland-only", action="store_true")
    p.add_argument(
        "--require-tech",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    p.add_argument("--require-tech-no-defaults", action="store_true")
    p.add_argument("--include-tech", action="append", default=[], metavar="SUBSTR")
    p.add_argument(
        "--exclude-noise",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    p.add_argument("--exclude-noise-no-defaults", action="store_true")
    p.add_argument("--exclude", action="append", default=[], metavar="SUBSTR")
    p.add_argument(
        "--search-track",
        choices=("industry", "academic", "both"),
        default="both",
        help="When academic/industry, keep only cards matching that track's FINN search terms",
    )
    p.add_argument("--max-details", type=int, default=40, help="Max PDF detail fetches per run")
    p.add_argument("--sleep-s", type=float, default=0.35, help="Pause between PDF requests")
    p.add_argument("--search-only", action="store_true", help="Store catalog summaries only (no PDF)")
    p.add_argument(
        "--mark-stale",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Mark ACTIVE Jobbnorge rows not seen this run as INACTIVE",
    )
    p.add_argument(
        "--use-ingest-state",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    p.add_argument("--list-keywords", action="store_true")
    args = p.parse_args()

    if args.list_keywords:
        kws = collect_ingest_keywords(
            args.keyword,
            include_skills=args.keyword_source == "keywords-and-skills",
            include_application_boosts=args.application_boosts,
        )
        for kw in kws:
            print(kw)
        return 0

    return run_ingest(args)


if __name__ == "__main__":
    raise SystemExit(main())
