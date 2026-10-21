#!/usr/bin/env python3
"""
Ingest job ads from FINN.no (search + JSON-LD detail pages).

Examples:
  .venv/bin/python -m job_search.ingest_finn_jobs
  .venv/bin/python -m job_search.ingest_finn_jobs --max-pages 5 --max-results-per-query 80
  .venv/bin/python -m job_search.ingest_finn_jobs --queries "data engineer,AI engineer" --no-require-tech
  .venv/bin/python -m job_search.ingest_finn_jobs --search-only
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import argparse
import json
import re
from typing import Any

from shared.cv_loader import load_default_profiles
from job_search.finn_deadlines import expires_and_status_from_finn_detail
from job_search.finn_job_client import FINN_EXPIRED_SENTINEL, FinnJobSession, JobGoneError, build_job_url
from job_search.finn_search_queries import finn_search_queries_for_track
from job_search.ingest_common import (
    ROGALAND_COUNTY,
    ROGALAND_MUNICIPAL,
    mark_stale_jobs_inactive,
    strip_html,
)
from job_search.ingest_keywords import collect_ingest_keywords
from job_search.job_db import DEFAULT_DB_PATH, connect, init_schema, set_state, upsert_job, utc_now_iso
from job_search.job_filters import (
    ACADEMIC_RESEARCH_EMPLOYERS,
    ACADEMIC_ROLE_TITLE_TERMS,
    MIN_FINN_DESCRIPTION_CHARS,
    haystack_for_filter,
    matching_terms,
    matches_any_include_term,
    matches_exclude_terms,
    merge_exclude_terms,
    merge_include_terms,
)
from job_search.location_preferences import match_preferred_location, merged_preferred_locations
from job_search.logging_config import configure_logging, get_logger, log_json_summary

SOURCE = "finn_no"
log = get_logger("job_search.ingest_finn")


_QUERY_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalized_words(text: str | None) -> list[str]:
    return _QUERY_TOKEN_RE.findall((text or "").casefold())


def _token_present(token: str, hay_token: str) -> bool:
    if len(token) <= 2:
        return hay_token == token
    return hay_token.startswith(token) or token in hay_token


def query_title_match_strength(query: str, title: str | None, employer: str | None = None) -> int:
    """2 = whole query phrase in title/employer, 1 = every query word present, 0 = no match.

    Search result cards with a title-level query match are the strongest signal that
    the ad is a real role for this search, even when its teaser has no CV keywords.
    """
    hay = _normalized_words(" ".join(part for part in (title, employer) if part))
    if not hay:
        return 0
    query_words = [w for w in _normalized_words(query) if len(w) >= 2]
    if not query_words:
        return 0
    phrase = " ".join(query_words)
    if f" {phrase} " in f" {' '.join(hay)} ":
        return 2
    if all(any(_token_present(word, hay_word) for hay_word in hay) for word in query_words):
        return 1
    return 0


def detail_fetch_priority(
    finnkode: str,
    *,
    known_uuids: set[str],
    missing_expires: set[str],
    thin_uuids: set[str] | None = None,
    query_match: dict[str, int] | None = None,
) -> tuple[int, str]:
    """Order detail fetches by relevance to the search query and card completeness."""
    strength = (query_match or {}).get(finnkode, 0)
    if strength >= 2:
        return (0, finnkode)
    if strength == 1:
        return (1, finnkode)
    if finnkode not in known_uuids:
        return (2, finnkode)
    if thin_uuids and finnkode in thin_uuids:
        return (3, finnkode)
    if finnkode in missing_expires:
        return (4, finnkode)
    return (5, finnkode)


def _newest_first(finnkode: str) -> int:
    """Tie-break detail fetches newest-first so recent ads are not starved."""
    return -int(finnkode) if finnkode.isdigit() else 0


def load_queries(args: argparse.Namespace) -> list[str]:
    if args.queries_file:
        text = Path(args.queries_file).read_text(encoding="utf-8")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if lines:
            return lines
    if args.queries:
        parts: list[str] = []
        for chunk in args.queries:
            parts.extend(q.strip() for q in chunk.split(",") if q.strip())
        if parts:
            return parts
    return list(finn_search_queries_for_track(getattr(args, "search_track", "both")))


def location_guess_rogaland(municipal: str | None, county: str | None) -> bool:
    muni = (municipal or "").strip().upper()
    cty = (county or "").strip().upper()
    if cty == ROGALAND_COUNTY:
        return True
    return bool(muni and muni in ROGALAND_MUNICIPAL)


def parse_location_guess(location_guess: str | None) -> tuple[str | None, str | None]:
    if not location_guess:
        return None, None
    parts = [p.strip() for p in location_guess.split(",") if p.strip()]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[-1]


def row_from_search_card(
    card: dict[str, str | None],
    *,
    fetched_at: str,
    keywords: list[str],
    preferred_locations: list[str],
    keyword_filter: bool,
    rogaland_only: bool,
    require_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...],
    force_keep: bool = False,
) -> dict[str, Any] | None:
    finnkode = card["finnkode"]
    title = (card.get("title") or "").strip()
    employer = (card.get("employer_guess") or "").strip() or None
    municipal_guess, county_guess = parse_location_guess(card.get("location_guess"))
    in_r = location_guess_rogaland(municipal_guess, county_guess)
    location_match = match_preferred_location(
        preferred_locations,
        municipal=municipal_guess,
        county=county_guess,
    )
    location_matched = location_match.matched or in_r

    snippet = (card.get("description_snippet") or "").strip()
    hay = haystack_for_filter(title, snippet, card.get("location_guess"), employer)
    hits = matching_terms(hay, keywords) if keywords else []

    if rogaland_only and not location_matched:
        return None
    if keyword_filter and not hits and not force_keep:
        return None
    if require_terms and not matches_any_include_term(
        haystack_for_filter(title, None, snippet or None, employer or ""),
        require_terms,
    ):
        return None
    if exclude_terms and matches_exclude_terms(
        haystack_for_filter(title, None, snippet or None, employer or ""),
        exclude_terms,
    ):
        return None

    return {
        "uuid": finnkode,
        "source": SOURCE,
        "status": "ACTIVE",
        "title": title or None,
        "jobtitle": None,
        "employer_name": employer,
        "employer_orgnr": None,
        "municipal": municipal_guess,
        "county": county_guess,
        "application_url": build_job_url(finnkode),
        "link": build_job_url(finnkode),
        "published": None,
        "expires": None,
        "updated": None,
        "description_text": snippet or None,
        "raw_json": json.dumps({"search_card": card}, ensure_ascii=False),
        "fetched_at": fetched_at,
        "in_rogaland": 1 if in_r else 0,
        "location_matched": 1 if location_matched else 0,
        "location_label": location_match.label or (ROGALAND_COUNTY.title() if in_r else None),
        "keyword_hits": ", ".join(hits) if hits else None,
        "feed_municipal": None,
    }


def row_from_detail(
    card: dict[str, str | None],
    detail: dict[str, Any],
    *,
    fetched_at: str,
    keywords: list[str],
    preferred_locations: list[str],
    keyword_filter: bool,
    rogaland_only: bool,
    require_terms: tuple[str, ...],
    exclude_terms: tuple[str, ...],
    force_keep: bool = False,
) -> dict[str, Any] | None:
    finnkode = card["finnkode"]
    title = (detail.get("title") or card.get("title") or "").strip()
    employer = (detail.get("employer_name") or card.get("employer_guess") or "").strip() or None
    desc_html = detail.get("description") or ""
    desc_text = strip_html(str(desc_html))[:20000] if desc_html else ""
    municipal = detail.get("municipal")
    county = detail.get("county")
    if not municipal and not county:
        municipal, county = parse_location_guess(card.get("location_guess"))

    in_r = location_guess_rogaland(municipal, county)
    location_match = match_preferred_location(
        preferred_locations,
        municipal=municipal,
        county=county,
    )
    location_matched = location_match.matched or in_r

    hay = haystack_for_filter(title, None, desc_text, employer)
    hits = matching_terms(hay, keywords) if keywords else []

    if rogaland_only and not location_matched:
        return None
    if keyword_filter and not hits and not force_keep:
        return None
    if require_terms and not matches_any_include_term(
        haystack_for_filter(title, None, desc_text, employer or ""),
        require_terms,
    ):
        return None
    if exclude_terms and matches_exclude_terms(
        haystack_for_filter(title, None, desc_text, employer or ""),
        exclude_terms,
    ):
        return None

    expires, status = expires_and_status_from_finn_detail(detail)

    return {
        "uuid": finnkode,
        "source": SOURCE,
        "status": status,
        "title": title or None,
        "jobtitle": None,
        "employer_name": employer,
        "employer_orgnr": None,
        "municipal": municipal,
        "county": county,
        "application_url": build_job_url(finnkode),
        "link": build_job_url(finnkode),
        "published": detail.get("datePosted"),
        "expires": expires,
        "updated": None,
        "description_text": desc_text or None,
        "raw_json": json.dumps({"search_card": card, "detail": detail.get("raw")}, ensure_ascii=False),
        "fetched_at": fetched_at,
        "in_rogaland": 1 if in_r else 0,
        "location_matched": 1 if location_matched else 0,
        "location_label": location_match.label or (ROGALAND_COUNTY.title() if in_r else None),
        "keyword_hits": ", ".join(hits) if hits else None,
        "feed_municipal": None,
    }


def gone_tombstone(
    finnkode: str,
    card: dict[str, str | None],
    *,
    fetched_at: str,
) -> dict[str, Any]:
    """Minimal INACTIVE row for an ad whose FINN detail page no longer exists.

    Storing a tombstone (rather than a storeable search card) keeps 404/410 ads
    out of the ACTIVE list; the status also survives the next stale-marking pass.
    """
    url = build_job_url(finnkode)
    return {
        "uuid": finnkode,
        "source": SOURCE,
        "status": "INACTIVE",
        "title": (card.get("title") or "").strip() or None,
        "employer_name": (card.get("employer_guess") or "").strip() or None,
        "application_url": url,
        "link": url,
        "expires": FINN_EXPIRED_SENTINEL,
        "description_text": None,
        "fetched_at": fetched_at,
    }


def run(args: argparse.Namespace) -> int:
    configure_logging(console=True)
    if args.list_keywords:
        for k in collect_ingest_keywords(
            args.keyword,
            include_skills=args.keyword_source == "keywords-and-skills",
            include_application_boosts=getattr(args, "application_boosts", None),
        ):
            print(k)
        return 0

    queries = load_queries(args)
    log.info(
        "FINN ingest start db=%s search_track=%s queries=%d max_pages=%d",
        Path(args.db) if args.db else DEFAULT_DB_PATH,
        getattr(args, "search_track", "both"),
        len(queries),
        args.max_pages,
    )
    profiles = load_default_profiles()
    preferred_locations = merged_preferred_locations(profiles)
    keywords = collect_ingest_keywords(
        args.keyword,
        include_skills=args.keyword_source == "keywords-and-skills",
        include_application_boosts=getattr(args, "application_boosts", None),
    )
    if not keywords:
        print("Note: no keywords from cv/*.md; pass --keyword or fill YAML lists.", file=sys.stderr)
        log.warning("no keywords from cv profiles; pass --keyword or fill YAML lists")

    require_terms: tuple[str, ...] = ()
    search_track = getattr(args, "search_track", "both")
    if search_track == "academic" and args.require_tech:
        require_terms = ACADEMIC_ROLE_TITLE_TERMS + ACADEMIC_RESEARCH_EMPLOYERS
        log.info(
            "academic FINN search track: using academic role allowlist (%d terms) instead of full ICT list",
            len(require_terms),
        )
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

    client = FinnJobSession(sleep_s=args.sleep_s, sleep_s_max=args.sleep_s_max)
    fetched_at = utc_now_iso()
    seen_uuids: set[str] = set()
    deduped_cards: dict[str, dict[str, str | None]] = {}
    query_match: dict[str, int] = {}
    query_match_rank: dict[str, tuple[int, int]] = {}
    n_search_pages = 0
    n_cards_seen = 0
    n_stored = 0
    n_details = 0
    n_gone = 0
    n_skip_noise = 0
    n_skip_not_tech = 0
    n_stale_inactivated = 0
    complete_query_walk = True

    for query_index, query in enumerate(queries):
        query_cards = 0
        log.info("FINN query start: %r", query)
        for page in range(1, args.max_pages + 1):
            n_search_pages += 1
            try:
                cards = client.search_jobs(query, page=page, employment=args.employment)
            except RuntimeError as e:
                print(f"Search error ({query!r} p{page}): {e}", file=sys.stderr)
                log.error("search failed query=%r page=%d: %s", query, page, e)
                complete_query_walk = False
                break
            if not cards:
                log.debug("query=%r page=%d: no cards", query, page)
                break
            new_on_page = 0
            for position, card in enumerate(cards, start=1):
                finnkode = card.get("finnkode")
                if not finnkode:
                    continue
                n_cards_seen += 1
                seen_uuids.add(finnkode)
                strength = query_title_match_strength(
                    query,
                    card.get("title"),
                    card.get("employer_guess"),
                )
                if strength:
                    rank = (query_index, (page - 1) * len(cards) + position)
                    best_rank = query_match_rank.get(finnkode)
                    if strength > query_match.get(finnkode, 0) or (
                        strength == query_match.get(finnkode, 0)
                        and (best_rank is None or rank < best_rank)
                    ):
                        query_match[finnkode] = strength
                        query_match_rank[finnkode] = rank
                if finnkode not in deduped_cards:
                    deduped_cards[finnkode] = card
                    query_cards += 1
                    new_on_page += 1
            log.debug(
                "query=%r page=%d cards=%d new=%d query_total=%d",
                query,
                page,
                len(cards),
                new_on_page,
                query_cards,
            )
            if new_on_page == 0:
                break
            if query_cards >= args.max_results_per_query:
                complete_query_walk = False
                break
        if query_cards >= args.max_results_per_query:
            continue
        log.info("FINN query done: %r unique_cards=%d", query, query_cards)

    conn = connect(Path(args.db) if args.db else None)
    init_schema(conn)

    fetch_details = args.fetch_details and not args.search_only
    detail_budget = args.max_details if fetch_details else 0
    detail_count = 0

    known_uuids: set[str] = set()
    missing_expires: set[str] = set()
    thin_uuids: set[str] = set()
    if fetch_details:
        known_rows = conn.execute(
            "SELECT uuid, expires, status, description_text FROM job_postings WHERE source = ?",
            (SOURCE,),
        ).fetchall()
        for r in known_rows:
            uuid = str(r["uuid"])
            known_uuids.add(uuid)
            status = (r["status"] or "").strip().upper()
            expires = (r["expires"] or "").strip()
            if status in ("", "ACTIVE") and not expires:
                missing_expires.add(uuid)
            desc_len = len((r["description_text"] or "").strip())
            if status in ("", "ACTIVE") and desc_len < MIN_FINN_DESCRIPTION_CHARS:
                thin_uuids.add(uuid)

    # Spend the limited detail budget on cards whose title/employer matches the
    # search query first, then new ads, then thin teaser cards (which the dashboard
    # cannot show without a real description), then deadline backfill.
    card_items = sorted(
        deduped_cards.items(),
        key=lambda item: (
            detail_fetch_priority(
                item[0],
                known_uuids=known_uuids,
                missing_expires=missing_expires,
                thin_uuids=thin_uuids,
                query_match=query_match,
            )[0],
            query_match_rank.get(item[0], (10**6, 10**6)),
            _newest_first(item[0]),
        ),
    )

    for finnkode, card in card_items:
        force_keep = finnkode in query_match
        row: dict[str, Any] | None
        if fetch_details and detail_count < detail_budget:
            try:
                detail = client.fetch_job_detail(finnkode)
            except JobGoneError as e:
                print(f"Gone {finnkode}: {e}", file=sys.stderr)
                log.info("gone finnkode=%s: %s", finnkode, e)
                n_gone += 1
                row = gone_tombstone(finnkode, card, fetched_at=fetched_at)
            except RuntimeError as e:
                print(f"Skip {finnkode}: {e}", file=sys.stderr)
                log.warning("skip detail finnkode=%s: %s", finnkode, e)
                row = row_from_search_card(
                    card,
                    fetched_at=fetched_at,
                    keywords=keywords,
                    preferred_locations=preferred_locations,
                    keyword_filter=args.keyword_filter,
                    rogaland_only=args.rogaland_only,
                    require_terms=require_terms,
                    exclude_terms=exclude_terms,
                    force_keep=force_keep,
                )
            else:
                n_details += 1
                detail_count += 1
                row = row_from_detail(
                    card,
                    detail,
                    fetched_at=fetched_at,
                    keywords=keywords,
                    preferred_locations=preferred_locations,
                    keyword_filter=args.keyword_filter,
                    rogaland_only=args.rogaland_only,
                    require_terms=require_terms,
                    exclude_terms=exclude_terms,
                    force_keep=force_keep,
                )
        else:
            row = row_from_search_card(
                card,
                fetched_at=fetched_at,
                keywords=keywords,
                preferred_locations=preferred_locations,
                keyword_filter=args.keyword_filter,
                rogaland_only=args.rogaland_only,
                require_terms=require_terms,
                exclude_terms=exclude_terms,
                force_keep=force_keep,
            )

        if row is None:
            if require_terms:
                n_skip_not_tech += 1
            elif exclude_terms:
                n_skip_noise += 1
            continue
        upsert_job(conn, row)
        n_stored += 1

    # Only stale-mark after a full default query walk. A custom --queries set
    # (e.g. employer-only) is a partial slice and must not inactivate the rest.
    used_custom_queries = bool(args.queries) or bool(getattr(args, "queries_file", "") or "")
    if complete_query_walk and seen_uuids and not used_custom_queries:
        n_stale_inactivated = mark_stale_jobs_inactive(
            conn,
            source=SOURCE,
            fetched_at=fetched_at,
            seen_uuids=seen_uuids,
        )
    if seen_uuids and args.use_ingest_state:
        set_state(conn, "finn_no:last_success_at", fetched_at)
    conn.commit()
    conn.close()

    summary = {
        "db": str(Path(args.db) if args.db else DEFAULT_DB_PATH),
        "queries": queries,
        "search_pages": n_search_pages,
        "cards_seen": n_cards_seen,
        "unique_finnkodes": len(deduped_cards),
        "stored_rows": n_stored,
        "detail_fetches": n_details,
        "gone_tombstones": n_gone,
        "preferred_locations": preferred_locations,
        "skipped_noise": n_skip_noise,
        "skipped_not_tech_allowlist": n_skip_not_tech,
        "stale_jobs_inactivated": n_stale_inactivated,
        "query_match_cards": len(query_match),
        "thin_cards_seen": len(thin_uuids.intersection(deduped_cards)),
        "thin_cards_total": len(thin_uuids),
        "complete_query_walk": complete_query_walk,
    }
    log.info(
        "FINN ingest done stored=%d detail_fetches=%d gone=%d skipped_noise=%d skipped_tech=%d stale=%d",
        n_stored,
        n_details,
        n_gone,
        n_skip_noise,
        n_skip_not_tech,
        n_stale_inactivated,
    )
    log_json_summary(log, "FINN ingest summary", summary)
    print(json.dumps(summary, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Ingest FINN.no jobs (search + JSON-LD detail)")
    p.add_argument("--db", default="", help=f"SQLite path (default: {DEFAULT_DB_PATH})")
    p.add_argument("--employment", default="fulltime", help="FINN employment path segment (default: fulltime)")
    p.add_argument("--max-pages", type=int, default=3, help="Max search pages per query")
    p.add_argument("--max-results-per-query", type=int, default=60, help="Stop paging a query after this many new finnkodes")
    p.add_argument("--max-details", type=int, default=40, help="Max detail page fetches when fetching details (keep low; FINN throttles)")
    p.add_argument(
        "--sleep-s",
        type=float,
        default=1.0,
        help="Minimum pause between FINN HTTP requests (default: 1.0s; actual delay is random up to --sleep-s-max)",
    )
    p.add_argument(
        "--sleep-s-max",
        type=float,
        default=None,
        help="Maximum pause between FINN requests (default: 2× --sleep-s)",
    )
    p.add_argument(
        "--fetch-details",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Fetch detail pages for JSON-LD descriptions (default: on)",
    )
    p.add_argument("--search-only", action="store_true", help="Only use search result cards (no detail fetch)")
    p.add_argument("--queries", action="append", default=[], help='Comma-separated queries (repeatable); default: built-in set')
    p.add_argument("--queries-file", default="", help="Text file with one query per line")
    p.add_argument(
        "--search-track",
        choices=("industry", "academic", "both"),
        default="both",
        help="Which built-in FINN query set to use when --queries/--queries-file are omitted (default: both)",
    )
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
        help="Keep ads that match a strong profile keyword/skill (default: on)",
    )
    p.add_argument(
        "--application-boosts",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Merge curated application-history keywords into the keep-gate "
            "(default: on for demo CV templates only; off for real profiles)"
        ),
    )
    p.add_argument("--rogaland-only", action="store_true", help="Keep only preferred/Rogaland locations")
    p.add_argument("--list-keywords", action="store_true", help="Print merged CV keywords and exit")
    p.add_argument(
        "--require-tech",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only store jobs matching >=1 ICT/AI/CS token (default: on)",
    )
    p.add_argument("--require-tech-no-defaults", action="store_true")
    p.add_argument("--include-tech", action="append", default=[], metavar="SUBSTR")
    p.add_argument(
        "--exclude-noise",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Skip jobs matching exclude/blocklist terms (default: on)",
    )
    p.add_argument("--exclude-noise-no-defaults", action="store_true")
    p.add_argument("--exclude", action="append", default=[], metavar="SUBSTR")
    p.add_argument(
        "--use-ingest-state",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Persist finn_no:last_success_at in ingest_state",
    )
    args = p.parse_args()
    if args.search_only:
        args.fetch_details = False
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
