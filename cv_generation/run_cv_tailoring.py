#!/usr/bin/env python3
"""
Create a per-job CV tailoring workspace using subagent specs.

This script does not call external LLM APIs directly.
It prepares structured inputs/outputs so you can run each step with your preferred agent.
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import argparse
import json
from datetime import datetime

from shared.cv_loader import CV_DIR, load_default_profiles
from cv_generation.agent_contract import contract_metadata, write_contract_manifest
from cv_generation.apply_prompts import (
    apply_language_markdown_section,
    apply_prompts_markdown_section,
    merge_apply_prompts,
    write_apply_prompts,
)
from cv_generation.cv_application_artifacts import application_artifacts_markdown
from cv_generation.cv_style import TAILORING_CONSTRAINTS
from cv_generation.cv_subagents import SUBAGENT_SPECS, as_markdown
from cv_generation.run_naming import (
    parse_role_from_job_posting,
    resolve_company_for_folder,
    run_folder_name,
)

RUNS_DIR = Path(__file__).resolve().parent / "cv_runs"


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare CV tailoring subagent run folder")
    p.add_argument("--job-file", required=True, type=Path, help="Path to plain-text job posting")
    p.add_argument("--company", default="", help="Company name (optional)")
    p.add_argument("--role", default="", help="Role title (optional)")
    p.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Write workspace here (e.g. cv_generation/demo/northline_ml_engineer) instead of cv_runs/<timestamp>_…",
    )
    p.add_argument(
        "--force",
        action="store_true",
        help="With --run-dir, allow overwriting an existing folder",
    )
    p.add_argument(
        "--output-language",
        choices=("en", "no"),
        default="en",
        help="Stash desired output language in job_meta (localization via run_agent_pipeline --language no)",
    )
    p.add_argument(
        "--apply-prompts",
        default="",
        help="Optional user tailoring instructions (written to apply_prompts.txt in the run folder)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    job_file = args.job_file.expanduser().resolve()
    if not job_file.is_file():
        raise SystemExit(f"Job file not found: {job_file}")

    job_text = job_file.read_text(encoding="utf-8").strip()
    role = args.role.strip() or parse_role_from_job_posting(job_text) or job_file.stem
    company = resolve_company_for_folder(company_arg=args.company, job_text=job_text)

    if args.run_dir:
        run_dir = args.run_dir.expanduser().resolve()
        if run_dir.exists():
            if not args.force:
                raise SystemExit(f"Run dir exists (use --force): {run_dir}")
        else:
            run_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_id = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        run_dir = RUNS_DIR / run_folder_name(run_id, role, company)
        run_dir.mkdir(parents=True, exist_ok=True)

    profiles = load_default_profiles()
    profile_by_track = {p.track: p for p in profiles}
    industry = profile_by_track.get("industry")
    academic = profile_by_track.get("academic")

    apply_prompts = merge_apply_prompts(args.apply_prompts)

    # Save source inputs
    (run_dir / "job_posting.txt").write_text(job_text + "\n", encoding="utf-8")
    (run_dir / "subagent_specs.md").write_text(as_markdown(), encoding="utf-8")
    artifacts_md = application_artifacts_markdown(job_text, role_title=role)
    artifacts_md += apply_language_markdown_section(args.output_language)
    artifacts_md += apply_prompts_markdown_section(apply_prompts)
    (run_dir / "application_artifacts.md").write_text(artifacts_md + "\n", encoding="utf-8")
    if apply_prompts:
        write_apply_prompts(run_dir, apply_prompts)
    if industry:
        (run_dir / "cv_industry_source.md").write_text(industry.body_markdown + "\n", encoding="utf-8")
    if academic:
        (run_dir / "cv_academic_source.md").write_text(academic.body_markdown + "\n", encoding="utf-8")

    # Build agent task stubs with strict input contracts.
    base_context = {
        "agent_contract": contract_metadata(),
        "job_meta": {
            "company": company,
            "role_title": role,
            "output_language": args.output_language,
        },
        "constraints": list(TAILORING_CONSTRAINTS),
        "cv_templates": {
            "industry": industry.body_markdown if industry else "",
            "academic": academic.body_markdown if academic else "",
        },
    }
    if apply_prompts:
        base_context["user_apply_prompts"] = apply_prompts

    for idx, spec in enumerate(SUBAGENT_SPECS, start=1):
        payload = {
            "agent": spec.name,
            "purpose": spec.purpose,
            "prompt_template": spec.prompt_template,
            "required_inputs": list(spec.required_inputs),
            "expected_output_schema": spec.output_schema,
            "context": base_context,
        }
        write_json(run_dir / f"{idx:02d}_{spec.name}_task.json", payload)

    # Starter output placeholders
    for idx, spec in enumerate(SUBAGENT_SPECS, start=1):
        write_json(run_dir / f"{idx:02d}_{spec.name}_output.sample.json", {"agent": spec.name, "status": "pending"})

    write_contract_manifest(run_dir)

    print(run_dir)
    print("Next:")
    print("  1) Run each *_task.json with your preferred agent runner")
    print("  2) Save responses into *_output.json")
    print("  3) Assemble final markdown/PDF from assembler output")
    print("  4) Create supplementary docs listed in application_artifacts.md (if required)")
    print("  5) ~/private/cv/cv apply <run_id>  # deanonymize all artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

