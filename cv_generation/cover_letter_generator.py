#!/usr/bin/env python3
"""
Generate cover_letter.md after final_cv.md when the posting requires it.

Triggered by ``detect_supplementary_artifacts()`` / ``application_artifacts.md``
for industry-track runs. Academic ``application_letter.md`` / ``research_proposal.md``
are not generated here yet.
"""
from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from cv_generation.agent_contract import load_json
from cv_generation.agent_providers import AgentRunResult, get_provider
from cv_generation.apply_prompts import read_apply_prompts
from cv_generation.cv_application_artifacts import detect_supplementary_artifacts
from cv_generation.cv_norwegian import looks_like_norwegian_cover_letter, strip_markdown_response
from cv_generation.cv_style import COVER_LETTER_VOICE, INSTITUTION_INTEGRITY_HINT, NORWEGIAN_COVER_LETTER_LENGTH_HINT

if TYPE_CHECKING:
    from cv_generation.pipeline_metrics import PipelineMetricsCollector

COVER_LETTER_FILENAME = "cover_letter.md"
COVER_LETTER_NO_FILENAME = "cover_letter_no.md"
STEP_STEM = "07_cover_letter"


@dataclass(frozen=True)
class CoverLetterResult:
    generated: bool
    skipped_reason: str | None = None
    markdown_path: Path | None = None
    pdf_path: Path | None = None
    wrote_norwegian_direct: bool = False
    """True when Norwegian prose was saved as cover_letter_no.md (skip cover-letter localize)."""


def cover_letter_markdown_path(run_dir: Path) -> Path:
    return run_dir / COVER_LETTER_FILENAME


def manual_cover_letter_prompt_path(run_dir: Path) -> Path:
    return run_dir / f"{STEP_STEM}_prompt.txt"


def manual_cover_letter_response_path(run_dir: Path) -> Path:
    return run_dir / f"{STEP_STEM}_output.manual.md"


def resolve_track(run_dir: Path, prior_outputs: list[dict[str, Any]] | None = None) -> str:
    if prior_outputs:
        for item in prior_outputs:
            if item.get("name") == "03_track_selector_output.json":
                out = item.get("output")
                if isinstance(out, dict):
                    track = str(out.get("selected_track") or "").strip().lower()
                    if track in ("industry", "academic"):
                        return track
    track_path = run_dir / "03_track_selector_output.json"
    if track_path.is_file():
        track = str(load_json(track_path).get("selected_track") or "").strip().lower()
        if track in ("industry", "academic"):
            return track
    return "industry"


def resolve_role_company(
    run_dir: Path,
    prior_outputs: list[dict[str, Any]] | None = None,
) -> tuple[str, str | None]:
    parser_out: dict[str, Any] | None = None
    if prior_outputs:
        for item in prior_outputs:
            if item.get("name") == "01_jd_parser_output.json":
                out = item.get("output")
                if isinstance(out, dict):
                    parser_out = out
                    break
    if parser_out is None:
        parser_path = run_dir / "01_jd_parser_output.json"
        if parser_path.is_file():
            parser_out = load_json(parser_path)
    if not parser_out:
        return "role", None
    role = str(parser_out.get("role_title") or "role").strip()
    company_raw = parser_out.get("company")
    company = str(company_raw).strip() if isinstance(company_raw, str) and company_raw.strip() else None
    return role, company


def read_job_posting(run_dir: Path) -> str:
    path = run_dir / "job_posting.txt"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def is_cover_letter_required(run_dir: Path, *, track: str) -> bool:
    """True when industry track and posting detection flags cover_letter.md."""
    if track != "industry":
        return False
    job_text = read_job_posting(run_dir)
    if not job_text.strip():
        return False
    detected = detect_supplementary_artifacts(job_text, track=track)
    return any(artifact.filename == COVER_LETTER_FILENAME for artifact in detected)


