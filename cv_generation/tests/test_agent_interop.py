"""Tests for the agent-portable CV pipeline surface."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cv_generation.agent_contract import (
    CONTRACT_VERSION,
    manual_prompt_path,
    manual_response_path,
    parse_json_response,
    validate_output_against_task,
)
from cv_generation.apply_prompts import write_apply_prompts
from cv_generation.agent_providers import ManualAgentProvider
from cv_generation.cv_assemble import build_assembler_output
from cv_generation.run_agent_pipeline import (
    build_prompt,
    programmatic_keyword_ranker_output,
    run_single_step,
    sanitize_jd_parser_output,
)

JOB_FILE = REPO / "cv_generation" / "jobs" / "demo_northline_ml_engineer.txt"


def _prepare_run(run_dir: Path) -> None:
    cmd = [
        sys.executable,
        "-m",
        "cv_generation.run_cv_tailoring",
        "--job-file",
        str(JOB_FILE),
        "--company",
        "Northline Labs",
        "--role",
        "ML Engineer",
        "--run-dir",
        str(run_dir),
        "--force",
    ]
    subprocess.run(cmd, cwd=REPO, check=True, capture_output=True, text=True)


class TestAgentInterop(unittest.TestCase):
    def test_prepare_run_writes_contract_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            _prepare_run(run_dir)
            manifest = json.loads((run_dir / "agent_contract.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["contract_version"], CONTRACT_VERSION)
            task = json.loads((run_dir / "01_jd_parser_task.json").read_text(encoding="utf-8"))
            self.assertEqual(task["context"]["agent_contract"]["contract_version"], CONTRACT_VERSION)

    def test_build_prompt_includes_user_apply_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            _prepare_run(run_dir)
            write_apply_prompts(run_dir, "emphasize RAG experience")
            task = json.loads((run_dir / "04_bullet_tailor_task.json").read_text(encoding="utf-8"))
            prompt = json.loads(build_prompt(task, [], run_dir=run_dir))
            self.assertEqual(prompt["user_apply_prompts"], "emphasize RAG experience")
            self.assertIn("user_apply_prompts", prompt["instruction"])

    def test_build_prompt_includes_task_and_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            _prepare_run(run_dir)
            task = json.loads((run_dir / "01_jd_parser_task.json").read_text(encoding="utf-8"))
            prompt = json.loads(build_prompt(task, [], run_dir=run_dir))
            self.assertEqual(prompt["task"]["agent"], "jd_parser")
            self.assertTrue(prompt["validation"]["must_be_json_object"])
            self.assertIn("role_title", prompt["validation"]["required_top_level_keys"])

    def test_manual_provider_uses_standard_prompt_and_response_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            run_dir.mkdir(parents=True, exist_ok=True)
            provider = ManualAgentProvider(run_dir, "01_jd_parser")
            response_path = manual_response_path(run_dir, "01_jd_parser")
            response_path.write_text('{"role_title":"ML Engineer"}\n', encoding="utf-8")
            result = provider.run("{}", model="manual")
            self.assertEqual(result.provider, "manual")
            self.assertTrue(manual_prompt_path(run_dir, "01_jd_parser").is_file())

    def test_run_single_step_supports_manual_external_agent_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            _prepare_run(run_dir)
            response = {
                "role_title": "ML Engineer",
                "company": "Northline Labs",
                "location": "Oslo",
                "must_have_skills": ["python"],
                "nice_to_have_skills": ["mlops"],
                "domain_keywords": ["machine learning"],
                "seniority": "mid",
            }
            manual_response_path(run_dir, "01_jd_parser").write_text(
                json.dumps(response, indent=2) + "\n",
                encoding="utf-8",
            )
            out_obj, _ = run_single_step(
                run_dir=run_dir,
                task_name="01_jd_parser_task.json",
                out_name="01_jd_parser_output.json",
                prior_outputs=[],
                provider_name="manual",
                model="manual",
                overwrite=True,
                dry_run=False,
                allow_fewer_bullets=False,
                apply_tailored_bullets=False,
            )
            self.assertEqual(out_obj["role_title"], "ML Engineer")
            saved = json.loads((run_dir / "01_jd_parser_output.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["company"], "Northline Labs")

    def test_legacy_cursor_named_module_remains_callable(self) -> None:
        for module_name in ("cv_generation.generate_cv_with_cursor", "cv_generation.run_agent_pipeline"):
            cmd = [sys.executable, "-m", module_name, "--help"]
            proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("--provider", proc.stdout)

    def test_agent_cli_show_contract(self) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "cv_generation.agent_cli", "show-contract"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        manifest = json.loads(proc.stdout)
        self.assertEqual(manifest["contract_version"], CONTRACT_VERSION)

    def test_agent_cli_build_step_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            _prepare_run(run_dir)
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "cv_generation.agent_cli",
                    "build-step-prompt",
                    "--run-dir",
                    str(run_dir),
                    "--step",
                    "01_jd_parser_output.json",
                ],
                cwd=REPO,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            prompt = json.loads(proc.stdout)
            self.assertEqual(prompt["task"]["agent"], "jd_parser")


    def test_build_assembler_output_includes_validation_warnings(self) -> None:
        out = build_assembler_output(
            "# Industry CV\n\n## Name\n\nMITCH EVANS\n",
            track="industry",
            company="Inspirit365",
            role_title="Data Engineer & Data Scientist",
        )
        self.assertEqual(out["validation_warnings"], [])
        self.assertIn("artifact_name", out)

    def test_programmatic_assembler_output_passes_task_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            _prepare_run(run_dir)
            task = json.loads((run_dir / "06_assembler_task.json").read_text(encoding="utf-8"))
            out = build_assembler_output(
                "# Industry CV\n\n## Name\n\nMITCH EVANS\n",
                track="industry",
                company="Northline Labs",
                role_title="ML Engineer",
            )
            errors = validate_output_against_task(task, out)
            self.assertEqual(errors, [])

    def test_parse_json_response_extracts_object_from_prose(self) -> None:
        raw = 'Here you go:\n{"role_title": "ML Engineer", "company": "Acme"}\nThanks.'
        out = parse_json_response(raw)
        self.assertEqual(out["role_title"], "ML Engineer")

    def test_programmatic_keyword_ranker_output_passes_task_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            _prepare_run(run_dir)
            jd_path = run_dir / "01_jd_parser_output.json"
            jd_path.write_text(
                json.dumps(
                    {
                        "role_title": "ML Engineer",
                        "company": "Northline Labs",
                        "location": "Oslo",
                        "must_have_skills": ["python", "mlops"],
                        "nice_to_have_skills": ["kubernetes", "c#"],
                        "domain_keywords": ["consulting"],
                        "seniority": "mid",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            task = json.loads((run_dir / "02_keyword_ranker_task.json").read_text(encoding="utf-8"))
            out = programmatic_keyword_ranker_output(run_dir, [])
            errors = validate_output_against_task(task, out)
            self.assertEqual(errors, [])
            terms = [row["term"] for row in out["priority_keywords"]]
            self.assertIn("python", terms)
            self.assertIn("kubernetes", out["missing_keywords"])
            self.assertGreater(out["overlap_score"], 0)


class TestPdfExportDefault(unittest.TestCase):
    def test_pipeline_skips_pdf_by_default(self) -> None:
        from cv_generation.run_agent_pipeline import make_parser, skip_pdf_export

        args = make_parser().parse_args(["--run-dir", "/tmp/run"])
        self.assertTrue(skip_pdf_export(args))

    def test_pdf_flag_opts_in(self) -> None:
        from cv_generation.run_agent_pipeline import make_parser, skip_pdf_export

        args = make_parser().parse_args(["--run-dir", "/tmp/run", "--pdf"])
        self.assertFalse(skip_pdf_export(args))

    def test_no_pdf_flag_still_skips(self) -> None:
        from cv_generation.run_agent_pipeline import make_parser, skip_pdf_export

        args = make_parser().parse_args(["--run-dir", "/tmp/run", "--no-pdf"])
        self.assertTrue(skip_pdf_export(args))

    def test_render_only_implies_pdf(self) -> None:
        from cv_generation.run_agent_pipeline import make_parser, skip_pdf_export

        args = make_parser().parse_args(["--run-dir", "/tmp/run", "--render-only"])
        self.assertFalse(skip_pdf_export(args))

    def test_render_only_no_pdf_skips(self) -> None:
        from cv_generation.run_agent_pipeline import make_parser, skip_pdf_export

        args = make_parser().parse_args(["--run-dir", "/tmp/run", "--render-only", "--no-pdf"])
        self.assertTrue(skip_pdf_export(args))


class TestJdParserSanitize(unittest.TestCase):
    JOB_TEXT = (
        "We need strong Python and software engineering skills. "
        "Required: NLP, generative AI, prompt design, RAG architectures, model evaluation. "
        "Preferred: Docker, Kubernetes, Azure. "
        "Experience with modern LLMs and agent frameworks (e.g. LangGraph, AutoGen) is required."
    )

    def test_drops_terms_absent_from_posting(self) -> None:
        output = {
            "must_have_skills": ["python", "llm fine-tuning", "pytorch", "nlp"],
            "nice_to_have_skills": ["docker", "ethical ai", "kubernetes"],
            "domain_keywords": ["generative ai", "reinforcement learning"],
        }
        cleaned, removed = sanitize_jd_parser_output(self.JOB_TEXT, output)
        self.assertEqual(cleaned["must_have_skills"], ["python", "nlp"])
        self.assertEqual(cleaned["nice_to_have_skills"], ["docker", "kubernetes"])
        self.assertEqual(cleaned["domain_keywords"], ["generative ai"])
        self.assertTrue(any("llm fine-tuning" in r for r in removed))
        self.assertTrue(any("pytorch" in r for r in removed))

    def test_keeps_phrase_and_multi_token_matches(self) -> None:
        output = {
            "must_have_skills": ["prompt design", "rag architectures", "agent frameworks"],
            "nice_to_have_skills": [],
            "domain_keywords": [],
        }
        cleaned, removed = sanitize_jd_parser_output(self.JOB_TEXT, output)
        self.assertEqual(removed, [])
        self.assertEqual(
            cleaned["must_have_skills"],
            ["prompt design", "rag architectures", "agent frameworks"],
        )

    def test_empty_job_text_is_noop(self) -> None:
        output = {"must_have_skills": ["python"], "nice_to_have_skills": ["pytorch"]}
        cleaned, removed = sanitize_jd_parser_output("", output)
        self.assertEqual(removed, [])
        self.assertEqual(cleaned["must_have_skills"], ["python"])

    def test_build_prompt_injects_job_text_for_jd_parser(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run"
            _prepare_run(run_dir)
            task = json.loads((run_dir / "01_jd_parser_task.json").read_text(encoding="utf-8"))
            prompt = json.loads(build_prompt(task, [], run_dir=run_dir))
            self.assertIn("job_text", prompt.get("context_extras", {}))
            self.assertIn("Northline", prompt["context_extras"]["job_text"])


if __name__ == "__main__":
    unittest.main()
