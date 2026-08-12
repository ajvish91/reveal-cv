#!/usr/bin/env python3
"""
Phase B: Ingest active job ads from NAV Arbeidsplassen (PAM stilling feed).

Uses a *recent* If-Modified-Since window so feed pages are mostly ACTIVE listings.
See https://navikt.github.io/pam-stilling-feed/

Examples:
  .venv/bin/python -m job_search.ingest_nav_jobs
  .venv/bin/python -m job_search.ingest_nav_jobs --since-days 7 --max-pages 4 --max-details 120
  .venv/bin/python -m job_search.ingest_nav_jobs --feed-only --no-keyword-filter
  .venv/bin/python -m job_search.ingest_nav_jobs --list-keywords
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import argparse
import json
import time
from typing import Any

from shared.cv_loader import load_default_profiles
from job_search.deadline_utils import coerce_expires_value
from job_search.ingest_common import (
    ROGALAND_COUNTY,
    ROGALAND_MUNICIPAL,
    mark_stale_jobs_inactive,
    strip_html,
)
from job_search.ingest_keywords import collect_ingest_keywords
from job_search.job_db import DEFAULT_DB_PATH, connect, get_state, init_schema, set_state, upsert_job, utc_now_iso
from job_search.job_filters import (
    haystack_for_filter,
    matching_terms,
    matches_any_include_term,
    matches_exclude_terms,
    merge_exclude_terms,
    merge_include_terms,
)
from job_search.location_preferences import match_preferred_location, merged_preferred_locations
from job_search.logging_config import configure_logging, get_logger, log_json_summary
from job_search.nav_feed_client import NavFeedSession, default_if_modified_since

log = get_logger("job_search.ingest_nav")


def rogaland_from_locations(locations: list[dict[str, Any]] | None) -> tuple[bool, str | None, str | None]:
    if not locations:
        return False, None, None
    munis: list[str] = []
    counties: list[str] = []
    for loc in locations:
        m = (loc.get("municipal") or "").strip().upper() or None
        c = (loc.get("county") or "").strip().upper() or None
        if m:
            munis.append(m)
        if c:
            counties.append(c)
        if c == ROGALAND_COUNTY:
            return True, m, c
        if m and m in ROGALAND_MUNICIPAL:
            return True, m, c
    return False, munis[0] if munis else None, counties[0] if counties else None


def feed_item_rogaland_guess(feed_municipal: str | None) -> bool:
    if not feed_municipal:
        return False
    return feed_municipal.strip().upper() in ROGALAND_MUNICIPAL


def parse_state_timestamp(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def effective_if_modified_since(conn: Any, args: argparse.Namespace) -> datetime:
    baseline = default_if_modified_since(args.since_days)
    if not args.use_feed_state:
        return baseline
    previous_success = parse_state_timestamp(get_state(conn, "nav_feed:last_success_at"))
    if previous_success is None:
        return baseline
    overlapped = previous_success - timedelta(hours=max(0, args.state_overlap_hours))
    return max(baseline, overlapped)


def run(args: argparse.Namespace) -> int:
    configure_logging(console=True)
    if args.list_keywords:
        for k in collect_ingest_keywords(args.keyword, include_skills=args.keyword_source == "keywords-and-skills"):
            print(k)
        return 0

    profiles = load_default_profiles()
    preferred_locations = merged_preferred_locations(profiles)
    keywords = collect_ingest_keywords(
        args.keyword,
        include_skills=args.keyword_source == "keywords-and-skills",
    )
    if not keywords:
        print("Note: no keywords from cv/*.md; pass --keyword or fill YAML lists.", file=sys.stderr)
        log.warning("no keywords from cv profiles; pass --keyword or fill YAML lists")

    client = NavFeedSession()
    log.info(
        "NAV ingest start db=%s max_pages=%d max_details=%d since_days=%d",
        Path(args.db) if args.db else DEFAULT_DB_PATH,
        args.max_pages,
        args.max_details,
        args.since_days,
    )
    path = "/api/v1/feed"
    fetched_at = utc_now_iso()
    n_pages = 0
    n_seen_active = 0
    n_stored = 0
    n_details = 0
    n_skip_noise = 0
    n_skip_not_tech = 0
    n_stale_inactivated = 0
    complete_feed_walk = True

    require_terms: tuple[str, ...] = ()
    if args.require_tech:
        require_terms = merge_include_terms(
            not getattr(args, "require_tech_no_defaults", False),
            "",
            args.include_tech or [],
        )
        if not require_terms:
            print("--require-tech set but no terms (--include-tech or defaults off).", file=sys.stderr)

    exclude_terms: tuple[str, ...] = ()
    if getattr(args, "exclude_noise", False):
        use_noise_def = not getattr(args, "exclude_noise_no_defaults", False)
        exclude_terms = merge_exclude_terms(
            use_noise_def,
            "",
            args.exclude or [],
        )

    conn = connect(Path(args.db) if args.db else None)
    init_schema(conn)
    ims = effective_if_modified_since(conn, args)
    feed_etag = get_state(conn, "nav_feed:first_page_etag") if args.use_feed_state else None

    queued: list[tuple[int, dict[str, Any]]] = []
    seen_uuids: set[str] = set()

    while n_pages < args.max_pages:
        n_pages += 1
        try:
            page, hdrs = client.fetch_feed_page(
                path,
                if_modified_since=ims,
                etag=feed_etag if n_pages == 1 else None,
            )
        except RuntimeError as e:
            print(f"Feed error: {e}", file=sys.stderr)
            log.error("feed page %d failed: %s", n_pages, e)
            conn.close()
            return 1

        items = page.get("items") or []
        log.info("feed page %d: %d items", n_pages, len(items))

        if n_pages == 1 and args.use_feed_state:
            if hdrs.get("etag"):
                set_state(conn, "nav_feed:first_page_etag", hdrs.get("etag"))

        if not items:
            if n_pages == args.max_pages and page.get("next_url"):
                complete_feed_walk = False
            break

        for it in items:
            fe = it.get("_feed_entry") or {}
            if fe.get("status") != "ACTIVE":
                continue
            n_seen_active += 1
            uuid = fe.get("uuid") or it.get("id")
            if not uuid:
                continue
            seen_uuids.add(uuid)
            feed_muni = (fe.get("municipal") or "").strip().upper() or None
            title_feed = (fe.get("title") or it.get("title") or "").strip()
            biz = (fe.get("businessName") or "").strip()
            feed_location_match = match_preferred_location(
                preferred_locations,
                municipal=feed_muni,
                county=ROGALAND_COUNTY if feed_item_rogaland_guess(feed_muni) else None,
                feed_municipal=feed_muni,
            )

            if args.feed_only:
                hay = haystack_for_filter(title_feed, None, None, biz)
                hits = matching_terms(hay, keywords) if keywords else []
                in_r = feed_item_rogaland_guess(feed_muni)
                location_matched = feed_location_match.matched or in_r
                if args.rogaland_only and not location_matched:
                    continue
                if args.keyword_filter:
                    if not hits and not location_matched:
                        continue
                if require_terms and not matches_any_include_term(
                    haystack_for_filter(title_feed, None, None, biz), require_terms
                ):
                    n_skip_not_tech += 1
                    continue
                if exclude_terms and matches_exclude_terms(
                    haystack_for_filter(title_feed, None, None, biz), exclude_terms
                ):
                    n_skip_noise += 1
                    continue
                row = {
                    "uuid": uuid,
                    "source": "nav_arbeidsplassen",
                    "status": "ACTIVE",
                    "title": title_feed,
                    "jobtitle": None,
                    "employer_name": biz or None,
                    "employer_orgnr": None,
                    "municipal": feed_muni,
                    "county": ROGALAND_COUNTY if in_r else None,
                    "application_url": None,
                    "link": f"https://arbeidsplassen.nav.no/stillinger/stilling/{uuid}",
                    "published": None,
                    "expires": None,
                    "updated": fe.get("sistEndret"),
                    "description_text": None,
                    "raw_json": json.dumps({"_feed_entry": fe, "feed_item": {"title": it.get("title")}}, ensure_ascii=False),
                    "fetched_at": fetched_at,
                    "in_rogaland": 1 if in_r else 0,
                    "location_matched": 1 if location_matched else 0,
                    "location_label": feed_location_match.label or (ROGALAND_COUNTY.title() if in_r else None),
                    "keyword_hits": ", ".join(hits) if hits else None,
                    "feed_municipal": feed_muni,
                }
                upsert_job(conn, row)
                n_stored += 1
                continue

            prio = 0 if (feed_location_match.matched or feed_item_rogaland_guess(feed_muni)) else 1
            queued.append((prio, it))

        next_path = page.get("next_url")
        if not next_path:
            break
        path = next_path
        if n_pages >= args.max_pages:
            complete_feed_walk = False

    if not args.feed_only and queued:
        queued.sort(key=lambda x: (x[0], x[1].get("id") or ""))
        for _prio, it in queued:
            if n_details >= args.max_details:
                break
            fe = it.get("_feed_entry") or {}
            uuid = fe.get("uuid") or it.get("id")
            feed_muni = (fe.get("municipal") or "").strip().upper() or None
            title_feed = (fe.get("title") or it.get("title") or "").strip()
            biz = (fe.get("businessName") or "").strip()
            rel = it.get("url")
            if not uuid or not rel or not isinstance(rel, str):
                continue
            in_r_feed = feed_item_rogaland_guess(feed_muni)
            try:
                entry = client.fetch_feed_entry(rel)
            except RuntimeError as e:
                print(f"Skip {uuid}: {e}", file=sys.stderr)
                log.warning("skip detail fetch uuid=%s: %s", uuid, e)
                continue
            n_details += 1
            if args.sleep_s:
                time.sleep(args.sleep_s)

            ad = entry.get("ad_content") or {}
            locs = ad.get("workLocations")
            in_r, municipal, county = rogaland_from_locations(locs if isinstance(locs, list) else None)
            if not in_r:
                in_r = in_r_feed
            location_match = match_preferred_location(
                preferred_locations,
                municipal=municipal or feed_muni,
                county=county,
                feed_municipal=feed_muni,
            )
            location_matched = location_match.matched or in_r

            title = (ad.get("title") or title_feed).strip()
            desc_html = ad.get("description") or ""
            desc_text = strip_html(desc_html)[:20000]
            jobtitle = (ad.get("jobtitle") or "").strip() or None
            emp = ad.get("employer") if isinstance(ad.get("employer"), dict) else {}
            emp_name = (emp.get("name") or biz or "").strip() or None
            emp_org = (emp.get("orgnr") or "").strip() or None

            hay = haystack_for_filter(title, jobtitle, desc_text, emp_name)
            hits = matching_terms(hay, keywords) if keywords else []

            if args.rogaland_only and not location_matched:
                continue
            if args.keyword_filter and not hits and not location_matched:
                continue
            if require_terms and not matches_any_include_term(
                haystack_for_filter(title, jobtitle, desc_text, emp_name or ""),
                require_terms,
            ):
                n_skip_not_tech += 1
                continue
            if exclude_terms and matches_exclude_terms(
                haystack_for_filter(title, jobtitle, desc_text, emp_name or ""),
                exclude_terms,
            ):
                n_skip_noise += 1
                continue

            row = {
                "uuid": uuid,
                "source": "nav_arbeidsplassen",
                "status": (entry.get("status") or fe.get("status") or "ACTIVE"),
                "title": title,
                "jobtitle": jobtitle,
                "employer_name": emp_name,
                "employer_orgnr": emp_org,
                "municipal": municipal or feed_muni,
                "county": county,
                "application_url": ad.get("applicationUrl"),
                "link": ad.get("link"),
                "published": ad.get("published"),
                "expires": coerce_expires_value(ad.get("expires")),
                "updated": ad.get("updated") or entry.get("sistEndret"),
                "description_text": desc_text or None,
                "raw_json": entry,
                "fetched_at": fetched_at,
                "in_rogaland": 1 if in_r else 0,
                "location_matched": 1 if location_matched else 0,
                "location_label": location_match.label or (ROGALAND_COUNTY.title() if in_r else None),
                "keyword_hits": ", ".join(hits) if hits else None,
                "feed_municipal": feed_muni,
            }
            upsert_job(conn, row)
            n_stored += 1

    # NAV feed is incremental (If-Modified-Since): a "complete" page walk only means we
    # reached the end of *recent changes*, not that we enumerated every active posting.
    # Stale marking is opt-in (--mark-stale) for full backfills without IMS.
    if args.mark_stale and complete_feed_walk and seen_uuids:
        n_stale_inactivated = mark_stale_jobs_inactive(
            conn,
            source="nav_arbeidsplassen",
            fetched_at=fetched_at,
            seen_uuids=seen_uuids,
        )
    if n_seen_active > 0 and args.use_feed_state:
        set_state(conn, "nav_feed:last_success_at", fetched_at)
    conn.commit()
    conn.close()

    summary = {
        "db": str(Path(args.db) if args.db else DEFAULT_DB_PATH),
        "pages": n_pages,
        "active_items_seen": n_seen_active,
        "stored_rows": n_stored,
        "detail_fetches": n_details,
        "if_modified_since": ims.isoformat(),
        "preferred_locations": preferred_locations,
        "skipped_noise": n_skip_noise,
        "skipped_not_tech_allowlist": n_skip_not_tech,
        "stale_jobs_inactivated": n_stale_inactivated,
        "complete_feed_walk": complete_feed_walk,
    }
    log.info(
        "NAV ingest done pages=%d stored=%d skipped_noise=%d skipped_tech=%d stale=%d",
        n_pages,
        n_stored,
        n_skip_noise,
        n_skip_not_tech,
        n_stale_inactivated,
    )
    log_json_summary(log, "NAV ingest summary", summary)
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Ingest NAV Arbeidsplassen jobs (PAM feed)")
    p.add_argument("--db", default="", help=f"SQLite path (default: {DEFAULT_DB_PATH})")
    p.add_argument("--since-days", type=int, default=3, help="Base If-Modified-Since window in days for daily ingest")
    p.add_argument("--max-pages", type=int, default=2, help="Max feed pages to walk (increase for backfills)")
    p.add_argument("--feed-only", action="store_true", help="Only use feed summaries (no per-ad detail fetch)")
    p.add_argument("--max-details", type=int, default=80, help="Max successful detail fetches when not --feed-only")
    p.add_argument("--sleep-s", type=float, default=0.1, help="Pause between detail requests")
    p.add_argument("--keyword", action="append", default=[], help="Extra keyword (repeatable)")
    p.add_argument(
        "--keyword-source",
        choices=("keywords", "keywords-and-skills"),
        default="keywords-and-skills",
        help="Use profile keywords only, or keywords plus skills, for ingest keyword matching (default: both)",
    )
    p.add_argument(
        "--keyword-filter",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Keep ads that match a profile keyword or a preferred location (default: on)",
    )
    p.add_argument("--rogaland-only", action="store_true", help="Keep only preferred/Rogaland locations")
    p.add_argument("--list-keywords", action="store_true", help="Print merged CV keywords and exit")
    p.add_argument(
        "--require-tech",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only store jobs matching >=1 ICT/AI/CS token (default: on)",
    )
    p.add_argument(
        "--require-tech-no-defaults",
        action="store_true",
        help="With --require-tech, only use --include-tech (not the built-in allowlist)",
    )
    p.add_argument(
        "--include-tech",
        action="append",
        default=[],
        metavar="SUBSTR",
        help="Extra allowlist substring for --require-tech (repeatable)",
    )
    p.add_argument(
        "--exclude-noise",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip jobs matching exclude/blocklist terms (default: on)",
    )
    p.add_argument(
        "--exclude-noise-no-defaults",
        action="store_true",
        help="With --exclude-noise, only use terms from --exclude (not the built-in list)",
    )
    p.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="SUBSTR",
        help="Extra case-insensitive substring to treat as noise (repeatable); needs --exclude-noise",
    )
    p.add_argument(
        "--use-feed-state",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Reuse persisted ETag / last-success time from the SQLite ingest_state table",
    )
    p.add_argument(
        "--state-overlap-hours",
        type=int,
        default=6,
        help="Overlap applied when resuming from persisted ingest state",
    )
    p.add_argument(
        "--mark-stale",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Mark ACTIVE rows not seen in this run as INACTIVE (default: off; NAV feed is incremental)",
    )
    args = p.parse_args()
    if args.feed_only:
        args.max_details = 0
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
