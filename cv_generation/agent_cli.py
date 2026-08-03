#!/usr/bin/env python3
"""
Provider-neutral CLI for the agent-portable CV pipeline.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from cv_generation.agent_contract import (
    contract_metadata,
    load_json,
    manual_prompt_path,
    manual_response_path,
    parse_json_response,
    task_output_pairs,
    validate_output_against_task,
)
from cv_generation.run_agent_pipeline import build_prompt, run_single_step


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CLI for the agent-portable CV pipeline")
    sub = p.add_subparsers(dest="command", required=True)

    prep = sub.add_parser("prepare-run", help="Create a run folder with task files")
    prep.add_argument("--job-file", required=True)
    prep.add_argument("--company", default="")
    prep.add_argument("--role", default="")
    prep.add_argument("--run-dir", default="")
    prep.add_argument("--force", action="store_true")
    prep.add_argument("--output-language", choices=("en", "no"), default="en")

    prompt = sub.add_parser("build-step-prompt", help="Emit a single step prompt to stdout")
    prompt.add_argument("--run-dir", required=True)
    prompt.add_argument("--step", required=True, help="Output file name such as 01_jd_parser_output.json")

    validate = sub.add_parser("validate-step-output", help="Validate a JSON response for one step")
    validate.add_argument("--run-dir", required=True)
    validate.add_argument("--step", required=True)
    validate.add_argument("--input", default="", help="Path to JSON file; defaults to the step output path")

    run_step = sub.add_parser("run-step", help="Run a single step with a provider")
    run_step.add_argument("--run-dir", required=True)
    run_step.add_argument("--step", required=True)
    run_step.add_argument("--provider", default="manual")
    run_step.add_argument("--model", default="")
    run_step.add_argument("--overwrite", action="store_true")
    run_step.add_argument("--dry-run", action="store_true")
    run_step.add_argument("--allow-fewer-bullets", action="store_true")
    run_step.add_argument("--apply-tailored-bullets", action="store_true")

    run_pipeline_cmd = sub.add_parser("run-pipeline", help="Run the full pipeline")
    run_pipeline_cmd.add_argument(
        "pipeline_args",
        nargs=argparse.REMAINDER,
        help="Arguments forwarded to run_agent_pipeline (e.g. --run-dir PATH --provider anthropic)",
    )

    sub.add_parser("show-contract", help="Print the run-folder contract JSON")
    return p.parse_args()


def _resolve_step(step: str) -> tuple[str, str]:
    for task_name, out_name in task_output_pairs():
        if step == out_name or step == out_name.replace("_output.json", ""):
            return task_name, out_name
    raise SystemExit(f"Unknown step: {step}")


def _prior_outputs(run_dir: Path, stop_before_output: str) -> list[dict[str, object]]:
    outputs: list[dict[str, object]] = []
    for task_name, out_name in task_output_pairs():
        if out_name == stop_before_output:
            break
        out_path = run_dir / out_name
        if out_path.is_file():
            outputs.append({"name": out_name, "output": load_json(out_path)})
    return outputs


def _run_prepare(args: argparse.Namespace) -> int:
    cmd = [
        sys.executable,
        "-m",
        "cv_generation.run_cv_tailoring",
        "--job-file",
        args.job_file,
        "--company",
        args.company,
        "--role",
        args.role,
        "--output-language",
        args.output_language,
    ]
    if args.run_dir:
        cmd.extend(["--run-dir", args.run_dir])
    if args.force:
        cmd.append("--force")
    return subprocess.call(cmd, cwd=_root)


def _run_build_prompt(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser().resolve()
    task_name, out_name = _resolve_step(args.step)
    task = load_json(run_dir / task_name)
    prompt = build_prompt(task, _prior_outputs(run_dir, out_name), run_dir=run_dir)
    print(prompt)
    return 0


def _run_validate(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser().resolve()
    task_name, out_name = _resolve_step(args.step)
    task = load_json(run_dir / task_name)
    input_path = Path(args.input).expanduser().resolve() if args.input else run_dir / out_name
    raw = input_path.read_text(encoding="utf-8")
    output = parse_json_response(raw)
    errors = validate_output_against_task(task, output)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("OK")
    return 0


def _run_step(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir).expanduser().resolve()
    task_name, out_name = _resolve_step(args.step)
    prior_outputs = _prior_outputs(run_dir, out_name)
    try:
        out_obj, _ = run_single_step(
            run_dir=run_dir,
            task_name=task_name,
            out_name=out_name,
            prior_outputs=prior_outputs,
            provider_name=args.provider,
            model=args.model,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            allow_fewer_bullets=args.allow_fewer_bullets,
            apply_tailored_bullets=args.apply_tailored_bullets,
        )
    except RuntimeError as err:
        print(str(err), file=sys.stderr)
        return 1

    step_stem = out_name.replace("_output.json", "")
    if args.provider == "manual":
        print(f"Prompt file: {manual_prompt_path(run_dir, step_stem)}")
        print(f"Manual response file: {manual_response_path(run_dir, step_stem)}")
    if out_obj is not None:
        print(json.dumps(out_obj, indent=2, ensure_ascii=False))
    return 0


def _run_pipeline_cmd(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "cv_generation.run_agent_pipeline", *(args.pipeline_args or [])]
    return subprocess.call(cmd, cwd=_root)


def main() -> int:
    args = parse_args()
    if args.command == "prepare-run":
        return _run_prepare(args)
    if args.command == "build-step-prompt":
        return _run_build_prompt(args)
    if args.command == "validate-step-output":
        return _run_validate(args)
    if args.command == "run-step":
        return _run_step(args)
    if args.command == "run-pipeline":
        return _run_pipeline_cmd(args)
    if args.command == "show-contract":
        print(json.dumps(contract_metadata(), indent=2, ensure_ascii=False))
        return 0
    raise SystemExit(f"Unknown command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
