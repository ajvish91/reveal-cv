from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from job_search.finn_job_client import (
    FinnJobSession,
    build_job_url,
    build_search_url,
    extract_finnkode,
    parse_job_detail_html,
    parse_job_posting_json_ld,
    parse_search_cards,
)
from job_search.finn_search_queries import DEFAULT_FINN_SEARCH_QUERIES
from job_search.ingest_common import mark_stale_jobs_inactive
from job_search.ingest_finn_jobs import load_queries, row_from_detail, row_from_search_card
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
        self.assertIn("machine learning", parsed["description"] or "")

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


if __name__ == "__main__":
    unittest.main()
