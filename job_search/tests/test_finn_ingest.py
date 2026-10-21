from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from job_search.finn_job_client import (
    FinnJobSession,
    JobGoneError,
    build_job_url,
    build_search_url,
    extract_finnkode,
    parse_job_detail_html,
    parse_job_posting_json_ld,
    parse_search_cards,
)
from job_search.finn_search_queries import DEFAULT_FINN_SEARCH_QUERIES
from job_search.ingest_common import mark_stale_jobs_inactive
from job_search.ingest_finn_jobs import (
    detail_fetch_priority,
    gone_tombstone,
    load_queries,
    query_title_match_strength,
    row_from_detail,
    row_from_search_card,
)
from job_search.job_db import connect, init_schema, upsert_job

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "finn"


class FinnIngestTests(unittest.TestCase):
    def test_build_search_url(self) -> None:
        self.assertIn("q=data+engineer", build_search_url("data engineer"))
        self.assertIn("page=2", build_search_url("data engineer", page=2))

    def test_extract_finnkode(self) -> None:
        self.assertEqual(extract_finnkode("https://www.finn.no/job/ad/465089104"), "465089104")
        self.assertIsNone(extract_finnkode("/job/other"))

    def test_parse_search_cards_dedupes_and_extracts_fields(self) -> None:
        html = (FIXTURES / "search_results.html").read_text(encoding="utf-8")
        cards = parse_search_cards(html)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["finnkode"], "465089104")
        self.assertEqual(cards[0]["title"], "ML / AI Engineer")
        self.assertEqual(cards[0]["employer_guess"], "Falkor AS")
        self.assertEqual(cards[0]["location_guess"], "Oslo")
        self.assertEqual(cards[1]["finnkode"], "465089105")

    def test_parse_job_posting_json_ld(self) -> None:
        html = (FIXTURES / "job_detail.html").read_text(encoding="utf-8")
        parsed = parse_job_posting_json_ld(html)
        assert parsed is not None
        self.assertEqual(parsed["title"], "ML / AI Engineer")
        self.assertEqual(parsed["employer_name"], "Falkor AS")
        self.assertEqual(parsed["municipal"], "Oslo")
        self.assertEqual(parsed["county"], "Oslo")
        self.assertEqual(parsed["datePosted"], "2026-07-01")
        self.assertEqual(parsed["validThrough"], "2026-08-15")
        self.assertIn("machine learning", parsed["description"])

    def test_parse_wrapped_json_ld_job_posting(self) -> None:
        html = (FIXTURES / "job_detail_wrapped_ld.json.html").read_text(encoding="utf-8")
        parsed = parse_job_posting_json_ld(html)
        assert parsed is not None
        self.assertEqual(parsed["title"], "Wrapped ML Engineer")
        self.assertEqual(parsed["employer_name"], "Wrapped Corp")
        self.assertEqual(parsed["municipal"], "Bergen")

    def test_parse_job_detail_html_fallback(self) -> None:
        html = (FIXTURES / "job_detail_html_only.html").read_text(encoding="utf-8")
        parsed = parse_job_detail_html(html)
        assert parsed is not None
        self.assertEqual(parsed["title"], "ML/AI Engineer")
        self.assertEqual(parsed["employer_name"], "Piano Software Norway")
        self.assertEqual(parsed["municipal"], "Oslo")
        self.assertEqual(parsed["datePosted"], "2026-05-27")
        self.assertEqual(parsed["validThrough"], "20.6.2026")
        self.assertFalse(parsed["listingExpired"])
        self.assertIn("machine learning", parsed["description"] or "")

    def test_parse_soknadsfrist_and_expired_badge(self) -> None:
        from job_search.finn_job_client import (
            FINN_EXPIRED_SENTINEL,
            extract_valid_through_from_html,
            finn_listing_deadline_expired,
        )

        html = (
            '<section><w-badge>Fristen er utløpt</w-badge></section>'
            "<ul><li>Søknadsfrist<!-- --> "
            '<span class="mt-2 font-bold">16.8.2026</span></li></ul>'
        )
        self.assertEqual(extract_valid_through_from_html(html), "16.8.2026")
        self.assertTrue(finn_listing_deadline_expired(html))
        parsed = parse_job_detail_html(
            "<html><body><h1>AI Lead</h1>" + html + "</body></html>"
        )
        assert parsed is not None
        self.assertEqual(parsed["validThrough"], "16.8.2026")
        self.assertTrue(parsed["listingExpired"])

    def test_expired_badge_with_snarest_sets_sentinel(self) -> None:
        from job_search.finn_job_client import (
            FINN_EXPIRED_SENTINEL,
            extract_valid_through_from_html,
        )

        html = (
            "<html><body><h1>R&D Engineer</h1>"
            "<w-badge>Fristen er utløpt</w-badge>"
            "<ul><li>Søknadsfrist<!-- --> "
            '<span class="mt-2 font-bold">Snarest</span></li></ul>'
            "</body></html>"
        )
        self.assertEqual(extract_valid_through_from_html(html), FINN_EXPIRED_SENTINEL)
        parsed = parse_job_detail_html(html)
        assert parsed is not None
        self.assertEqual(parsed["validThrough"], FINN_EXPIRED_SENTINEL)
        self.assertTrue(parsed["listingExpired"])

    def test_soknadsfrist_regex_does_not_catastrophically_backtrack(self) -> None:
        """Regression: nested tag quantifiers + DOTALL hung refresh for hours."""
        import time

        from job_search.finn_job_client import extract_valid_through_from_html

        # Large HTML with Søknadsfrist but no date — old regex could spin forever.
        junk = "<span class='x'>" * 8000 + "</span>" * 8000
        html = f"<html><body><h1>Job</h1>Søknadsfrist {junk} Snarest</body></html>"
        t0 = time.perf_counter()
        result = extract_valid_through_from_html(html)
        elapsed = time.perf_counter() - t0
        self.assertIsNone(result)
        self.assertLess(elapsed, 1.0, f"deadline extract took {elapsed:.2f}s")

    def test_row_from_detail_maps_listing_expired_without_date(self) -> None:
        card = {
            "finnkode": "471127093",
            "title": "AI Lead",
            "employer_guess": "Mojob",
            "location_guess": "Oslo",
            "url": build_job_url("471127093"),
        }
        row = row_from_detail(
            card,
            {
                "title": "AI Lead",
                "employer_name": "Mojob",
                "description": "Hiring AI lead for marketplace.",
                "municipal": "Oslo",
                "county": "Oslo",
                "datePosted": "2026-07-28",
                "validThrough": None,
                "listingExpired": True,
                "raw": {},
            },
            fetched_at="2026-08-26T10:00:00+00:00",
            keywords=["python", "ai"],
            preferred_locations=["Oslo"],
            keyword_filter=False,
            rogaland_only=False,
            require_terms=(),
            exclude_terms=(),
        )
        assert row is not None
        from job_search.finn_job_client import FINN_EXPIRED_SENTINEL

        self.assertEqual(row["expires"], FINN_EXPIRED_SENTINEL)
        self.assertEqual(row["status"], "INACTIVE")

    def test_row_from_detail_keeps_active_for_future_deadline(self) -> None:
        card = {
            "finnkode": "465089104",
            "title": "ML / AI Engineer",
            "employer_guess": "Falkor AS",
            "location_guess": "Oslo",
            "url": build_job_url("465089104"),
        }
        row = row_from_detail(
            card,
            {
                "title": "ML / AI Engineer",
                "employer_name": "Falkor AS",
                "description": "Build ML systems.",
                "validThrough": "2099-01-01",
                "listingExpired": False,
                "raw": {},
            },
            fetched_at="2026-07-13T10:00:00+00:00",
            keywords=["python"],
            preferred_locations=["Oslo"],
            keyword_filter=False,
            rogaland_only=False,
            require_terms=(),
            exclude_terms=(),
        )
        assert row is not None
        self.assertEqual(row["expires"], "2099-01-01")
        self.assertEqual(row["status"], "ACTIVE")

    def test_parse_search_cards_live_markup(self) -> None:
        html = (FIXTURES / "search_results_live.html").read_text(encoding="utf-8")
        cards = parse_search_cards(html)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0]["finnkode"], "465089105")
        self.assertEqual(cards[0]["employer_guess"], "Northline Data")
        self.assertEqual(cards[0]["location_guess"], "Stavanger")
        self.assertIn("data pipelines", cards[0]["description_snippet"] or "")

    def test_row_from_detail_maps_db_fields(self) -> None:
        html = (FIXTURES / "job_detail.html").read_text(encoding="utf-8")
        detail = parse_job_posting_json_ld(html)
        assert detail is not None
        card = {
            "finnkode": "465089104",
            "title": "ML / AI Engineer",
            "employer_guess": "Falkor AS",
            "location_guess": "Oslo",
            "url": build_job_url("465089104"),
        }
        row = row_from_detail(
            card,
            {**detail, "finnkode": "465089104", "url": build_job_url("465089104")},
            fetched_at="2026-07-13T10:00:00+00:00",
            keywords=["python", "machine learning"],
            preferred_locations=["Oslo"],
            keyword_filter=True,
            rogaland_only=False,
            require_terms=("machine learning",),
            exclude_terms=(),
        )
        assert row is not None
        self.assertEqual(row["uuid"], "465089104")
        self.assertEqual(row["source"], "finn_no")
        self.assertEqual(row["link"], "https://www.finn.no/job/ad/465089104")
        self.assertEqual(row["employer_name"], "Falkor AS")
        self.assertIn("machine learning", row["description_text"] or "")
        self.assertEqual(row["location_matched"], 1)

    def test_row_from_search_card_without_detail(self) -> None:
        card = {
            "finnkode": "465089105",
            "title": "Data Engineer",
            "employer_guess": "Northline Data",
            "location_guess": "Stavanger, Rogaland",
            "description_snippet": "Design data pipelines for analytics workloads.",
            "url": build_job_url("465089105"),
        }
        row = row_from_search_card(
            card,
            fetched_at="2026-07-13T10:00:00+00:00",
            keywords=["data engineer"],
            preferred_locations=["Rogaland"],
            keyword_filter=True,
            rogaland_only=False,
            require_terms=("data engineer",),
            exclude_terms=(),
        )
        assert row is not None
        self.assertEqual(row["uuid"], "465089105")
        self.assertEqual(row["source"], "finn_no")
        self.assertIn("data pipelines", row["description_text"] or "")

    def test_sparse_search_card_without_cv_keyword_is_dropped(self) -> None:
        """Card teasers must now carry a real CV keyword hit to be stored."""
        card = {
            "finnkode": "475971035",
            "title": "Graduate 2027 - Data Scientist",
            "employer_guess": "DNV AS",
            "location_guess": "Oslo - Sentrum",
            "description_snippet": (
                "Are you ready to kickstart your career as a Data Scientist in DNV? "
                "We are seeking Graduates to join our team in 2027!"
            ),
            "url": build_job_url("475971035"),
        }
        row = row_from_search_card(
            card,
            fetched_at="2026-09-09T12:00:00+00:00",
            keywords=["Python", "machine learning"],
            preferred_locations=["Oslo"],
            keyword_filter=True,
            rogaland_only=False,
            require_terms=("data scientist", "machine learning"),
            exclude_terms=(),
        )
        self.assertIsNone(row)

    def test_gone_tombstone_is_inactive_with_link(self) -> None:
        card = {"finnkode": "475971035", "title": "Data Scientist", "employer_guess": "DNV AS"}
        row = gone_tombstone("475971035", card, fetched_at="2026-09-09T12:00:00+00:00")
        self.assertEqual(row["status"], "INACTIVE")
        self.assertEqual(row["uuid"], "475971035")
        self.assertEqual(row["source"], "finn_no")
        self.assertEqual(row["link"], build_job_url("475971035"))
        self.assertIsNone(row["description_text"])

    def test_fetch_detail_without_content_raises_job_gone(self) -> None:
        session = FinnJobSession(sleep_s=0)
        with patch.object(session, "fetch_text", return_value="<html><body>Not a job</body></html>"):
            with self.assertRaises(JobGoneError):
                session.fetch_job_detail("475971035")

    def test_long_search_card_still_requires_keyword_hit(self) -> None:
        long_snippet = ("x" * 300) + " collaborative culture and career growth."
        card = {
            "finnkode": "999000001",
            "title": "Data Scientist",
            "employer_guess": "Example AS",
            "location_guess": "Oslo",
            "description_snippet": long_snippet,
            "url": build_job_url("999000001"),
        }
        row = row_from_search_card(
            card,
            fetched_at="2026-09-09T12:00:00+00:00",
            keywords=["Python", "machine learning"],
            preferred_locations=["Oslo"],
            keyword_filter=True,
            rogaland_only=False,
            require_terms=("data scientist",),
            exclude_terms=(),
        )
        self.assertIsNone(row)

    def test_detail_fetch_priority_prefers_new_over_missing_expires(self) -> None:
        known = {"old1", "old2"}
        missing = {"old1"}
        ordered = sorted(
            ["old2", "new1", "old1"],
            key=lambda fk: detail_fetch_priority(
                fk, known_uuids=known, missing_expires=missing
            ),
        )
        self.assertEqual(ordered, ["new1", "old1", "old2"])

    def test_detail_fetch_priority_prefers_thin_teaser_rows(self) -> None:
        known = {"old1", "old2", "thin"}
        missing = {"old1"}
        thin = {"thin"}
        ordered = sorted(
            ["old1", "thin", "new1"],
            key=lambda fk: detail_fetch_priority(
                fk,
                known_uuids=known,
                missing_expires=missing,
                thin_uuids=thin,
            ),
        )
        self.assertEqual(ordered, ["new1", "thin", "old1"])

    def test_query_title_match_detects_aker_pattern(self) -> None:
        self.assertEqual(
            query_title_match_strength(
                "data scientist", "Senior Data Scientist", "Aker Solutions AS"
            ),
            2,
        )
        self.assertEqual(
            query_title_match_strength(
                "AI engineer", "AI Platform & Infrastructure Engineer", "Aker Solutions AS"
            ),
            1,
        )
        self.assertEqual(
            query_title_match_strength(
                "data scientist", "Instrument Engineer", "Aker Solutions AS"
            ),
            0,
        )

    def test_detail_fetch_priority_puts_query_matches_before_generic_new_ads(self) -> None:
        ordered = sorted(
            ["generic-new", "token-match", "phrase-match"],
            key=lambda fk: detail_fetch_priority(
                fk,
                known_uuids=set(),
                missing_expires=set(),
                query_match={"phrase-match": 2, "token-match": 1},
            ),
        )
        self.assertEqual(ordered, ["phrase-match", "token-match", "generic-new"])

    def test_force_keep_stores_query_match_without_teaser_keyword(self) -> None:
        card = {
            "finnkode": "478002572",
            "title": "Senior Data Scientist",
            "employer_guess": "Aker Solutions AS",
            "location_guess": "Lysaker",
            "description_snippet": "Apply AI where engineering meets industry",
        }
        kwargs = dict(
            fetched_at="2026-10-21T10:00:00+00:00",
            keywords=["Python", "machine learning"],
            preferred_locations=["Rogaland"],
            keyword_filter=True,
            rogaland_only=False,
            require_terms=(),
            exclude_terms=(),
        )
        self.assertIsNone(row_from_search_card(card, **kwargs))
        kept = row_from_search_card(card, force_keep=True, **kwargs)
        assert kept is not None
        self.assertEqual(kept["uuid"], "478002572")

    def test_mark_stale_jobs_inactive_for_finn_no(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            conn = connect(Path(tmp_dir) / "jobs.sqlite")
            init_schema(conn)
            base = {
                "source": "finn_no",
                "status": "ACTIVE",
                "title": "Title",
                "fetched_at": "2026-07-08T10:00:00+00:00",
            }
            upsert_job(conn, {"uuid": "seen", **base})
            upsert_job(conn, {"uuid": "stale", **base})
            updated = mark_stale_jobs_inactive(
                conn,
                source="finn_no",
                fetched_at="2026-07-09T10:00:00+00:00",
                seen_uuids={"seen"},
            )
            rows = {
                row["uuid"]: row["status"]
                for row in conn.execute("SELECT uuid, status FROM job_postings").fetchall()
            }
            self.assertEqual(updated, 1)
            self.assertEqual(rows["seen"], "ACTIVE")
            self.assertEqual(rows["stale"], "INACTIVE")

    def test_default_queries_cover_application_lanes(self) -> None:
        joined = " ".join(DEFAULT_FINN_SEARCH_QUERIES).casefold()
        for term in (
            "data engineer",
            "AI engineer",
            "software engineer",
            "agentic AI",
            "RAG",
            "platform engineer",
            "AI platform engineer",
        ):
            self.assertIn(term.casefold(), joined)

    def test_load_queries_prefers_cli_over_defaults(self) -> None:
        class Args:
            queries = ["data engineer, platform engineer"]
            queries_file = ""

        self.assertEqual(load_queries(Args()), ["data engineer", "platform engineer"])

    def test_finn_session_uses_fixture_html(self) -> None:
        search_html = (FIXTURES / "search_results.html").read_text(encoding="utf-8")
        detail_html = (FIXTURES / "job_detail.html").read_text(encoding="utf-8")
        html_only = (FIXTURES / "job_detail_html_only.html").read_text(encoding="utf-8")
        session = FinnJobSession(sleep_s=0)

        with patch.object(session, "fetch_text", side_effect=[search_html, detail_html]):
            cards = session.search_jobs("data engineer")
            detail = session.fetch_job_detail("465089104")

        self.assertEqual(len(cards), 2)
        self.assertEqual(detail["employer_name"], "Falkor AS")

        with patch.object(session, "fetch_text", return_value=html_only):
            detail = session.fetch_job_detail("465089104")
        self.assertIn("machine learning", detail["description"] or "")

    def test_rate_limit_uses_time_module(self) -> None:
        """Regression: _rate_limit must call time.monotonic / time.sleep (needs import time)."""
        session = FinnJobSession(sleep_s=0.25, sleep_s_max=0.25)
        with patch("job_search.finn_job_client.random.uniform", return_value=0.25):
            with patch(
                "job_search.finn_job_client.time.monotonic",
                side_effect=[100.0, 100.0, 100.5],
            ):
                with patch("job_search.finn_job_client.time.sleep") as sleep_mock:
                    session._rate_limit()  # first request: no wait, schedules delay
                    session._rate_limit()  # second: wait remaining of 0.25
                    sleep_mock.assert_called_once_with(0.25)
        self.assertEqual(session._last_request_at, 100.5)

    def test_rate_limit_randomizes_within_range(self) -> None:
        session = FinnJobSession(sleep_s=1.0, sleep_s_max=3.0)
        with patch("job_search.finn_job_client.random.uniform", return_value=2.4) as uni:
            with patch("job_search.finn_job_client.time.monotonic", return_value=50.0):
                with patch("job_search.finn_job_client.time.sleep"):
                    session._rate_limit()
        uni.assert_called_once_with(1.0, 3.0)
        self.assertEqual(session._next_delay_s, 2.4)

    def test_fetch_text_invokes_rate_limit(self) -> None:
        session = FinnJobSession(sleep_s=0.1)
        with patch.object(session, "_rate_limit") as rate_limit:
            with patch(
                "job_search.finn_job_client.http_get_text",
                return_value=("<html/>", {}),
            ):
                body = session.fetch_text("https://www.finn.no/job/search")
        rate_limit.assert_called_once_with()
        self.assertEqual(body, "<html/>")


if __name__ == "__main__":
    unittest.main()
