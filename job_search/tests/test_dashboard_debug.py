"""Tests for dashboard debug tracing helpers."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search import dashboard_debug as dbg


class TestDashboardDebug(unittest.TestCase):
    def test_debug_log_appends_to_session_ring_buffer(self) -> None:
        session: dict = {}
        dbg.init_dashboard_debug(session)
        session[dbg.SESSION_ENABLED_KEY] = True
        dbg.debug_log("page_rerun", session_state=session, reason="full_render")
        dbg.debug_log("dialog_open", session_state=session, key="job_0")
        events = dbg.recent_debug_events(session)
        self.assertEqual(len(events), 2)
        self.assertIn("page_rerun", events[0])
        self.assertIn("dialog_open", events[1])

    def test_debug_log_redacts_sensitive_fields(self) -> None:
        session = {dbg.SESSION_ENABLED_KEY: True, dbg.SESSION_EVENTS_KEY: []}
        dbg.debug_log(
            "apply_modify_click",
            session_state=session,
            title="Engineer",
            description_text="secret jd body",
            notes="CV run: /Users/me/private/cv/deanonymized/foo",
        )
        line = session[dbg.SESSION_EVENTS_KEY][0]
        self.assertIn("Engineer", line)
        self.assertNotIn("secret jd body", line)
        self.assertIn("[redacted]", line)

    def test_env_var_enables_debug(self) -> None:
        session: dict = {}
        with patch.dict("os.environ", {"JOB_SEARCH_DEBUG": "1"}):
            dbg.init_dashboard_debug(session)
            self.assertTrue(dbg.is_debug_enabled(session))
            dbg.debug_log("page_rerun", session_state=session, reason="ingest")
            self.assertEqual(len(session[dbg.SESSION_EVENTS_KEY]), 1)

    def test_debug_log_writes_file_when_enabled(self) -> None:
        session = {dbg.SESSION_ENABLED_KEY: True, dbg.SESSION_EVENTS_KEY: []}
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "dashboard_debug.log"
            with patch.object(dbg, "DEBUG_LOG_PATH", log_path):
                dbg.debug_log("filter_change", session_state=session, stage="explorer")
            self.assertTrue(log_path.is_file())
            self.assertIn("filter_change", log_path.read_text(encoding="utf-8"))

    def test_start_rerun_trace_attaches_rerun_id_and_scope(self) -> None:
        session = {}
        dbg.init_dashboard_debug(session)
        session[dbg.SESSION_ENABLED_KEY] = True
        ctx = dbg.start_rerun_trace(session, scope="main", trigger="full_render", force_new=True)
        dbg.debug_log("page_rerun", session_state=session, reason="full_render")
        record = dbg.recent_debug_records(session)[-1]
        self.assertEqual(record["rerun_id"], ctx["rerun_id"])
        self.assertEqual(record["scope"], "main")

    def test_log_state_diff_records_only_changes(self) -> None:
        session = {dbg.SESSION_ENABLED_KEY: True}
        dbg.init_dashboard_debug(session)
        session["cv_track"] = "industry"
        self.assertEqual(dbg.log_state_diff(session), {"cv_track": {"before": None, "after": "industry"}})
        self.assertEqual(dbg.log_state_diff(session), {})
        session["cv_track"] = "academic"
        changed = dbg.log_state_diff(session)
        self.assertEqual(changed["cv_track"]["before"], "industry")
        self.assertEqual(changed["cv_track"]["after"], "academic")

    def test_summarize_recent_reruns_groups_events(self) -> None:
        session = {dbg.SESSION_ENABLED_KEY: True}
        dbg.init_dashboard_debug(session)
        dbg.start_rerun_trace(session, scope="main", trigger="full_render", force_new=True)
        dbg.debug_log("state_diff", session_state=session, changed_keys=["cv_track"])
        dbg.debug_log("render_timing", session_state=session, label="main_render", duration_ms=12.5)
        summary = dbg.summarize_recent_reruns(session)
        self.assertEqual(summary[0]["scope"], "main")
        self.assertEqual(summary[0]["trigger"], "full_render")
        self.assertIn("cv_track", summary[0]["state_changes"])
        self.assertIn("main_render 12.5ms", summary[0]["expensive"])


if __name__ == "__main__":
    unittest.main()
