"""API tests for the Bootstrap job-search UI (FastAPI TestClient)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.job_db import connect, init_schema, upsert_job, upsert_score, utc_now_iso


class TestWebApi(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "jobs.sqlite"
        conn = connect(self.db_path)
        init_schema(conn)
        now = utc_now_iso()
        upsert_job(
            conn,
            {
                "uuid": "job-1",
                "source": "nav_arbeidsplassen",
                "title": "ML Engineer",
                "employer_name": "Acme",
                "status": "ACTIVE",
                "fetched_at": now,
                "expires": "2099-01-01",
                "description_text": "Python and machine learning.",
            },
        )
        upsert_score(
            conn,
            {
                "uuid": "job-1",
                "source": "nav_arbeidsplassen",
                "track": "industry",
                "score_base": 40.0,
                "boost_rogaland": 0.0,
                "boost_tek": 0.0,
                "score_total": 40.0,
                "scored_at": now,
                "matched_keywords": "python",
                "matched_skills": "ml",
            },
        )
        conn.commit()
        conn.close()
        self.env = patch.dict(os.environ, {"JOBS_DB": str(self.db_path)})
        self.env.start()
        from fastapi.testclient import TestClient

        from job_search.web.app import app

        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_health_and_meta(self) -> None:
        health = self.client.get("/api/health").json()
        self.assertTrue(health["ok"])
        self.assertTrue(health["db_exists"])
        meta = self.client.get("/api/meta").json()
        self.assertTrue(meta["defaults"]["hide_expired"])
        self.assertIn("industry", meta["tracks"])

    def test_stale_streamlit_probes_are_no_content(self) -> None:
        self.assertEqual(self.client.get("/_stcore/health").status_code, 204)
        self.assertEqual(self.client.get("/_stcore/host-config").status_code, 204)
        self.assertEqual(
            self.client.get("/3_3_Run_Simulation/_stcore/health").status_code, 204
        )

    def test_index_serves_bootstrap_page(self) -> None:
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("Job explorer", res.text)
        self.assertIn("hide-expired", res.text)
        self.assertIn("bootstrap", res.text.lower())
        self.assertIn("container-xl", res.text)
        self.assertNotIn("container-fluid", res.text)

    def test_metric_cards_close_column_wrappers(self) -> None:
        js = self.client.get("/static/js/app.js").text
        start = js.index(".map(([label, val])")
        end = js.index(".join(\"\")", start)
        snippet = js[start:end]
        self.assertEqual(snippet.count("<div"), snippet.count("</div>"))
        self.assertIn("col-12", snippet)

    def test_jobs_list_and_detail(self) -> None:
        data = self.client.get("/api/jobs?track=industry&hide_expired=true").json()
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["jobs"][0]["uuid"], "job-1")
        self.assertIn("Hide expired", data["chips"])
        detail = self.client.get("/api/jobs/nav_arbeidsplassen/job-1?track=industry").json()
        self.assertEqual(detail["title"], "ML Engineer")
        self.assertIn("Python", detail["description_text"])

    def test_overview(self) -> None:
        data = self.client.get("/api/overview?track=industry").json()
        self.assertGreaterEqual(data["metrics"]["n_active"], 1)

    def test_jobs_search_and_pagination_fields(self) -> None:
        hit = self.client.get("/api/jobs?track=industry&hide_expired=true&q=python").json()
        self.assertEqual([j["uuid"] for j in hit["jobs"]], ["job-1"])
        miss = self.client.get("/api/jobs?track=industry&hide_expired=true&q=zzzznope").json()
        self.assertEqual(miss["total"], 0)
        for key in ("page", "pages", "page_size", "total"):
            self.assertIn(key, hit)
        self.assertEqual(hit["pages"], 1)

    def test_ingest_conflict_while_idle_starts(self) -> None:
        from job_search.web import runtime

        with patch.object(runtime, "start_ingest", return_value=(False, "Ingest is already running.")):
            res = self.client.post("/api/ingest", json={})
            self.assertEqual(res.status_code, 409)


if __name__ == "__main__":
    unittest.main()
