"""Tests for preference label collection (no scoring side effects)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from job_search.job_db import connect, init_schema, upsert_application, upsert_job, upsert_score, utc_now_iso
from job_search.preference_collect import (
    build_preference_collection,
    collect_and_save,
    contrast_terms,
    load_labeled_jobs,
    load_preference_collection,
    normalize_employer,
    polarity_for_status,
    tokenize_text,
)
from collections import Counter


class PreferenceCollectTests(unittest.TestCase):
    def test_polarity_mapping(self) -> None:
        self.assertEqual(polarity_for_status("skipped"), "negative")
        self.assertEqual(polarity_for_status("rejected"), "negative")
        self.assertEqual(polarity_for_status("drafted"), "positive")
        self.assertEqual(polarity_for_status("applied"), "positive")
        self.assertEqual(polarity_for_status("withdrawn"), "ignored")
        self.assertIsNone(polarity_for_status("unknown"))

    def test_tokenize_and_employer(self) -> None:
        toks = tokenize_text("Senior Data Engineer — Graduate 2027")
        self.assertIn("senior", toks)
        self.assertIn("data", toks)
        self.assertIn("engineer", toks)
        self.assertIn("graduate", toks)
        self.assertNotIn("and", toks)
        self.assertEqual(normalize_employer("Capgemini Norge AS"), "capgemini")

    def test_contrast_terms_ranks_negative_leaning(self) -> None:
        neg = Counter({"graduate": 5, "python": 1})
        pos = Counter({"python": 4, "graduate": 0, "llm": 2})
        neg_rows, pos_rows = contrast_terms(neg, pos, min_neg=2, min_pos=1)
        self.assertEqual(neg_rows[0]["term"], "graduate")
        self.assertEqual(neg_rows[0]["contrast"], 5.0)
        pos_terms = {r["term"] for r in pos_rows}
        self.assertIn("llm", pos_terms)
        self.assertIn("python", pos_terms)

    def _seed(self, conn) -> None:
        now = utc_now_iso()
        jobs = [
            ("skip-1", "Graduate 2027 Operations", "Vår Energi AS", "skipped"),
            ("skip-2", "Graduate 2027 Project Control", "Vår Energi AS", "rejected"),
            ("good-1", "Senior Data Engineer", "Capgemini Norge AS", "interested"),
            ("good-2", "ML Engineer LLM platform", "Tech AS", "drafted"),
            ("out-1", "Something else", "Other AS", "withdrawn"),
        ]
        for uuid, title, employer, status in jobs:
            upsert_job(
                conn,
                {
                    "uuid": uuid,
                    "source": "finn_no",
                    "status": "ACTIVE",
                    "title": title,
                    "employer_name": employer,
                    "description_text": title,
                    "fetched_at": now,
                },
            )
            upsert_score(
                conn,
                {
                    "uuid": uuid,
                    "source": "finn_no",
                    "track": "industry",
                    "score_base": 2.0,
                    "boost_rogaland": 0.0,
                    "boost_tek": 0.0,
                    "score_total": 2.0,
                    "matched_keywords": "python" if status in {"interested", "drafted"} else "graduate",
                    "matched_skills": "llm" if "LLM" in title else None,
                    "scored_at": now,
                },
            )
            upsert_application(
                conn,
                {
                    "uuid": uuid,
                    "source": "finn_no",
                    "track": "industry",
                    "status": status,
                    "updated_at": now,
                },
            )
        conn.commit()

    def test_build_collection_from_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            conn = connect(Path(tmp) / "jobs.sqlite")
            init_schema(conn)
            self._seed(conn)
            labeled = load_labeled_jobs(conn, track="industry")
            self.assertEqual(len(labeled), 5)
            collection = build_preference_collection(conn, track="industry", min_neg=1)
            counts = collection["label_counts"]
            self.assertEqual(counts["negative"], 2)
            self.assertEqual(counts["positive"], 2)
            self.assertEqual(counts["ignored"], 1)
            neg_titles = {r["term"] for r in collection["title_stems"]["negative"]}
            self.assertIn("graduate", neg_titles)
            neg_emps = {r["term"] for r in collection["employers"]["negative"]}
            self.assertTrue(any("energi" in t or "vår" in t for t in neg_emps))

    def test_collect_and_save_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "jobs.sqlite"
            out = Path(tmp) / "prefs.json"
            conn = connect(db)
            init_schema(conn)
            self._seed(conn)
            collection, written = collect_and_save(conn, track="industry", path=out)
            self.assertEqual(written, out)
            self.assertTrue(out.is_file())
            loaded = load_preference_collection(out)
            assert loaded is not None
            self.assertEqual(loaded["label_counts"]["negative"], collection["label_counts"]["negative"])
            raw = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(raw["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
