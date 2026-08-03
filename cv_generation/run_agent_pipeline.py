#!/usr/bin/env python3
"""
Run CV tailoring end-to-end with a pluggable agent backend.

Default provider: cursor. Also supports anthropic, openai, and manual.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from cv_generation.apply_prompts import read_apply_prompts
from cv_generation.agent_contract import (
    OUTPUT_ORDER,
    TASK_ORDER,
    load_json,
    parse_json_response,
    required_top_level_keys,
    task_output_pairs,
    validate_output_against_task,
    write_json,
)
from cv_generation.agent_providers import get_provider, list_providers
from cv_generation.cover_letter_generator import maybe_generate_cover_letter
from cv_generation.supplementary_generator import (
    maybe_generate_application_letter,
    maybe_generate_research_proposal,
)
from cv_generation.pipeline_metrics import PipelineMetricsCollector, write_pipeline_metrics
from cv_generation.cv_assemble import (
    assemble_final_cv_markdown,
    build_assembler_output,
    experience_role_key,
    normalize_bullet_tailor_output,
    resolve_job_role_title,
)
from cv_generation.cv_pdf_renderer import parse_cv_markdown, render_styled_cv_pdf
from cv_generation.cv_source_sync import full_cv_markdown
from cv_generation.cv_subagents import SUBAGENT_SPECS
from shared.cv_loader import load_default_profiles


def make_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Automate CV generation with a pluggable agent backend")
    p.add_argument("--run-dir", required=True, type=Path, help="Path to cv_runs/<run_id> folder")
    p.add_argument(
        "--provider",
        default="cursor",
        choices=list_providers(),
        help="Agent backend: cursor (default), anthropic, openai, manual",
    )
    p.add_argument(
        "--model",
        default="",
        help=(
            "Model id (provider-specific; cursor default composer-2.5, "
            "anthropic claude-sonnet-4-20250514, openai gpt-4o)"
        ),
    )
    p.add_argument("--overwrite", action="store_true", help="Overwrite existing *_output.json files")
    p.add_argument("--dry-run", action="store_true", help="Print prompts only, do not call agent APIs")
    p.add_argument("--no-pdf", action="store_true", help="Skip PDF export")
    p.add_argument(
        "--render-only",
        action="store_true",
        help="Do not run agents or rewrite final_cv.md; regenerate PDF from existing final_cv.md",
    )
    p.add_argument(
        "--refresh-tasks",
        action="store_true",
        help="Sync task JSON and cv_*_source.md from repo cv/ before running agents",
    )
    p.add_argument(
        "--allow-fewer-bullets",
        action="store_true",
        help="Allow bullet_tailor to return fewer bullets per role (default: pad from source)",
    )
    p.add_argument(
        "--profile-photo",
        type=Path,
        default=None,
        help="Path to your headshot (or set CV_PROFILE_PHOTO / _profile_photo_path in mapping JSON)",
    )
    p.add_argument(
        "--apply-tailored-bullets",
        action="store_true",
        help="Apply bullet_tailor profile/experience rewrites (default: keep source wording)",
    )
    p.add_argument(
        "--language",
        choices=("en", "no"),
        default="en",
        help="After English CV assembly, also write Norwegian B1 artifacts (_no.md / _no.pdf)",
    )
    p.add_argument(
        "--localize-only",
        action="store_true",
        help="Skip agent tailoring; localize existing final_cv.md (+ cover_letter.md) to Norwegian",
    )
    p.add_argument(
        "--generate-cover-letter",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Generate cover_letter.md (default: auto-detect for industry track)",
    )
    p.add_argument(
        "--generate-application-letter",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Generate application_letter.md (default: off unless set)",
    )
    p.add_argument(
        "--generate-research-proposal",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Generate research_proposal.md (default: off unless set)",
    )
    p.add_argument(
        "--overwrite-cover-letter",
        action="store_true",
        help="Overwrite existing cover_letter.md",
    )
    p.add_argument(
        "--overwrite-application-letter",
        action="store_true",
        help="Overwrite existing application_letter.md",
    )
    p.add_argument(
        "--overwrite-research-proposal",
        action="store_true",
        help="Overwrite existing research_proposal.md",
    )
    return p


def parse_args() -> argparse.Namespace:
    return make_parser().parse_args()


def _output_by_name(prior_outputs: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in prior_outputs:
        if item.get("name") == name:
            out = item.get("output")
            if isinstance(out, dict):
                return out
    return None


def _selected_track(prior_outputs: list[dict[str, Any]]) -> str:
    track_out = _output_by_name(prior_outputs, "03_track_selector_output.json") or {}
    track = str(track_out.get("selected_track") or "industry").strip().lower()
    return track if track in ("industry", "academic") else "industry"


def resolve_source_cv_markdown(run_dir: Path, prior_outputs: list[dict[str, Any]], task: dict[str, Any]) -> str:
    track = _selected_track(prior_outputs)
    source_path = run_dir / f"cv_{track}_source.md"
    if source_path.is_file():
        return source_path.read_text(encoding="utf-8")
    templates = (task.get("context") or {}).get("cv_templates") or {}
    text = templates.get(track) if isinstance(templates, dict) else ""
    return text if isinstance(text, str) else ""


def experience_inventory(source_markdown: str) -> list[dict[str, Any]]:
    cv = parse_cv_markdown(source_markdown)
    inventory: list[dict[str, Any]] = []
    for item in cv.experience:
        inventory.append(
            {
                "role_key": experience_role_key(item.role, item.company, item.duration),
                "role": item.role,
                "company": item.company,
                "duration": item.duration,
                "source_bullets": list(item.bullets),
                "bullet_count": len(item.bullets),
            }
        )
    return inventory


def sync_run_source_cvs(run_dir: Path) -> None:
    for profile in load_default_profiles():
        text = full_cv_markdown(profile.front_matter, profile.body_markdown)
        (run_dir / f"cv_{profile.track}_source.md").write_text(text, encoding="utf-8")


def refresh_run_tasks(run_dir: Path) -> None:
    profiles = {p.track: p for p in load_default_profiles()}
    templates = {track: p.body_markdown for track, p in profiles.items()}
    for idx, spec in enumerate(SUBAGENT_SPECS, start=1):
        task_path = run_dir / f"{idx:02d}_{spec.name}_task.json"
        if not task_path.is_file():
            continue
        task = load_json(task_path)
        task["purpose"] = spec.purpose
        task["prompt_template"] = spec.prompt_template
        task["required_inputs"] = list(spec.required_inputs)
        task["expected_output_schema"] = spec.output_schema
        ctx = task.setdefault("context", {})
        if isinstance(ctx, dict):
            ctx["cv_templates"] = templates
            user_prompts = read_apply_prompts(run_dir)
            if user_prompts:
                ctx["user_apply_prompts"] = user_prompts
            else:
                ctx.pop("user_apply_prompts", None)
        write_json(task_path, task)
    sync_run_source_cvs(run_dir)


def write_tailored_cv(run_dir: Path, markdown: str) -> Path:
    path = run_dir / "tailored_cv.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def extract_priority_terms(prior_outputs: list[dict[str, Any]]) -> list[str]:
    """Merge ranked JD keywords and parser skills for Skills-line tailoring."""
    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> None:
        cleaned = term.strip()
        low = cleaned.lower()
        if cleaned and low not in seen:
            seen.add(low)
            terms.append(cleaned)

    for out in prior_outputs:
        if not isinstance(out, dict):
            continue
        priority = out.get("priority_keywords")
        if isinstance(priority, list):
            for item in priority:
                if isinstance(item, dict):
                    add(str(item.get("term") or ""))
                else:
                    add(str(item))
        for key in ("must_have_skills", "nice_to_have_skills", "domain_keywords"):
            block = out.get(key)
            if isinstance(block, list):
                for item in block:
                    add(str(item))

    return terms


def normalize_and_persist_bullet_tailor(
    run_dir: Path,
    source_markdown: str,
    raw_output: dict[str, Any],
    *,
    allow_fewer_bullets: bool = False,
    apply_tailored_bullets: bool = False,
    prior_outputs: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], str, list[str]]:
    normalized = normalize_bullet_tailor_output(
        source_markdown,
        raw_output,
        allow_fewer_bullets=allow_fewer_bullets,
        apply_tailored_profile=apply_tailored_bullets,
        apply_tailored_experience=apply_tailored_bullets,
    )
    job_role = resolve_job_role_title(run_dir)
    md, merge_warnings = assemble_final_cv_markdown(
        source_markdown,
        normalized,
        allow_fewer_bullets=allow_fewer_bullets,
        apply_tailored_profile=apply_tailored_bullets,
        apply_tailored_experience=apply_tailored_bullets,
        job_role_title=job_role or None,
        priority_terms=extract_priority_terms(prior_outputs or []),
    )
    warnings = list(normalized.pop("_merge_warnings", None) or []) + merge_warnings
    write_tailored_cv(run_dir, md)
    return normalized, md, warnings


def build_prompt(
    task: dict[str, Any],
    prior_outputs: list[dict[str, Any]],
    *,
    run_dir: Path | None = None,
) -> str:
    required = required_top_level_keys(task.get("expected_output_schema"))
    required_hint = ", ".join(required) if required else "(unknown)"
    agent = str(task.get("agent") or "")
    extras: dict[str, Any] = {}

    if run_dir and agent == "bullet_tailor":
        source_md = resolve_source_cv_markdown(run_dir, prior_outputs, task)
        if source_md.strip():
            extras["selected_cv_text"] = source_md
            extras["experience_inventory"] = experience_inventory(source_md)

    if run_dir and agent in {"ats_checker", "assembler"}:
        tailored_path = run_dir / "tailored_cv.md"
        if tailored_path.is_file():
            extras["tailored_cv_markdown"] = tailored_path.read_text(encoding="utf-8")

    instruction = (
        "Execute this CV tailoring task and return strict JSON only. "
        "No markdown, no prose, no code fences."
    )
    user_apply_prompts = read_apply_prompts(run_dir) if run_dir else ""
    if user_apply_prompts and agent in {"bullet_tailor", "ats_checker"}:
        instruction += (
            " Follow user_apply_prompts when tailoring truthfully; "
            "do not invent employers, dates, metrics, or tools absent from the source CV."
        )

    prompt = {
        "instruction": instruction,
        "task": task,
        "prior_outputs": prior_outputs,
        "validation": {
            "must_be_json_object": True,
            "required_top_level_keys": required,
            "if_unknown_values_use_empty_string_or_empty_list": True,
        },
        "note": f"Ensure output includes top-level keys: {required_hint}",
    }
    if user_apply_prompts:
        prompt["user_apply_prompts"] = user_apply_prompts
    if extras:
        prompt["context_extras"] = extras
    return json.dumps(prompt, ensure_ascii=False, indent=2)


def validate_output_for_step(task: dict[str, Any], output: dict[str, Any]) -> list[str]:
    return validate_output_against_task(task, output)


def render_final_cv(assembler_output: dict[str, Any]) -> str:
    fr = assembler_output.get("final_resume") or {}
    if not isinstance(fr, dict):
        return ""
    lines: list[str] = []
    header = fr.get("header")
    if isinstance(header, str) and header.strip():
        lines.append(header.strip())
        lines.append("")

    summary = fr.get("professional_summary")
    if isinstance(summary, str) and summary.strip():
        lines.append("## Professional Summary")
        lines.append(summary.strip())
        lines.append("")

    skills = fr.get("skills_block")
    if isinstance(skills, list) and skills:
        lines.append("## Skills")
        for s in skills:
            if isinstance(s, str) and s.strip():
                lines.append(f"- {s.strip()}")
        lines.append("")

    exp = fr.get("experience_block")
    if isinstance(exp, list) and exp:
        lines.append("## Experience")
        for item in exp:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            company = str(item.get("company") or "").strip()
            dates = str(item.get("dates") or "").strip()
            title = " - ".join(part for part in (role, company) if part)
            lines.append(f"### {title or 'Role'}")
            if dates:
                lines.append(dates)
            for b in item.get("bullets") or []:
                if isinstance(b, str) and b.strip():
                    lines.append(f"- {b.strip()}")
            lines.append("")

    for section_name, key in (
        ("Education", "education_block"),
        ("Publications", "publications_block"),
        ("Mentoring & Leadership", "mentoring_leadership_block"),
    ):
        block = fr.get(key)
        if isinstance(block, list) and block:
            lines.append(f"## {section_name}")
            for b in block:
                if isinstance(b, str) and b.strip():
                    lines.append(f"- {b.strip()}")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def extract_final_cv_markdown(
    assembler_output: dict[str, Any],
    *,
    run_dir: Path | None = None,
) -> str:
    tailored_path = run_dir / "tailored_cv.md" if run_dir else None
    if tailored_path and tailored_path.is_file():
        return tailored_path.read_text(encoding="utf-8").rstrip() + "\n"

    final_from_resume = render_final_cv(assembler_output)
    if final_from_resume.strip():
        return final_from_resume

    cv_markdown = assembler_output.get("cv_markdown")
    if isinstance(cv_markdown, str) and cv_markdown.strip():
        return cv_markdown.rstrip() + "\n"

    return ""


def programmatic_assembler_output(
    run_dir: Path,
    prior_outputs: list[dict[str, Any]],
    cv_markdown: str,
) -> dict[str, Any]:
    task_path = run_dir / "06_assembler_task.json"
    job_meta = {}
    if task_path.is_file():
        ctx = (load_json(task_path).get("context") or {}).get("job_meta") or {}
        if isinstance(ctx, dict):
            job_meta = ctx
    track = _selected_track(prior_outputs)
    company = job_meta.get("company") if isinstance(job_meta.get("company"), str) else None
    role_title = str(job_meta.get("role_title") or "role").strip()
    return build_assembler_output(
        cv_markdown,
        track=track,
        company=company,
        role_title=role_title,
        company_slug=str(company or ""),
    )


def resolve_profile_photo_cli_arg(profile_photo: Path | None) -> Path | None:
    if profile_photo is None:
        return None
    path = profile_photo.expanduser().resolve()
    if not path.is_file():
        print(f"Warning: profile photo not found: {path}", file=sys.stderr)
        return None
    return path


def try_export_pdf(
    markdown_path: Path,
    pdf_path: Path,
    *,
    profile_photo: Path | None = None,
    document_language: str | None = None,
) -> tuple[bool, str]:
    try:
        render_styled_cv_pdf(
            markdown_path,
            pdf_path,
            profile_photo=profile_photo,
            document_language=document_language,
        )
        return True, ""
    except Exception as err:
        styled_error = str(err).strip() or "unknown error"

    pandoc = shutil.which("pandoc")
    if not pandoc:
        return False, f"Styled PDF failed ({styled_error}); pandoc not found; skipping PDF export."

    wkhtmltopdf = shutil.which("wkhtmltopdf")
    if wkhtmltopdf:
        cmd = [
            pandoc,
            str(markdown_path),
            "-o",
            str(pdf_path),
            "--pdf-engine",
            "wkhtmltopdf",
        ]
    else:
        cmd = [pandoc, str(markdown_path), "-o", str(pdf_path)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as err:
        detail = (err.stderr or err.stdout or "").strip()
        if detail:
            return False, f"Styled PDF failed ({styled_error}); fallback PDF export failed: {detail}"
        return False, f"Styled PDF failed ({styled_error}); fallback PDF export failed."

    return True, ""


def run_single_step(
    *,
    run_dir: Path,
    task_name: str,
    out_name: str,
    prior_outputs: list[dict[str, Any]],
    provider_name: str,
    model: str,
    overwrite: bool,
    dry_run: bool,
    allow_fewer_bullets: bool,
    apply_tailored_bullets: bool,
    metrics: PipelineMetricsCollector | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    task_path = run_dir / task_name
    out_path = run_dir / out_name
    if not task_path.is_file():
        raise RuntimeError(f"Missing task file: {task_path}")
    task = load_json(task_path)
    agent = str(task.get("agent") or "")
    step_stem = out_name.replace("_output.json", "")
    step_started = time.monotonic()

    if out_path.exists() and not overwrite:
        existing = load_json(out_path)
        errors = validate_output_for_step(task, existing)
        if errors:
            raise RuntimeError(f"{out_name} is invalid: {'; '.join(errors)}")
        if out_name == "04_bullet_tailor_output.json":
            source_md = resolve_source_cv_markdown(run_dir, prior_outputs, task)
            if source_md.strip():
                existing, _, warnings = normalize_and_persist_bullet_tailor(
                    run_dir,
                    source_md,
                    existing,
                    allow_fewer_bullets=allow_fewer_bullets,
                    apply_tailored_bullets=apply_tailored_bullets,
                    prior_outputs=prior_outputs,
                )
                write_json(out_path, existing)
                for warning in warnings:
                    print(f"  merge: {warning}")
        print(f"Skip existing: {out_name}")
        if metrics is not None:
            metrics.record_stage(
                name=step_stem,
                started_mono=step_started,
                ended_mono=time.monotonic(),
                provider=provider_name,
                model=model,
                kind="agent" if agent != "assembler" else "deterministic",
                skipped=True,
            )
        return existing, task

    if agent == "assembler":
        if dry_run:
            print("--- 06_assembler_task.json (programmatic; no agent call) ---")
            return None, task
        tailored_path = run_dir / "tailored_cv.md"
        if not tailored_path.is_file():
            bullet_out = _output_by_name(prior_outputs, "04_bullet_tailor_output.json")
            source_md = resolve_source_cv_markdown(run_dir, prior_outputs, task)
            if bullet_out and source_md.strip():
                _, _, warnings = normalize_and_persist_bullet_tailor(
                    run_dir,
                    source_md,
                    bullet_out,
                    allow_fewer_bullets=allow_fewer_bullets,
                    apply_tailored_bullets=apply_tailored_bullets,
                    prior_outputs=prior_outputs,
                )
                for warning in warnings:
                    print(f"  merge: {warning}")
            else:
                raise RuntimeError("Cannot assemble: missing bullet_tailor output or source CV.")
        cv_md = tailored_path.read_text(encoding="utf-8")
        out_obj = programmatic_assembler_output(run_dir, prior_outputs, cv_md)
        write_json(out_path, out_obj)
        print(f"Wrote: {out_path.name} (programmatic)")
        if metrics is not None:
            metrics.record_stage(
                name=step_stem,
                started_mono=step_started,
                ended_mono=time.monotonic(),
                provider=provider_name,
                model=model,
                kind="deterministic",
            )
        return out_obj, task

    prompt = build_prompt(task, prior_outputs, run_dir=run_dir)
    if dry_run:
        print(f"--- {task_name} prompt ---")
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
        return None, task

    backend = (
        get_provider("manual", run_dir=run_dir, step_stem=step_stem)
        if provider_name == "manual"
        else get_provider(provider_name)
    )
    run_result = backend.run(prompt, model=model, cwd=Path.cwd())
    response_text = run_result.text.strip()
    if not response_text:
        raise RuntimeError(f"Empty response for {task_name}")

    token_source = "api" if (
        run_result.tokens_input is not None or run_result.tokens_output is not None
    ) else "none"
    if metrics is not None:
        metrics.record_stage(
            name=step_stem,
            started_mono=step_started,
            ended_mono=time.monotonic(),
            provider=run_result.provider or provider_name,
            model=run_result.model or model,
            kind="agent",
            tokens_input=run_result.tokens_input,
            tokens_output=run_result.tokens_output,
            tokens_source=token_source,
            agent_run_id=run_result.run_id,
            prompt_text=prompt,
            response_text=response_text,
        )

    out_obj = parse_json_response(response_text)
    errors = validate_output_for_step(task, out_obj)
    if errors:
        raise RuntimeError(f"Invalid output for {task_name}: {'; '.join(errors)}")

    if out_name == "04_bullet_tailor_output.json":
        source_md = resolve_source_cv_markdown(run_dir, prior_outputs, task)
        if source_md.strip():
            out_obj, _, warnings = normalize_and_persist_bullet_tailor(
                run_dir,
                source_md,
                out_obj,
                allow_fewer_bullets=allow_fewer_bullets,
                apply_tailored_bullets=apply_tailored_bullets,
                prior_outputs=prior_outputs,
            )
            for warning in warnings:
                print(f"  merge: {warning}")
        else:
            print("Warning: no source CV markdown found; skipping merge enforcement.", file=sys.stderr)

    write_json(out_path, out_obj)
    print(f"Wrote: {out_path.name}")
    return out_obj, task


def run_pipeline(args: argparse.Namespace) -> int:
    from repo_paths import load_repo_dotenv

    load_repo_dotenv()
    run_dir = args.run_dir.expanduser().resolve()
    profile_photo = resolve_profile_photo_cli_arg(args.profile_photo)
    if not run_dir.is_dir():
        print(f"Run folder not found: {run_dir}", file=sys.stderr)
        return 1

    if args.render_only:
        final_path = run_dir / "final_cv.md"
        if not final_path.is_file():
            print("render-only requested but final_cv.md not found.", file=sys.stderr)
            return 8
        if args.no_pdf:
            print("render-only requested with --no-pdf; nothing to do.")
            return 0
        pdf_path = run_dir / "final_cv.pdf"
        ok, msg = try_export_pdf(final_path, pdf_path, profile_photo=profile_photo)
        if ok:
            print(f"Wrote: {pdf_path.name}")
        else:
            print(msg, file=sys.stderr)
            return 9
        if args.language == "no":
            from cv_generation.cv_norwegian import localize_run

            return localize_run(
                run_dir,
                provider=args.provider.strip().lower(),
                model=args.model,
                no_pdf=args.no_pdf,
                profile_photo=profile_photo,
            )
        return 0

    if args.localize_only:
        if args.language != "no":
            print("--localize-only requires --language no", file=sys.stderr)
            return 1
        from cv_generation.cv_norwegian import localize_run

        return localize_run(
            run_dir,
            provider=args.provider.strip().lower(),
            model=args.model,
            no_pdf=args.no_pdf,
            profile_photo=profile_photo,
        )

    provider_name = args.provider.strip().lower()
    default_models = {
        "cursor": "composer-2.5",
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4o",
        "manual": "manual",
    }
    model = (args.model or "").strip() or default_models.get(provider_name, "composer-2.5")

    if args.refresh_tasks:
        refresh_run_tasks(run_dir)
        print("Refreshed task JSON and source CV copies from repo.")
    else:
        sync_run_source_cvs(run_dir)

    prior_outputs: list[dict[str, Any]] = []
    assembler_out: dict[str, Any] | None = None
    print(f"Agent provider: {provider_name} (model={model})")
    metrics_collector: PipelineMetricsCollector | None = None
    if not args.dry_run:
        metrics_collector = PipelineMetricsCollector(provider=provider_name, model=model)

    for task_name, out_name in task_output_pairs():
        try:
            out_obj, _ = run_single_step(
                run_dir=run_dir,
                task_name=task_name,
                out_name=out_name,
                prior_outputs=prior_outputs,
                provider_name=provider_name,
                model=model,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                allow_fewer_bullets=args.allow_fewer_bullets,
                apply_tailored_bullets=args.apply_tailored_bullets,
                metrics=metrics_collector,
            )
        except RuntimeError as err:
            print(f"Agent error ({task_name}): {err}", file=sys.stderr)
            return 2

        if out_obj is not None:
            prior_outputs.append({"name": out_name, "output": out_obj})
            if out_name == "06_assembler_output.json":
                assembler_out = out_obj

    if assembler_out is None and (run_dir / "06_assembler_output.json").is_file():
        assembler_out = load_json(run_dir / "06_assembler_output.json")

    if assembler_out or (run_dir / "tailored_cv.md").is_file():
        final_path = run_dir / "final_cv.md"
        assembler_path = run_dir / "06_assembler_output.json"
        keep_existing_markdown = (
            final_path.exists()
            and assembler_path.exists()
            and not args.overwrite
            and final_path.stat().st_mtime > assembler_path.stat().st_mtime
        )

        if keep_existing_markdown:
            print("Using newer existing final_cv.md (assembler output is older).")
            if not args.no_pdf:
                pdf_path = run_dir / "final_cv.pdf"
                ok, msg = try_export_pdf(final_path, pdf_path, profile_photo=profile_photo)
                if ok:
                    print(f"Wrote: {pdf_path.name}")
                else:
                    print(msg, file=sys.stderr)
        else:
            final_md = extract_final_cv_markdown(assembler_out or {}, run_dir=run_dir)
            if final_md.strip():
                final_path.write_text(final_md, encoding="utf-8")
                print(f"Wrote: {final_path.name}")
                if not args.no_pdf:
                    pdf_path = run_dir / "final_cv.pdf"
                    ok, msg = try_export_pdf(final_path, pdf_path, profile_photo=profile_photo)
                    if ok:
                        print(f"Wrote: {pdf_path.name}")
                    else:
                        print(msg, file=sys.stderr)
            else:
                print("Assembler output present but no final CV content found.", file=sys.stderr)
                return 6
    else:
        print("No assembler output found; final_cv.md not generated.", file=sys.stderr)
        return 7

    cover_letter_result = None
    try:
        cover_letter_result = maybe_generate_cover_letter(
            run_dir,
            prior_outputs=prior_outputs,
            provider_name=provider_name,
            model=model,
            dry_run=args.dry_run,
            no_pdf=args.no_pdf,
            overwrite=args.overwrite or args.overwrite_cover_letter,
            generate=args.generate_cover_letter,
            metrics=metrics_collector,
            output_language=args.language,
        )
        maybe_generate_application_letter(
            run_dir,
            prior_outputs=prior_outputs,
            provider_name=provider_name,
            model=model,
            dry_run=args.dry_run,
            no_pdf=args.no_pdf,
            overwrite=args.overwrite_application_letter,
            generate=bool(args.generate_application_letter),
            metrics=metrics_collector,
        )
        maybe_generate_research_proposal(
            run_dir,
            prior_outputs=prior_outputs,
            provider_name=provider_name,
            model=model,
            dry_run=args.dry_run,
            no_pdf=args.no_pdf,
            overwrite=args.overwrite_research_proposal,
            generate=bool(args.generate_research_proposal),
            metrics=metrics_collector,
        )
    except RuntimeError:
        return 10

    pipeline_language = args.language
    if pipeline_language != "no":
        from cv_generation.cover_letter_generator import resolve_output_language

        meta_language = resolve_output_language(run_dir, prior_outputs)
        if meta_language == "no":
            print("Using output_language=no from run job_meta (CLI --language was en).")
            pipeline_language = "no"

    if pipeline_language == "no":
        from cv_generation.cv_norwegian import localize_run

        loc_artifacts: tuple[str, ...] = ("cv", "cover-letter")
        if cover_letter_result is not None and cover_letter_result.wrote_norwegian_direct:
            loc_artifacts = ("cv",)
            print("Skip cover-letter localize: cover_letter_no.md already written.")
        loc_code = localize_run(
            run_dir,
            artifacts=loc_artifacts,  # type: ignore[arg-type]
            provider=provider_name,
            model=model,
            no_pdf=args.no_pdf,
            profile_photo=profile_photo,
            metrics=metrics_collector,
        )
        if loc_code != 0:
            if metrics_collector is not None:
                write_pipeline_metrics(run_dir, metrics_collector.finalize())
            return loc_code
    elif cover_letter_result is not None and cover_letter_result.wrote_norwegian_direct:
        # English apply but agent returned Norwegian — already saved as cover_letter_no.md.
        print(
            "Note: cover_letter_no.md was written while --language en; "
            "re-run with --language no to also generate final_cv_no.md.",
            file=sys.stderr,
        )

    if metrics_collector is not None:
        metrics_path = write_pipeline_metrics(run_dir, metrics_collector.finalize())
        print(f"Wrote: {metrics_path.name}")

    return 0


def main() -> int:
    return run_pipeline(parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
