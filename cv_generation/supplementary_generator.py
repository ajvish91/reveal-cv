#!/usr/bin/env python3
"""
Generate academic supplementary markdown (application_letter, research_proposal).

Uses the same agent ``run_markdown`` pattern as ``cover_letter_generator``.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from cv_generation.agent_providers import AgentRunResult, get_provider
from cv_generation.apply_prompts import read_apply_prompts
from cv_generation.cover_letter_generator import (
    read_job_posting,
    resolve_role_company,
    resolve_track,
)
from cv_generation.cv_norwegian import strip_markdown_response
from cv_generation.cv_style import COVER_LETTER_VOICE, INSTITUTION_INTEGRITY_HINT

if TYPE_CHECKING:
    from cv_generation.pipeline_metrics import PipelineMetricsCollector

APPLICATION_LETTER_FILENAME = "application_letter.md"
RESEARCH_PROPOSAL_FILENAME = "research_proposal.md"
STEP_APPLICATION_LETTER = "08_application_letter"
STEP_RESEARCH_PROPOSAL = "09_research_proposal"


@dataclass(frozen=True)
class SupplementaryDocResult:
    filename: str
    generated: bool
    skipped_reason: str | None = None
    markdown_path: Path | None = None
    pdf_path: Path | None = None


def _manual_paths(run_dir: Path, step_stem: str) -> tuple[Path, Path]:
    return run_dir / f"{step_stem}_prompt.txt", run_dir / f"{step_stem}_output.manual.md"


def _call_markdown_agent(
    prompt: str,
    *,
    run_dir: Path,
    step_stem: str,
    provider_name: str,
    model: str,
) -> AgentRunResult:
    if provider_name == "manual":
        prompt_path, response_path = _manual_paths(run_dir, step_stem)
        prompt_path.write_text(prompt, encoding="utf-8")
        if not response_path.is_file():
            raise RuntimeError(
                "Manual mode requires an external agent step.\n"
                f"1. Open the prompt file:\n  {prompt_path}\n"
                f"2. Run it with Claude/Codex/another agent.\n"
                f"3. Save the markdown to:\n  {response_path}"
            )
        text = response_path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Manual response file is empty: {response_path}")
        return AgentRunResult(text=text, provider="manual", model=model or "manual")

    backend = get_provider(provider_name)
    if hasattr(backend, "run_markdown"):
        return backend.run_markdown(prompt, model=model, cwd=Path.cwd())
    return backend.run(prompt, model=model, cwd=Path.cwd())


def _render_plain_pdf(run_dir: Path, md_path: Path, *, no_pdf: bool) -> Path | None:
    if no_pdf or not md_path.is_file():
        return None
    pdf_path = md_path.with_suffix(".pdf")
    from cv_generation.render_cv_pdf import _looks_like_cover_letter, _render_plain_markdown_pdf

    text = md_path.read_text(encoding="utf-8")
    _render_plain_markdown_pdf(
        md_path,
        pdf_path,
        normalize_upper_names=_looks_like_cover_letter(md_path, text),
    )
    return pdf_path if pdf_path.is_file() else None


def build_application_letter_prompt(
    *,
    role_title: str,
    company: str | None,
    job_posting: str,
    final_cv_markdown: str,
    user_apply_prompts: str = "",
) -> str:
    instruction = (
        "Write a tailored academic application letter as markdown only. "
        "Return the full letter text; no JSON, no code fences, no commentary."
    )
    if user_apply_prompts:
        instruction += (
            " Follow user_apply_prompts when tailoring truthfully; "
            "do not invent employers, dates, metrics, or tools absent from the CV."
        )
    payload: dict[str, Any] = {
        "instruction": instruction,
        "voice_rules": list(COVER_LETTER_VOICE),
        "institution_rules": INSTITUTION_INTEGRITY_HINT,
        "structure": {
            "header": "Applicant contact block (reuse placeholders from final_cv.md)",
            "date": "Today's date in long form",
            "addressee": "Hiring committee / department from posting when known",
            "heading": "**Re: <role title>** (only bold allowed in body)",
            "body": "Four substantive paragraphs plus brief closing; link to research fit",
            "signature": "Sincerely, then MITCH EVANS on its own line",
        },
        "placeholders": {
            "name": "MITCH EVANS (all caps in header and signature)",
            "note": "Reuse anonymized tokens from final_cv.md; do not invent experience.",
        },
        "role_title": role_title,
        "company": company or "",
        "job_posting": job_posting,
        "final_cv_markdown": final_cv_markdown,
    }
    if user_apply_prompts:
        payload["user_apply_prompts"] = user_apply_prompts
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_research_proposal_prompt(
    *,
    role_title: str,
    company: str | None,
    job_posting: str,
    final_cv_markdown: str,
    user_apply_prompts: str = "",
) -> str:
    instruction = (
        "Write a concise research proposal as markdown only for a postdoc/researcher call. "
        "Return the full document; no JSON, no code fences, no commentary."
    )
    if user_apply_prompts:
        instruction += (
            " Follow user_apply_prompts when tailoring truthfully; "
            "do not invent employers, dates, metrics, or tools absent from the CV."
        )
    payload: dict[str, Any] = {
        "instruction": instruction,
        "structure": {
            "title": "Working title aligned with the posting",
            "sections": [
                "Background and motivation",
                "Research questions and approach",
                "Methods and expected outcomes",
                "Fit with the host group and timeline",
            ],
        },
        "placeholders": {
            "name": "MITCH EVANS when a signature block is needed",
            "note": "Ground the proposal in experience from final_cv.md only.",
        },
        "role_title": role_title,
        "company": company or "",
        "job_posting": job_posting,
        "final_cv_markdown": final_cv_markdown,
    }
    if user_apply_prompts:
        payload["user_apply_prompts"] = user_apply_prompts
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _generate_doc(
    run_dir: Path,
    *,
    filename: str,
    step_stem: str,
    build_prompt,
    prior_outputs: list[dict[str, Any]] | None,
    provider_name: str,
    model: str,
    dry_run: bool,
    no_pdf: bool,
    overwrite: bool,
    metrics: PipelineMetricsCollector | None,
) -> SupplementaryDocResult:
    md_path = run_dir / filename
    if md_path.is_file() and not overwrite:
        print(f"Skip existing: {filename}")
        if metrics is not None:
            metrics.record_stage(
                name=step_stem,
                started_mono=time.monotonic(),
                ended_mono=time.monotonic(),
                provider=provider_name,
                model=model,
                kind="agent",
                skipped=True,
            )
        return SupplementaryDocResult(
            filename=filename,
            generated=False,
            skipped_reason="already exists",
            markdown_path=md_path,
            pdf_path=_render_plain_pdf(run_dir, md_path, no_pdf=no_pdf),
        )

    final_cv_path = run_dir / "final_cv.md"
    if not final_cv_path.is_file():
        raise RuntimeError(f"Cannot generate {filename}: final_cv.md not found.")

    role_title, company = resolve_role_company(run_dir, prior_outputs)
    job_posting = read_job_posting(run_dir)
    user_apply_prompts = read_apply_prompts(run_dir)
    prompt = build_prompt(
        role_title=role_title,
        company=company,
        job_posting=job_posting,
        final_cv_markdown=final_cv_path.read_text(encoding="utf-8"),
        user_apply_prompts=user_apply_prompts,
    )
    if dry_run:
        print(f"--- {step_stem} prompt ---")
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
        return SupplementaryDocResult(filename=filename, generated=False, skipped_reason="dry-run")

    step_started = time.monotonic()
    result = _call_markdown_agent(
        prompt,
        run_dir=run_dir,
        step_stem=step_stem,
        provider_name=provider_name,
        model=model,
    )
    body = strip_markdown_response(result.text)
    if not body.strip():
        raise RuntimeError(f"{filename} agent returned empty markdown.")
    md_path.write_text(body, encoding="utf-8")
    print(f"Wrote: {filename}")
    pdf_path = _render_plain_pdf(run_dir, md_path, no_pdf=no_pdf)
    if pdf_path is not None:
        print(f"Wrote: {pdf_path.name}")

    if metrics is not None:
        metrics.record_stage(
            name=step_stem,
            started_mono=step_started,
            ended_mono=time.monotonic(),
            provider=provider_name,
            model=model,
            kind="agent",
            prompt_text=prompt,
            response_text=body,
        )

    return SupplementaryDocResult(
        filename=filename,
        generated=True,
        markdown_path=md_path,
        pdf_path=pdf_path,
    )


def maybe_generate_application_letter(
    run_dir: Path,
    *,
    prior_outputs: list[dict[str, Any]] | None = None,
    provider_name: str,
    model: str,
    dry_run: bool = False,
    no_pdf: bool = False,
    overwrite: bool = False,
    generate: bool = True,
    metrics: PipelineMetricsCollector | None = None,
) -> SupplementaryDocResult:
    if not generate:
        print("Skip application letter: disabled by user.")
        return SupplementaryDocResult(
            filename=APPLICATION_LETTER_FILENAME,
            generated=False,
            skipped_reason="disabled",
        )
    track = resolve_track(run_dir, prior_outputs)
    if track != "academic":
        print("Skip application letter: not academic track.")
        return SupplementaryDocResult(
            filename=APPLICATION_LETTER_FILENAME,
            generated=False,
            skipped_reason="not academic track",
        )
    return _generate_doc(
        run_dir,
        filename=APPLICATION_LETTER_FILENAME,
        step_stem=STEP_APPLICATION_LETTER,
        build_prompt=build_application_letter_prompt,
        prior_outputs=prior_outputs,
        provider_name=provider_name,
        model=model,
        dry_run=dry_run,
        no_pdf=no_pdf,
        overwrite=overwrite,
        metrics=metrics,
    )


def maybe_generate_research_proposal(
    run_dir: Path,
    *,
    prior_outputs: list[dict[str, Any]] | None = None,
    provider_name: str,
    model: str,
    dry_run: bool = False,
    no_pdf: bool = False,
    overwrite: bool = False,
    generate: bool = True,
    metrics: PipelineMetricsCollector | None = None,
) -> SupplementaryDocResult:
    if not generate:
        print("Skip research proposal: disabled by user.")
        return SupplementaryDocResult(
            filename=RESEARCH_PROPOSAL_FILENAME,
            generated=False,
            skipped_reason="disabled",
        )
    track = resolve_track(run_dir, prior_outputs)
    if track != "academic":
        print("Skip research proposal: not academic track.")
        return SupplementaryDocResult(
            filename=RESEARCH_PROPOSAL_FILENAME,
            generated=False,
            skipped_reason="not academic track",
        )
    return _generate_doc(
        run_dir,
        filename=RESEARCH_PROPOSAL_FILENAME,
        step_stem=STEP_RESEARCH_PROPOSAL,
        build_prompt=build_research_proposal_prompt,
        prior_outputs=prior_outputs,
        provider_name=provider_name,
        model=model,
        dry_run=dry_run,
        no_pdf=no_pdf,
        overwrite=overwrite,
        metrics=metrics,
    )