def build_cover_letter_prompt(
    *,
    role_title: str,
    company: str | None,
    job_posting: str,
    final_cv_markdown: str,
    user_apply_prompts: str = "",
    output_language: str = "en",
) -> str:
    instruction = (
        "Write a tailored cover letter as markdown only. "
        "Return the full letter text; no JSON, no code fences, no commentary."
    )
    if user_apply_prompts:
        instruction += (
            " Follow user_apply_prompts when tailoring truthfully; "
            "do not invent employers, dates, metrics, or tools absent from the CV."
        )
    lang = (output_language or "en").strip().lower()
    body_structure = "Four substantive paragraphs plus brief closing"
    localization_note = ""
    if lang == "no":
        instruction += (
            " Write the letter entirely in English (not Norwegian), even if the job posting "
            "is in Norwegian. This letter will be localized to Norwegian B1 in a later step; "
            "keep English concise: short sentences, one idea per sentence, four short body "
            "paragraphs max."
        )
        localization_note = (
            f"Will be localized to Norwegian B1. {NORWEGIAN_COVER_LETTER_LENGTH_HINT} "
            "Include one sentence on personality and team fit for the Norwegian version. "
            "Draft language must be English."
        )
        body_structure = (
            "Four short body paragraphs plus brief closing "
            "(concise English draft for Norwegian B1 localization)"
        )
    else:
        instruction += (
            " Write the letter entirely in English, even if the job posting is in Norwegian."
        )
    payload: dict[str, Any] = {
        "instruction": instruction,
        "voice_rules": list(COVER_LETTER_VOICE),
        "institution_rules": INSTITUTION_INTEGRITY_HINT,
        "structure": {
            "header": "Applicant contact block (reuse placeholders from final_cv.md)",
            "date": "Today's date in long form",
            "addressee": "Hiring team / company / location from posting when known",
            "heading": "**Re: <role title>** (only bold allowed in body)",
            "body": body_structure,
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
    if localization_note:
        payload["localization_note"] = localization_note
        payload["output_language"] = "no"
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _call_cover_letter_agent(
    prompt: str,
    *,
    run_dir: Path,
    provider_name: str,
    model: str,
) -> AgentRunResult:
    if provider_name == "manual":
        prompt_path = manual_cover_letter_prompt_path(run_dir)
        response_path = manual_cover_letter_response_path(run_dir)
        prompt_path.write_text(prompt, encoding="utf-8")
        if not response_path.is_file():
            raise RuntimeError(
                "Manual mode requires an external agent step.\n"
                f"1. Open the prompt file:\n  {prompt_path}\n"
                f"2. Run it with Claude/Codex/another agent.\n"
                f"3. Save the cover letter markdown to:\n  {response_path}"
            )
        text = response_path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Manual response file is empty: {response_path}")
        return AgentRunResult(text=text, provider="manual", model=model or "manual")

    backend = get_provider(provider_name)
    if hasattr(backend, "run_markdown"):
        return backend.run_markdown(prompt, model=model, cwd=Path.cwd())
    return backend.run(prompt, model=model, cwd=Path.cwd())


def resolve_output_language(
    run_dir: Path,
    prior_outputs: list[dict[str, Any]] | None = None,
) -> str:
    if prior_outputs:
        for item in prior_outputs:
            if item.get("name") == "job_meta.json":
                out = item.get("output")
                if isinstance(out, dict):
                    lang = str(out.get("output_language") or "").strip().lower()
                    if lang in ("en", "no"):
                        return lang
    meta_path = run_dir / "job_meta.json"
    if meta_path.is_file():
        lang = str(load_json(meta_path).get("output_language") or "").strip().lower()
        if lang in ("en", "no"):
            return lang
    # Stashed by run_cv_tailoring inside each *_task.json context.job_meta.
    for task_path in sorted(run_dir.glob("0*_task.json")):
        try:
            task = load_json(task_path)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            continue
        ctx = task.get("context") if isinstance(task, dict) else None
        if not isinstance(ctx, dict):
            continue
        job_meta = ctx.get("job_meta")
        if not isinstance(job_meta, dict):
            continue
        lang = str(job_meta.get("output_language") or "").strip().lower()
        if lang in ("en", "no"):
            return lang
    artifacts = run_dir / "application_artifacts.md"
    if artifacts.is_file():
        text = artifacts.read_text(encoding="utf-8")
        if re.search(r"Output language:.*\(`no`\)", text):
            return "no"
        if re.search(r"Output language:.*\(`en`\)", text):
            return "en"
    return "en"


def generate_cover_letter_markdown(
    run_dir: Path,
    *,
    prior_outputs: list[dict[str, Any]] | None = None,
    provider_name: str,
    model: str,
    dry_run: bool = False,
    output_language: str | None = None,
) -> tuple[str | None, str]:
    final_cv_path = run_dir / "final_cv.md"
    if not final_cv_path.is_file():
        raise RuntimeError("Cannot generate cover letter: final_cv.md not found.")
    final_cv_md = final_cv_path.read_text(encoding="utf-8")
    role_title, company = resolve_role_company(run_dir, prior_outputs)
    job_posting = read_job_posting(run_dir)
    user_apply_prompts = read_apply_prompts(run_dir)
    resolved_language = output_language or resolve_output_language(run_dir, prior_outputs)
    prompt = build_cover_letter_prompt(
        role_title=role_title,
        company=company,
        job_posting=job_posting,
        final_cv_markdown=final_cv_md,
        user_apply_prompts=user_apply_prompts,
        output_language=resolved_language,
    )
    if dry_run:
        return None, prompt

    result = _call_cover_letter_agent(
        prompt,
        run_dir=run_dir,
        provider_name=provider_name,
        model=model,
    )
    letter = strip_markdown_response(result.text)
    if not letter.strip():
        raise RuntimeError("Cover letter agent returned empty markdown.")
    return letter, prompt


def render_cover_letter_pdf(
    run_dir: Path,
    *,
    no_pdf: bool = False,
    markdown_name: str = COVER_LETTER_FILENAME,
) -> Path | None:
    if no_pdf:
        return None
    md_path = run_dir / markdown_name
    if not md_path.is_file():
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


def maybe_generate_cover_letter(
    run_dir: Path,
    *,
    prior_outputs: list[dict[str, Any]] | None = None,
    provider_name: str,
    model: str,
    dry_run: bool = False,
    no_pdf: bool = False,
    overwrite: bool = False,
    generate: bool | None = None,
    metrics: PipelineMetricsCollector | None = None,
    output_language: str | None = None,
) -> CoverLetterResult:
    run_dir = run_dir.expanduser().resolve()
    track = resolve_track(run_dir, prior_outputs)
    md_path = cover_letter_markdown_path(run_dir)

    if generate is False:
        print("Skip cover letter: disabled by user.")
        return CoverLetterResult(generated=False, skipped_reason="disabled")

    if track != "industry":
        reason = f"industry cover letter skipped for {track} track"
        print(f"Skip cover letter: {reason}.")
        return CoverLetterResult(generated=False, skipped_reason=reason)

    if generate is None and not is_cover_letter_required(run_dir, track=track):
        reason = "not required for this posting/track"
        print(f"Skip cover letter: {reason}.")
        return CoverLetterResult(generated=False, skipped_reason=reason)

    if md_path.is_file() and not overwrite:
        print(f"Skip existing: {COVER_LETTER_FILENAME}")
        if metrics is not None:
            metrics.record_stage(
                name=STEP_STEM,
                started_mono=time.monotonic(),
                ended_mono=time.monotonic(),
                provider=provider_name,
                model=model,
                kind="agent",
                skipped=True,
            )
        pdf_path = render_cover_letter_pdf(run_dir, no_pdf=no_pdf)
        return CoverLetterResult(
            generated=False,
            skipped_reason="already exists",
            markdown_path=md_path,
            pdf_path=pdf_path,
        )

    step_started = time.monotonic()
    prompt = ""
    try:
        letter_md, prompt = generate_cover_letter_markdown(
            run_dir,
            prior_outputs=prior_outputs,
            provider_name=provider_name,
            model=model,
            dry_run=dry_run,
            output_language=output_language,
        )
    except RuntimeError as err:
        print(f"Cover letter error: {err}", file=sys.stderr)
        raise

    if dry_run:
        print(f"--- {STEP_STEM} prompt ---")
        print(prompt[:1200] + ("..." if len(prompt) > 1200 else ""))
        return CoverLetterResult(generated=False, skipped_reason="dry-run")

    assert letter_md is not None
    wrote_norwegian_direct = False
    target_name = COVER_LETTER_FILENAME
    if looks_like_norwegian_cover_letter(letter_md):
        # Never store Norwegian prose as cover_letter.md (English is canonical).
        target_name = COVER_LETTER_NO_FILENAME
        wrote_norwegian_direct = True
        print(
            "Cover letter agent returned Norwegian; saving as "
            f"{COVER_LETTER_NO_FILENAME} (not {COVER_LETTER_FILENAME}).",
            file=sys.stderr,
        )

    target_path = run_dir / target_name
    target_path.write_text(letter_md, encoding="utf-8")
    print(f"Wrote: {target_name}")

    pdf_path = render_cover_letter_pdf(run_dir, no_pdf=no_pdf, markdown_name=target_name)
    if pdf_path is not None:
        print(f"Wrote: {pdf_path.name}")

    if metrics is not None:
        metrics.record_stage(
            name=STEP_STEM,
            started_mono=step_started,
            ended_mono=time.monotonic(),
            provider=provider_name,
            model=model,
            kind="agent",
            prompt_text=prompt,
            response_text=letter_md,
        )

    return CoverLetterResult(
        generated=True,
        markdown_path=target_path,
        pdf_path=pdf_path,
        wrote_norwegian_direct=wrote_norwegian_direct,
    )
