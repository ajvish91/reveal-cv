"""Tests for dashboard Applied roles helpers (no Streamlit import)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from job_search.dashboard import (
    APPLIED_ROLE_ROW_COLUMNS,
    DEFAULT_APPLIED_STATUS_FILTER,
    DEFAULT_DEDUPE_CROSS_SOURCE,
    DEFAULT_DRAFTS_STATUS_FILTER,
    DEFAULT_HIDE_APPLIED,
    DRAFTS_STATUS_OPTIONS,
    HIDE_APPLIED_STATUSES,
    JOB_EXPLORER_ROW_COLUMNS,
    LOG_DELETE_BUTTON_COLUMNS,
    MODIFY_STATUSES,
    PIPELINE_MAX_IN_FLIGHT,
    PIPELINE_MAX_WAITING,
    PIPELINE_TOTAL_STEPS,
    ApplyPipelineOptions,
    application_status_upsert_row,
    apply_button_label,
    apply_dialog_ready,
    build_explorer_filter_chips,
    build_pipeline_queue_item,
    bulk_deanonymize_command,
    can_enqueue_pipeline,
    default_artifact_options,
    dequeue_pipeline_item,
    enqueue_pipeline_item,
    extract_run_ids_from_notes,
    filter_applied_roles_df,
    is_modify_mode,
    load_applied_roles_df,
    load_jobs_df,
    pipeline_active_for_job_key,
    pipeline_fallback_eligible,
    pipeline_job_display_title,
    pipeline_notice_id,
    pipeline_phase_is_busy,
    pipeline_queue_display_titles,
    pipeline_queue_is_full,
    pipeline_queue_remaining,
    pipeline_queue_slots_used,
    pipeline_result_details,
    pipeline_metrics_summary_for_notes,
    pipeline_stage_label,
    pipeline_stage_number,
    reconcile_apply_dialog_flags,
    resolve_project_python,
    row_dict_for_apply_from_app,
    row_suggests_academic_documents,
    status_badge_markdown,
    yield_to_apply_modify_dialog,
    _count_applied_roles,
    _dialog_artifact_bundle,
    _explorer_jobs_cache_fingerprint,
    _subprocess_env,
)
from job_search.dashboard_styles import (
    _JOB_LIST_ANCHOR_ID,
    _SCROLL_FORCE_RESTORE_JS,
    _SCROLL_RESTORE_JS,
    _SCROLL_STORAGE_KEY,
    _SCROLL_TO_JOB_LIST_JS,
    _SCROLL_TO_LIST_FN,
)
from job_search.job_db import connect, init_schema, upsert_application, upsert_job, upsert_score, utc_now_iso


class TestPipelineStageNumber(unittest.TestCase):
    def test_extracts_step_index(self) -> None:
        self.assertEqual(pipeline_stage_number("3/11 Parse job description"), 3)
        self.assertEqual(pipeline_stage_number("9/11 Cover letter"), 9)
        self.assertEqual(pipeline_stage_number("11/11 Complete — run `foo`"), 11)
        self.assertEqual(PIPELINE_TOTAL_STEPS, 11)

    def test_unknown_label_returns_zero(self) -> None:
        self.assertEqual(pipeline_stage_number("Agent pipeline failed"), 0)
        self.assertEqual(pipeline_stage_number(""), 0)

    def test_stage_label_maps_wrote_lines(self) -> None:
        self.assertEqual(
            pipeline_stage_label("Wrote: 01_jd_parser_output.json"),
            "3/11 Parse job description",
        )
        self.assertEqual(
            pipeline_stage_label("Wrote: 04_bullet_tailor_output.json"),
            "6/11 Tailor bullets",
        )


class TestSubprocessEnv(unittest.TestCase):
    def test_forces_python_unbuffered(self) -> None:
        self.assertEqual(_subprocess_env().get("PYTHONUNBUFFERED"), "1")


class TestResolveProjectPython(unittest.TestCase):
    def test_explicit_overrides_venv(self) -> None:
        self.assertEqual(resolve_project_python("/usr/bin/python3"), "/usr/bin/python3")

    def test_prefers_repo_venv_when_present(self) -> None:
        resolved = resolve_project_python()
        venv_python = REPO / ".venv" / "bin" / "python"
        venv_python3 = REPO / ".venv" / "bin" / "python3"
        if venv_python.is_file() or venv_python3.is_file():
            self.assertTrue(
                resolved == str(venv_python) or resolved == str(venv_python3),
                msg=f"expected project venv python, got {resolved!r}",
            )
        else:
            self.assertEqual(resolved, sys.executable)


class TestScrollRestorationScript(unittest.TestCase):
    def test_scroll_script_targets_session_storage_and_st_main(self) -> None:
        self.assertEqual(_SCROLL_STORAGE_KEY, "job_search_dashboard_scrollY")
        self.assertIn(_SCROLL_STORAGE_KEY, _SCROLL_RESTORE_JS)
        self.assertIn("sessionStorage", _SCROLL_RESTORE_JS)
        self.assertIn('data-testid="stMain"', _SCROLL_RESTORE_JS)
        self.assertIn("pagehide", _SCROLL_RESTORE_JS)
        self.assertIn("stAppViewContainer", _SCROLL_RESTORE_JS)

    def test_pagination_scroll_hook_targets_job_list_anchor(self) -> None:
        self.assertEqual(_JOB_LIST_ANCHOR_ID, "job-explorer-list-start")
        self.assertEqual(_SCROLL_TO_LIST_FN, "__jobSearchScrollToJobList")
        self.assertIn(_SCROLL_TO_LIST_FN, _SCROLL_RESTORE_JS)
        self.assertIn(_JOB_LIST_ANCHOR_ID, _SCROLL_RESTORE_JS)
        self.assertIn(_SCROLL_TO_LIST_FN, _SCROLL_TO_JOB_LIST_JS)
        self.assertIn("explorer-results-header", _SCROLL_RESTORE_JS)
        self.assertIn("shouldPersistScroll", _SCROLL_RESTORE_JS)

    def test_scroll_save_skips_minimal_pages_without_job_list(self) -> None:
        self.assertIn("findJobListAnchor", _SCROLL_RESTORE_JS)
        self.assertIn("if (!shouldPersistScroll()) return;", _SCROLL_RESTORE_JS)

    def test_force_restore_resets_restore_scheduled_after_dialog(self) -> None:
        self.assertIn('ACTION === "forceRestore"', _SCROLL_FORCE_RESTORE_JS)
        self.assertIn("mgr.restoreScheduled = false", _SCROLL_FORCE_RESTORE_JS)
        self.assertIn("mgr.userMoved = false", _SCROLL_FORCE_RESTORE_JS)
        self.assertIn("mgr.scheduleRestore()", _SCROLL_FORCE_RESTORE_JS)


class TestApplyDialogReady(unittest.TestCase):
    _ROW = {"title": "ML engineer", "employer_name": "Acme"}

    def test_ready_with_row_context(self) -> None:
        self.assertTrue(
            apply_dialog_ready(
                use_dialog=True,
                apply_dialog_open=True,
                apply_dialog_key="job_0",
                apply_dialog_context={"row_dict": self._ROW},
            )
        )

    def test_not_ready_without_context_or_pipeline(self) -> None:
        self.assertFalse(
            apply_dialog_ready(
                use_dialog=True,
                apply_dialog_open=True,
                apply_dialog_key="job_0",
                apply_dialog_context=None,
            )
        )
        self.assertFalse(
            apply_dialog_ready(
                use_dialog=True,
                apply_dialog_open=True,
                apply_dialog_key="job_0",
                apply_dialog_context={"row_dict": {}},
            )
        )

    def test_ready_with_active_pipeline_even_without_context(self) -> None:
        self.assertTrue(
            apply_dialog_ready(
                use_dialog=True,
                apply_dialog_open=True,
                apply_dialog_key="job_0",
                apply_dialog_context=None,
                pipeline_job_key="job_0",
                pipeline_phase="running",
            )
        )

    def test_reconcile_clears_stale_open_flags(self) -> None:
        cleared = reconcile_apply_dialog_flags(
            {
                "_use_dialog": True,
                "apply_dialog_open": True,
                "apply_dialog_key": "job_0",
                "apply_dialog_context": None,
            }
        )
        self.assertEqual(
            cleared,
            {
                "apply_dialog_open": False,
                "apply_dialog_key": None,
                "apply_dialog_context": None,
            },
        )

    def test_reconcile_keeps_valid_context(self) -> None:
        self.assertEqual(
            reconcile_apply_dialog_flags(
                {
                    "_use_dialog": True,
                    "apply_dialog_open": True,
                    "apply_dialog_key": "job_0",
                    "apply_dialog_context": {"row_dict": self._ROW},
                }
            ),
            {},
        )

    def test_yield_after_prepare_snapshot_opens_from_fragment(self) -> None:
        """Fragment reruns skip main(); flags set in on_click must still be dialog-ready."""
        snapshot = {
            "_use_dialog": True,
            "apply_dialog_open": True,
            "apply_dialog_key": "exp_0",
            "apply_dialog_context": {
                "row_dict": self._ROW,
                "track": "industry",
                "db_path_s": "/tmp/jobs.sqlite",
            },
            "pipeline_job_key": None,
            "pipeline_phase": None,
        }
        self.assertTrue(yield_to_apply_modify_dialog(snapshot))

    def test_pipeline_active_for_job_key(self) -> None:
        self.assertTrue(
            pipeline_active_for_job_key(
                "job_0",
                pipeline_job_key="job_0",
                pipeline_phase="queued",
            )
        )
        self.assertFalse(
            pipeline_active_for_job_key(
                "job_0",
                pipeline_job_key="job_1",
                pipeline_phase="running",
            )
        )


class TestPipelineFallbackEligible(unittest.TestCase):
    def test_skips_when_apply_dialog_open(self) -> None:
        self.assertFalse(
            pipeline_fallback_eligible(
                apply_dialog_open=True,
                pipeline_job_key="job_0",
                pipeline_panel_rendered=False,
                pipeline_phase="queued",
            )
        )

    def test_true_when_dialog_closed_and_pipeline_queued(self) -> None:
        self.assertTrue(
            pipeline_fallback_eligible(
                apply_dialog_open=False,
                pipeline_job_key="job_0",
                pipeline_panel_rendered=False,
                pipeline_phase="queued",
            )
        )

    def test_false_when_panel_already_rendered(self) -> None:
        self.assertFalse(
            pipeline_fallback_eligible(
                apply_dialog_open=False,
                pipeline_job_key="job_0",
                pipeline_panel_rendered=True,
                pipeline_phase="running",
            )
        )


class TestPipelineQueueHelpers(unittest.TestCase):
    def test_max_in_flight_is_one_running_plus_two_waiting(self) -> None:
        self.assertEqual(PIPELINE_MAX_WAITING, 2)
        self.assertEqual(PIPELINE_MAX_IN_FLIGHT, 3)

    def test_phase_busy_only_queued_or_running(self) -> None:
        self.assertTrue(pipeline_phase_is_busy("queued"))
        self.assertTrue(pipeline_phase_is_busy("running"))
        self.assertFalse(pipeline_phase_is_busy("complete"))
        self.assertFalse(pipeline_phase_is_busy("error"))
        self.assertFalse(pipeline_phase_is_busy(None))

    def test_display_title(self) -> None:
        self.assertEqual(pipeline_job_display_title("AI Eng", "Acme"), "AI Eng — Acme")
        self.assertEqual(pipeline_job_display_title("AI Eng", ""), "AI Eng")
        self.assertEqual(pipeline_job_display_title(None, None), "Job")

    def test_slots_and_full(self) -> None:
        self.assertEqual(pipeline_queue_slots_used(has_active=False, queue_len=0), 0)
        self.assertEqual(pipeline_queue_slots_used(has_active=True, queue_len=2), 3)
        self.assertFalse(pipeline_queue_is_full(has_active=True, queue_len=1))
        self.assertTrue(pipeline_queue_is_full(has_active=True, queue_len=2))
        self.assertEqual(pipeline_queue_remaining(has_active=True, queue_len=1), 1)
        self.assertEqual(pipeline_queue_remaining(has_active=True, queue_len=2), 0)

    def test_can_enqueue_idle_starts_ok(self) -> None:
        ok, reason = can_enqueue_pipeline(
            has_active=False,
            active_job_key=None,
            queue=[],
            job_key="job_a",
        )
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_can_enqueue_rejects_duplicate_active_and_waiting(self) -> None:
        ok, reason = can_enqueue_pipeline(
            has_active=True,
            active_job_key="job_a",
            queue=[],
            job_key="job_a",
        )
        self.assertFalse(ok)
        self.assertIn("already has an active", reason)

        ok, reason = can_enqueue_pipeline(
            has_active=True,
            active_job_key="job_a",
            queue=[{"job_key": "job_b"}],
            job_key="job_b",
        )
        self.assertFalse(ok)
        self.assertIn("already in the queue", reason)

    def test_can_enqueue_rejects_when_full_or_ingest(self) -> None:
        ok, reason = can_enqueue_pipeline(
            has_active=True,
            active_job_key="job_a",
            queue=[{"job_key": "job_b"}, {"job_key": "job_c"}],
            job_key="job_d",
        )
        self.assertFalse(ok)
        self.assertIn("Queue full", reason)

        ok, reason = can_enqueue_pipeline(
            has_active=False,
            active_job_key=None,
            queue=[],
            job_key="job_a",
            ingest_running=True,
        )
        self.assertFalse(ok)
        self.assertIn("Ingest", reason)

    def test_enqueue_dequeue_roundtrip(self) -> None:
        item_a = build_pipeline_queue_item(
            "job_a",
            {"title": "Role A", "employer_name": "Co A"},
            track="industry",
            options=ApplyPipelineOptions(language="en"),
        )
        item_b = build_pipeline_queue_item(
            "job_b",
            {"title": "Role B", "employer_name": "Co B"},
            track="academic",
            options={"language": "no"},
        )
        queue, ok, reason = enqueue_pipeline_item([], item_a)
        self.assertTrue(ok)
        self.assertEqual(reason, "")
        self.assertEqual(len(queue), 1)
        queue, ok, _ = enqueue_pipeline_item(queue, item_b)
        self.assertTrue(ok)
        self.assertEqual(len(queue), 2)
        queue, ok, reason = enqueue_pipeline_item(queue, item_a)
        self.assertFalse(ok)
        self.assertIn("already in the queue", reason)

        item_c = build_pipeline_queue_item(
            "job_c",
            {"title": "Role C", "employer_name": "Co C"},
            track="industry",
            options=None,
        )
        queue, ok, reason = enqueue_pipeline_item(queue, item_c)
        self.assertFalse(ok)
        self.assertIn("Queue full", reason)

        remaining, first = dequeue_pipeline_item(queue)
        self.assertEqual(first["job_key"], "job_a")
        self.assertEqual(len(remaining), 1)
        self.assertEqual(
            pipeline_queue_display_titles(remaining),
            ["Role B — Co B"],
        )
        remaining, second = dequeue_pipeline_item(remaining)
        self.assertEqual(second["job_key"], "job_b")
        remaining, empty = dequeue_pipeline_item(remaining)
        self.assertIsNone(empty)
        self.assertEqual(remaining, [])

    def test_apply_dialog_ready_for_view_completion(self) -> None:
        self.assertTrue(
            apply_dialog_ready(
                use_dialog=True,
                apply_dialog_open=True,
                apply_dialog_key="job_0",
                apply_dialog_context={
                    "view_completion": True,
                    "completion": {"job_key": "job_0", "phase": "complete"},
                },
            )
        )


class TestPipelineResultDetails(unittest.TestCase):
    def test_notice_id_is_stable(self) -> None:
        self.assertEqual(
            pipeline_notice_id(job_key="job_1", phase="complete", run_name="run_123"),
            "job_1|complete|run_123",
        )

    def test_result_details_include_existing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / "cv_generation" / "cv_runs" / "run_123"
            run_dir.mkdir(parents=True)
            (run_dir / "final_cv.md").write_text("# CV\n", encoding="utf-8")
            (run_dir / "cover_letter.md").write_text("# Cover\n", encoding="utf-8")
            details = pipeline_result_details("run_123", repo_root=repo_root)
            self.assertEqual(details["run_dir"], str(run_dir))
            self.assertEqual(details["deanonymize_cmd"], "~/private/cv/cv apply run_123")
            self.assertEqual(
                details["artifact_paths"],
                [str(run_dir / "final_cv.md"), str(run_dir / "cover_letter.md")],
            )


class TestApplyModifyHelpers(unittest.TestCase):
    def test_apply_button_label(self) -> None:
        self.assertEqual(apply_button_label(None), "Apply")
        self.assertEqual(apply_button_label("interested"), "Apply")
        self.assertEqual(apply_button_label("drafted"), "Modify")
        self.assertEqual(apply_button_label("applied"), "Modify")

    def test_is_modify_mode(self) -> None:
        self.assertFalse(is_modify_mode("interested"))
        self.assertTrue(is_modify_mode("drafted"))
        self.assertTrue(is_modify_mode("applied"))

    def test_default_artifact_options_industry(self) -> None:
        opts = default_artifact_options("Please send a cover letter.", track="industry")
        self.assertTrue(opts["generate_cover_letter"])
        self.assertFalse(opts["generate_application_letter"])

    def test_default_artifact_options_academic(self) -> None:
        opts = default_artifact_options(
            "Postdoctoral researcher. Attach research proposal.",
            track="academic",
        )
        self.assertFalse(opts["generate_cover_letter"])
        self.assertTrue(opts["generate_application_letter"])
        self.assertTrue(opts["generate_research_proposal"])

    def test_row_suggests_academic_documents_postdoktor(self) -> None:
        self.assertTrue(
            row_suggests_academic_documents(
                {
                    "title": "Postdoktor innen e-helse/tjenester",
                    "employer_name": "Høgskulen på Vestlandet",
                }
            )
        )
        self.assertFalse(
            row_suggests_academic_documents(
                {"title": "Software engineer", "employer_name": "Acme AS"}
            )
        )

    def test_dialog_artifact_bundle_industry_skips_jd_dependency(self) -> None:
        """Industry open path always defaults cover letter without needing JD markers."""
        bundle = _dialog_artifact_bundle(
            {"description_text": "", "app_notes": None, "title": "ML engineer"},
            track="industry",
            modify=False,
        )
        self.assertTrue(bundle["artifact_defaults"]["generate_cover_letter"])
        self.assertFalse(bundle["show_academic_docs"])
        self.assertIsNone(bundle["existing_run_name"])
        self.assertEqual(bundle["existing_flags"], {})

    def test_dialog_artifact_bundle_industry_postdoc_shows_academic_docs(self) -> None:
        bundle = _dialog_artifact_bundle(
            {
                "title": "Postdoktor innen e-helse",
                "employer_name": "Høgskulen på Vestlandet",
                "description_text": "Vedlegg: prosjektskisse (maks 5 sider).",
                "app_notes": None,
            },
            track="industry",
            modify=False,
        )
        self.assertTrue(bundle["show_academic_docs"])
        self.assertTrue(bundle["artifact_defaults"]["generate_cover_letter"])
        self.assertTrue(bundle["artifact_defaults"]["generate_application_letter"])
        self.assertTrue(bundle["artifact_defaults"]["generate_research_proposal"])

    def test_dialog_artifact_bundle_academic_always_shows_docs(self) -> None:
        bundle = _dialog_artifact_bundle(
            {
                "title": "Research fellow",
                "employer_name": "NMBU",
                "description_text": "",
                "app_notes": None,
            },
            track="academic",
            modify=False,
        )
        self.assertTrue(bundle["show_academic_docs"])
        self.assertTrue(bundle["artifact_defaults"]["generate_application_letter"])
        self.assertFalse(bundle["artifact_defaults"]["generate_cover_letter"])

    def test_apply_pipeline_options_flags_map_to_expected_fields(self) -> None:
        opts = ApplyPipelineOptions(
            generate_cover_letter=False,
            generate_application_letter=True,
            generate_research_proposal=True,
            overwrite_application_letter=True,
        )
        self.assertTrue(opts.generate_application_letter)
        self.assertTrue(opts.generate_research_proposal)
        self.assertFalse(opts.generate_cover_letter)
        self.assertTrue(opts.overwrite_application_letter)


class TestDashboardColumnLayouts(unittest.TestCase):
    def test_applied_role_row_uses_flat_action_columns(self) -> None:
        self.assertEqual(len(APPLIED_ROLE_ROW_COLUMNS), 5)
        action_weights = APPLIED_ROLE_ROW_COLUMNS[-2:]
        self.assertEqual(action_weights, [1.3, 1.2])
        for weight in action_weights:
            self.assertGreaterEqual(weight, 1.0)

    def test_job_explorer_apply_column_wide_enough(self) -> None:
        self.assertEqual(len(JOB_EXPLORER_ROW_COLUMNS), 4)
        self.assertGreaterEqual(JOB_EXPLORER_ROW_COLUMNS[-1], 1.0)

    def test_log_delete_button_column_wide_enough(self) -> None:
        self.assertGreaterEqual(LOG_DELETE_BUTTON_COLUMNS[0], 1.0)


class TestExtractRunIds(unittest.TestCase):
    def test_extracts_basename_from_full_path(self) -> None:
        notes = "CV run: /repo/cv_generation/cv_runs/20260713T120000Z_Falkor_role\n"
        self.assertEqual(
            extract_run_ids_from_notes(notes),
            ["20260713T120000Z_Falkor_role"],
        )

    def test_extracts_multiple_runs(self) -> None:
        notes = (
            "CV run: /a/20260101T100000Z_first\n"
            "CV run: /b/20260202T110000Z_second (Norwegian)\n"
        )
        self.assertEqual(
            extract_run_ids_from_notes(notes),
            ["20260101T100000Z_first", "20260202T110000Z_second"],
        )

    def test_empty_notes(self) -> None:
        self.assertEqual(extract_run_ids_from_notes(None), [])
        self.assertEqual(extract_run_ids_from_notes(""), [])

    def test_extracts_path_with_spaces(self) -> None:
        notes = (
            "CV run: /Users/me/Job Applications/job search automation/"
            "cv_generation/cv_runs/20260713T120000Z_Falkor_role\n"
        )
        self.assertEqual(
            extract_run_ids_from_notes(notes),
            ["20260713T120000Z_Falkor_role"],
        )


class TestApplicationStatusUpsertRow(unittest.TestCase):
    def test_sets_applied_at_when_moving_to_applied(self) -> None:
        row = {
            "uuid": "job-1",
            "source": "nav_arbeidsplassen",
            "track": "industry",
            "status": "drafted",
            "notes": "CV run: /x/run_one",
            "cover_letter_path": "/x/cover.md",
            "applied_at": None,
            "follow_up_at": "2026-08-01",
        }
        payload = application_status_upsert_row(row, "applied", now="2026-07-21T12:00:00Z")
        self.assertEqual(payload["status"], "applied")
        self.assertEqual(payload["applied_at"], "2026-07-21T12:00:00Z")
        self.assertEqual(payload["notes"], "CV run: /x/run_one")
        self.assertEqual(payload["cover_letter_path"], "/x/cover.md")
        self.assertEqual(payload["follow_up_at"], "2026-08-01")
        self.assertEqual(payload["updated_at"], "2026-07-21T12:00:00Z")

    def test_preserves_existing_applied_at(self) -> None:
        row = {
            "uuid": "job-1",
            "source": "finn_no",
            "track": "academic",
            "status": "applied",
            "applied_at": "2026-07-01T09:00:00Z",
            "notes": None,
        }
        payload = application_status_upsert_row(row, "interview", now="2026-07-21T12:00:00Z")
        self.assertEqual(payload["status"], "interview")
        self.assertEqual(payload["applied_at"], "2026-07-01T09:00:00Z")

    def test_rejects_unknown_status(self) -> None:
        with self.assertRaises(ValueError):
            application_status_upsert_row(
                {"uuid": "u", "source": "nav_arbeidsplassen", "track": "industry"},
                "nope",
            )


class TestAppliedRolesHelpers(unittest.TestCase):
    def test_status_badge_markdown(self) -> None:
        self.assertIn("drafted", status_badge_markdown("drafted"))
        self.assertIn("gray", status_badge_markdown("unknown_status"))

    def test_filter_applied_roles_df(self) -> None:
        df = pd.DataFrame(
            {"status": ["drafted", "applied", "rejected"], "title": ["a", "b", "c"]}
        )
        filtered = filter_applied_roles_df(df, status_filter=("drafted", "applied"))
        self.assertEqual(len(filtered), 2)
        self.assertEqual(set(filtered["status"]), {"drafted", "applied"})

    def test_default_status_filters_split_drafts_and_applied(self) -> None:
        self.assertEqual(DEFAULT_DRAFTS_STATUS_FILTER, ("drafted",))
        self.assertEqual(DRAFTS_STATUS_OPTIONS, ["drafted"])
        self.assertEqual(DEFAULT_APPLIED_STATUS_FILTER, ("applied", "interested"))
        self.assertNotIn("drafted", DEFAULT_APPLIED_STATUS_FILTER)

    def test_count_applied_roles_by_status_group(self) -> None:
        df = pd.DataFrame(
            {"status": ["drafted", "drafted", "applied", "interested", "rejected"]}
        )
        self.assertEqual(_count_applied_roles(df, statuses={"drafted"}), 2)
        self.assertEqual(
            _count_applied_roles(df, statuses={"applied", "interested", "rejected"}),
            3,
        )
        self.assertEqual(_count_applied_roles(pd.DataFrame(), statuses={"drafted"}), 0)

    def test_bulk_deanonymize_command_requires_two_drafted(self) -> None:
        df = pd.DataFrame(
            {
                "status": ["drafted", "drafted", "applied"],
                "notes": [
                    "CV run: /x/run_one",
                    "CV run: /x/run_two",
                    "CV run: /x/run_three",
                ],
            }
        )
        cmd = bulk_deanonymize_command(df)
        self.assertIsNotNone(cmd)
        assert cmd is not None
        self.assertIn("run_one", cmd)
        self.assertIn("run_two", cmd)
        self.assertNotIn("run_three", cmd)

    def test_bulk_deanonymize_command_single_run_returns_none(self) -> None:
        df = pd.DataFrame({"status": ["drafted"], "notes": ["CV run: /x/only_one"]})
        self.assertIsNone(bulk_deanonymize_command(df))

    def test_row_dict_for_apply_from_app(self) -> None:
        row = {
            "uuid": "u1",
            "source": "nav_arbeidsplassen",
            "title": "Engineer",
            "employer_name": "Acme",
            "notes": "CV run: /x/run",
        }
        out = row_dict_for_apply_from_app(row)
        self.assertEqual(out["uuid"], "u1")
        self.assertEqual(out["app_notes"], "CV run: /x/run")


class TestHideAppliedFilter(unittest.TestCase):
    def test_explorer_defaults_hide_applied_and_dedupe(self) -> None:
        self.assertTrue(DEFAULT_HIDE_APPLIED)
        self.assertTrue(DEFAULT_DEDUPE_CROSS_SOURCE)

    def test_hide_applied_statuses_include_drafted_not_interested(self) -> None:
        self.assertEqual(HIDE_APPLIED_STATUSES, MODIFY_STATUSES)
        self.assertIn("drafted", HIDE_APPLIED_STATUSES)
        self.assertIn("applied", HIDE_APPLIED_STATUSES)
        for status in ("interview", "offer", "rejected", "withdrawn"):
            self.assertIn(status, HIDE_APPLIED_STATUSES)
        self.assertNotIn("interested", HIDE_APPLIED_STATUSES)

    def test_explorer_cache_fingerprint_includes_dedupe_and_hide_applied(self) -> None:
        base_kwargs = dict(
            path_s="/tmp/jobs.sqlite",
            track="industry",
            min_score=0.0,
            rogaland_only=False,
            hide_applied=DEFAULT_HIDE_APPLIED,
            query_include_terms=(),
            exclude_tuple=(),
            source_filter="all",
            hide_phd_student=True,
            apply_academic_filter=False,
            dedupe_cross_source=DEFAULT_DEDUPE_CROSS_SOURCE,
            use_tech_allowlist=True,
            include_tuple=(),
            urgency_days=7,
            text_query="",
        )
        on = _explorer_jobs_cache_fingerprint(**base_kwargs)
        dedupe_off = _explorer_jobs_cache_fingerprint(
            **{**base_kwargs, "dedupe_cross_source": False}
        )
        hide_off = _explorer_jobs_cache_fingerprint(
            **{**base_kwargs, "hide_applied": False}
        )
        self.assertNotEqual(on, dedupe_off)
        self.assertNotEqual(on, hide_off)

    def test_explorer_filter_chips_reflect_defaults(self) -> None:
        chips = build_explorer_filter_chips(
            track="industry",
            source_filter="all",
            apply_academic_filter=False,
            use_tech_allowlist=True,
            include_tuple=("python",),
            exclude_tuple=(),
            hide_phd_student=True,
            dedupe_cross_source=DEFAULT_DEDUPE_CROSS_SOURCE,
            min_score=0.0,
            rogaland_only=False,
            hide_applied=DEFAULT_HIDE_APPLIED,
            text_query="",
        )
        self.assertIn("Hide applications", chips)
        self.assertIn("Dedup cross-source", chips)

    def test_load_jobs_df_hide_applied_excludes_drafted_and_applied(self) -> None:
        now = utc_now_iso()
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.sqlite"
            conn = connect(db_path)
            init_schema(conn)
            jobs = [
                ("job-drafted", "drafted"),
                ("job-interested", "interested"),
                ("job-applied", "applied"),
                ("job-none", None),
            ]
            for uuid, status in jobs:
                upsert_job(
                    conn,
                    {
                        "uuid": uuid,
                        "source": "nav_arbeidsplassen",
                        "title": f"Role {uuid}",
                        "employer_name": "Acme",
                        "fetched_at": now,
                    },
                )
                upsert_score(
                    conn,
                    {
                        "uuid": uuid,
                        "source": "nav_arbeidsplassen",
                        "track": "industry",
                        "score_base": 10.0,
                        "boost_rogaland": 0.0,
                        "boost_tek": 0.0,
                        "score_total": 10.0,
                        "scored_at": now,
                    },
                )
                if status is not None:
                    upsert_application(
                        conn,
                        {
                            "uuid": uuid,
                            "source": "nav_arbeidsplassen",
                            "track": "industry",
                            "status": status,
                            "notes": None,
                            "updated_at": now,
                        },
                    )
            conn.commit()
            conn.close()

            all_jobs = load_jobs_df(
                str(db_path),
                "industry",
                0.0,
                False,
                False,
                False,
                (),
                (),
                "all",
                False,
            )
            hidden = load_jobs_df(
                str(db_path),
                "industry",
                0.0,
                False,
                False,
                True,
                (),
                (),
                "all",
                False,
            )
            self.assertEqual(len(all_jobs), 4)
            self.assertEqual(
                set(hidden["uuid"]),
                {"job-interested", "job-none"},
            )


class TestLoadAppliedRolesDf(unittest.TestCase):
    def test_load_applied_roles_df_filters_by_track(self) -> None:
        now = utc_now_iso()
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "jobs.sqlite"
            conn = connect(db_path)
            init_schema(conn)
            upsert_job(
                conn,
                {
                    "uuid": "job-1",
                    "source": "nav_arbeidsplassen",
                    "title": "ML Engineer",
                    "employer_name": "Falkor",
                    "fetched_at": now,
                },
            )
            upsert_score(
                conn,
                {
                    "uuid": "job-1",
                    "source": "nav_arbeidsplassen",
                    "track": "industry",
                    "score_base": 42.0,
                    "boost_rogaland": 0.0,
                    "boost_tek": 0.0,
                    "score_total": 42.0,
                    "scored_at": now,
                },
            )
            upsert_application(
                conn,
                {
                    "uuid": "job-1",
                    "source": "nav_arbeidsplassen",
                    "track": "industry",
                    "status": "drafted",
                    "notes": "CV run: /x/20260713T_industry",
                    "updated_at": now,
                },
            )
            upsert_application(
                conn,
                {
                    "uuid": "job-1",
                    "source": "nav_arbeidsplassen",
                    "track": "academic",
                    "status": "interested",
                    "notes": None,
                    "updated_at": now,
                },
            )
            conn.commit()
            conn.close()

            industry = load_applied_roles_df(str(db_path), "industry")
            academic = load_applied_roles_df(str(db_path), "academic")
            self.assertEqual(len(industry), 1)
            self.assertEqual(industry.iloc[0]["status"], "drafted")
            self.assertEqual(float(industry.iloc[0]["score_total"]), 42.0)
            self.assertEqual(len(academic), 1)
            self.assertEqual(academic.iloc[0]["status"], "interested")


class TestPipelineMetricsDashboard(unittest.TestCase):
    def test_summary_missing_metrics_returns_none(self) -> None:
        self.assertIsNone(pipeline_metrics_summary_for_notes("CV run: /x/nonexistent_run_id"))

    def test_summary_from_metrics_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_id = "20260714T_test_metrics"
            run_dir = REPO / "cv_generation" / "cv_runs" / run_id
            run_dir.mkdir(parents=True, exist_ok=True)
            try:
                metrics = {
                    "duration_sec": 120,
                    "totals": {
                        "wall_clock_sec": 120,
                        "tokens_total": 8000,
                        "tokens_source": "measured_api",
                    },
                    "energy_estimate": {"kwh": 0.004},
                }
                (run_dir / "pipeline_metrics.json").write_text(
                    json.dumps(metrics, indent=2) + "\n",
                    encoding="utf-8",
                )
                notes = f"CV run: {run_dir}\n"
                line = pipeline_metrics_summary_for_notes(notes)
                self.assertIsNotNone(line)
                assert line is not None
                self.assertIn("Pipeline:", line)
                self.assertIn("8k tokens", line)
            finally:
                metrics_path = run_dir / "pipeline_metrics.json"
                if metrics_path.is_file():
                    metrics_path.unlink()
                if run_dir.is_dir() and not any(run_dir.iterdir()):
                    run_dir.rmdir()


if __name__ == "__main__":
    unittest.main()
