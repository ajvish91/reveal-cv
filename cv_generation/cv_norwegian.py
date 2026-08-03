#!/usr/bin/env python3
"""
Norwegian B1 localization pass for tailored CV and cover letter artifacts.

English markdown remains canonical for ATS and deanonymize mapping keys.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from cv_generation.agent_providers import get_provider
from cv_generation.cv_style import (
    NORWEGIAN_B1_COVER_LETTER_VOICE,
    NORWEGIAN_B1_CV_VOICE,
    NORWEGIAN_COVER_LETTER_BODY_MAX_WORDS,
    NORWEGIAN_COVER_LETTER_LENGTH_HINT,
    SECTION_LABELS_NO,
)

if TYPE_CHECKING:
    from cv_generation.pipeline_metrics import PipelineMetricsCollector

REFERENCE_SAMPLES_PATH = Path(__file__).resolve().parent / "reference" / "norwegian_b1_writing_samples.md"

ArtifactKind = Literal["cv", "cover-letter"]

SOURCE_OUTPUT: dict[ArtifactKind, tuple[str, str]] = {
    "cv": ("final_cv.md", "final_cv_no.md"),
    "cover-letter": ("cover_letter.md", "cover_letter_no.md"),
}

_NO_CV_SECTION = re.compile(
    r"(?im)^##\s+(Navn|Profil|Erfaring|Stilling|Kontakt|Ferdigheter|Utdanning)\s*$"
)
_NO_LETTER_MARKERS = re.compile(
    r"(?i)\b(jeg|stillingen|arbeidet|søknaden|med vennlig hilsen|\*\*Ang:)\b"
)


def looks_like_norwegian_cv(markdown: str) -> bool:
    """True when markdown uses Norwegian CV section labels / H1."""
    for line in markdown.splitlines():
        if line.startswith("# "):
            heading = line[2:].strip().lower()
            if "bransje" in heading or heading == "cv" or "akademisk" in heading:
                return True
            break
    return bool(_NO_CV_SECTION.search(markdown))


def looks_like_norwegian_cover_letter(markdown: str) -> bool:
    """Heuristic: body uses common Bokmål markers (not just a Norwegian role title)."""
    return bool(_NO_LETTER_MARKERS.search(markdown))


def norwegian_output_name(artifact: ArtifactKind) -> str:
    return SOURCE_OUTPUT[artifact][1]


_EN_MONTH_TO_NO: dict[str, str] = {
    "jan": "jan.",
    "feb": "feb.",
    "mar": "mars",
    "apr": "apr.",
    "may": "mai",
    "jun": "juni",
    "jul": "juli",
    "aug": "aug.",
    "sep": "sep.",
    "oct": "okt.",
    "nov": "nov.",
    "dec": "des.",
}

_EXPERIENCE_ROLE_EN_TO_NO: dict[str, str] = {
    "Professional Activities": "Profesjonelle aktiviteter",
    "Postdoctoral Researcher": "Postdoktor",
    "Ph.D. Student in AI": "Ph.D.-student i AI",
    "Research Engineer": "Forskningsingeniør",
    "Research Assistant": "Forskningsassistent",
    "Backend Developer": "Backend-utvikler",
    "Assistant Engineer": "Assisterende ingeniør",
}

_DESIGNATION_EN_TO_NO: dict[str, str] = {
    "SENIOR AI PLATFORM ENGINEER": "SENIOR AI-PLATTFORMINGENIØR",
    "ML/AI ENGINEER": "ML/AI-INGENIØR",
    "AI ENGINEER": "AI-INGENIØR",
}

_HOBBY_EN_TO_NO: dict[str, str] = {
    "Skiing": "Ski",
    "Backpacking": "Fotturer",
    "Hunting": "Jakt",
    "Social events": "Sosiale arrangementer",
}


def load_writing_samples() -> str:
    if REFERENCE_SAMPLES_PATH.is_file():
        return REFERENCE_SAMPLES_PATH.read_text(encoding="utf-8").strip()
    return ""


def detect_track(markdown: str) -> str:
    first = ""
    for line in markdown.splitlines():
        if line.startswith("# "):
            first = line[2:].strip().lower()
            break
    if "academic" in first or "akademisk" in first:
        return "academic"
    return "industry"


def _experience_section_lines(markdown: str) -> list[str]:
    """Lines inside ## Experience / ## Erfaring until next ##."""
    lines = markdown.splitlines()
    in_section = False
    collected: list[str] = []
    for line in lines:
        lower = line.strip().lower()
        if lower.startswith("## "):
            if in_section:
                break
            if lower in ("## experience", "## erfaring", "## research experience", "## forskningserfaring"):
                in_section = True
            continue
        if in_section:
            collected.append(line)
    return collected


def count_experience_roles(markdown: str) -> int:
    return sum(1 for line in _experience_section_lines(markdown) if line.startswith("### "))


def count_experience_bullets(markdown: str) -> int:
    return sum(
        1
        for line in _experience_section_lines(markdown)
        if line.strip().startswith("- ")
    )


def validate_localized_cv(source_md: str, localized_md: str) -> list[str]:
    warnings: list[str] = []
    src_roles = count_experience_roles(source_md)
    out_roles = count_experience_roles(localized_md)
    if src_roles and out_roles != src_roles:
        warnings.append(f"experience role count {out_roles} != source {src_roles}")

    src_bullets = count_experience_bullets(source_md)
    out_bullets = count_experience_bullets(localized_md)
    if src_bullets and out_bullets != src_bullets:
        warnings.append(f"experience bullet count {out_bullets} != source {src_bullets}")

    required_no = ("## profil", "## kontakt", "## erfaring", "## utdanning")
    lower = localized_md.lower()
    for header in required_no:
        if header not in lower and header.replace("profil", "sammendrag") not in lower:
            if header == "## profil" and "## sammendrag" in lower:
                continue
            warnings.append(f"missing Norwegian section {header}")
    return warnings


def strip_markdown_response(raw: str) -> str:
    txt = raw.strip()
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-z]*\n?", "", txt)
        txt = re.sub(r"\n?```\s*$", "", txt)
    return txt.strip() + "\n"


def _month_token_to_no(token: str) -> str:
    key = token.strip().lower()[:3]
    return _EN_MONTH_TO_NO.get(key, token)


def localize_dates_no(text: str) -> str:
    """Convert English month names and Present to Norwegian CV date style."""

    def birth_date(match: re.Match[str]) -> str:
        day, month, year = match.group(1), match.group(2), match.group(3)
        return f"{day}. {_month_token_to_no(month)} {year}"

    out = re.sub(
        r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b",
        birth_date,
        text,
        flags=re.IGNORECASE,
    )

    def month_year(match: re.Match[str]) -> str:
        return f"{_month_token_to_no(match.group(1))} {match.group(2)}"

    out = re.sub(
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{4})\b",
        month_year,
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(r"\bPresent\b", "nå", out, flags=re.IGNORECASE)
    out = re.sub(r"(\d{4})\s+-\s+(\d{4})", r"\1 – \2", out)
    out = re.sub(
        r"((?:jan\.|feb\.|mars|apr\.|mai|juni|juli|aug\.|sep\.|okt\.|nov\.|des\.)\s+\d{4})\s+-\s+"
        r"((?:jan\.|feb\.|mars|apr\.|mai|juni|juli|aug\.|sep\.|okt\.|nov\.|des\.)\s+\d{4}|nå)",
        r"\1 – \2",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"((?:jan\.|feb\.|mars|apr\.|mai|juni|juli|aug\.|sep\.|okt\.|nov\.|des\.)\s+\d{4})\s+-\s+nå",
        r"\1 – nå",
        out,
        flags=re.IGNORECASE,
    )
    return out


def translate_experience_roles_no(text: str) -> str:
    for english, norwegian in _EXPERIENCE_ROLE_EN_TO_NO.items():
        text = text.replace(english, norwegian)
    return text


def translate_designation_no(text: str) -> str:
    lines = text.splitlines()
    in_stilling = False
    for idx, line in enumerate(lines):
        lower = line.strip().lower()
        if lower in ("## role", "## stilling"):
            in_stilling = True
            continue
        if in_stilling:
            if lower.startswith("## "):
                break
            stripped = line.strip()
            if stripped:
                upper = stripped.upper()
                if upper in _DESIGNATION_EN_TO_NO:
                    lines[idx] = _DESIGNATION_EN_TO_NO[upper]
                elif stripped in _DESIGNATION_EN_TO_NO:
                    lines[idx] = _DESIGNATION_EN_TO_NO[stripped]
                break
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def translate_work_permit_no(text: str) -> str:
    return text.replace("Valid Norwegian work permit", "Gyldig norsk arbeidstillatelse")


def translate_hobbies_no(text: str) -> str:
    lines = text.splitlines()
    in_hobbies = False
    for idx, line in enumerate(lines):
        lower = line.strip().lower()
        if lower in ("## hobbies", "## hobbyer"):
            in_hobbies = True
            continue
        if in_hobbies:
            if lower.startswith("## "):
                break
            stripped = line.strip()
            if stripped.startswith("- "):
                hobby = stripped[2:].strip()
                translated = _HOBBY_EN_TO_NO.get(hobby)
                if translated:
                    lines[idx] = f"- {translated}"
    return "\n".join(lines) + ("\n" if text.endswith("\n") else "")


def postprocess_norwegian_cv(text: str) -> str:
    """Deterministic Norwegian CV polish after agent localization."""
    text = translate_designation_no(text)
    text = translate_experience_roles_no(text)
    text = translate_work_permit_no(text)
    text = translate_hobbies_no(text)
    text = localize_dates_no(text)
    return text


def _cover_letter_body_text(text: str) -> str:
    """Text between **Ang:**/**Re:** heading and closing salutation."""
    lines = text.splitlines()
    in_body = False
    body_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"\*\*Ang:\s", stripped, re.IGNORECASE) or re.match(
            r"\*\*Re:\s", stripped, re.IGNORECASE
        ):
            in_body = True
            continue
        if not in_body:
            continue
        lower = stripped.lower()
        if lower.startswith("med vennlig hilsen"):
            break
        body_lines.append(line)
    return "\n".join(body_lines).strip()


def count_norwegian_cover_letter_body_words(text: str) -> int:
    body = _cover_letter_body_text(text)
    return len(re.findall(r"\b[\wæøåÆØÅ-]+\b", body, flags=re.UNICODE))


def postprocess_norwegian_cover_letter(text: str) -> tuple[str, list[str]]:
    """Polish localized cover letter and return warnings (e.g. length)."""
    warnings: list[str] = []
    text = localize_dates_no(text)
    word_count = count_norwegian_cover_letter_body_words(text)
    if word_count > NORWEGIAN_COVER_LETTER_BODY_MAX_WORDS:
        warnings.append(
            f"Norwegian cover letter body is {word_count} words "
            f"(target max {NORWEGIAN_COVER_LETTER_BODY_MAX_WORDS}); consider shortening."
        )
    return text, warnings


def build_localization_prompt(
    artifact: ArtifactKind,
    source_md: str,
    *,
    track: str,
    samples: str,
) -> str:
    section_glossary = json.dumps(SECTION_LABELS_NO, ensure_ascii=False, indent=2)
    if artifact == "cv":
        voice = list(NORWEGIAN_B1_CV_VOICE)
        task = (
            "Translate the English CV markdown into polished Norwegian B1. "
            "Return ONLY the full localized markdown document as your reply text. "
            "Do not create, edit, or save any files (especially not final_cv.md). "
            "No JSON, no commentary."
        )
        extra = (
            f"Track: {track}. Use H1 '# Bransje-CV' for industry or '# Akademisk CV' for academic. "
            "Keep the same markdown structure, ### role blocks, bullet count, and section order. "
            "The caller will save your reply as final_cv_no.md."
        )
    else:
        voice = list(NORWEGIAN_B1_COVER_LETTER_VOICE)
        task = (
            "Translate and shorten the English cover letter into polished Norwegian B1. "
            "Return ONLY the full localized markdown/plain letter as your reply text. "
            "Do not create, edit, or save any files (especially not cover_letter.md). "
            "No JSON, no commentary. The caller will save your reply as cover_letter_no.md."
        )
        extra = (
            "Preserve line breaks and header block layout. Translate **Re:** to **Ang:**. "
            f"{NORWEGIAN_COVER_LETTER_LENGTH_HINT} "
            "If the English source is long, compress while keeping the same facts."
        )
        cover_constraints = [
            "Do not invent facts, tools, employers, or dates.",
            "Do not translate URLs, emails, phone numbers, or publication titles.",
            "Polished B1: plain words, correct grammar, short sentences (one idea per sentence).",
            NORWEGIAN_COVER_LETTER_LENGTH_HINT,
            "Include one honest sentence on personality and team fit (collaboration, calm working style, "
            "learning from colleagues) — no hype.",
            "Prefer patterns from style_reference_samples: Kjære rekrutteringsteam, short paragraphs, "
            "simple verbs (liker, jobber, bygger).",
        ]
    payload = {
        "instruction": task,
        "voice_rules": voice,
        "section_glossary_en_to_no": SECTION_LABELS_NO,
        "style_reference_samples": samples,
        "constraints": cover_constraints if artifact == "cover-letter" else [
            "Do not invent facts, tools, employers, or dates.",
            "Do not translate URLs, emails, phone numbers, or publication titles.",
            "Polished B1: simple words, correct grammar, short-to-medium sentences.",
        ],
        "notes": extra,
        "source_markdown": source_md,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def localize_markdown(
    source_md: str,
    *,
    artifact: ArtifactKind,
    track: str | None = None,
    provider: str = "cursor",
    model: str = "",
    metrics: PipelineMetricsCollector | None = None,
) -> str:
    resolved_track = track or detect_track(source_md)
    samples = load_writing_samples()
    prompt = build_localization_prompt(
        artifact, source_md, track=resolved_track, samples=samples
    )
    default_models = {
        "cursor": "composer-2.5",
        "anthropic": "claude-sonnet-4-20250514",
        "openai": "gpt-4o",
        "manual": "manual",
    }
    resolved_model = (model or "").strip() or default_models.get(provider, "composer-2.5")

    if provider == "manual":
        raise RuntimeError("manual provider is not supported for localization; use cursor/anthropic/openai.")

    step_started = time.monotonic()
    backend = get_provider(provider)
    result = backend.run(prompt, model=resolved_model, cwd=Path.cwd())
    localized = strip_markdown_response(result.text)
    if not localized.strip():
        raise RuntimeError("Localization returned empty markdown.")
    if metrics is not None:
        token_source = "api" if (
            result.tokens_input is not None or result.tokens_output is not None
        ) else "none"
        metrics.record_stage(
            name=f"localize_{artifact.replace('-', '_')}",
            started_mono=step_started,
            ended_mono=time.monotonic(),
            provider=result.provider or provider,
            model=result.model or resolved_model,
            kind="localization",
            tokens_input=result.tokens_input,
            tokens_output=result.tokens_output,
            tokens_source=token_source,
            agent_run_id=result.run_id,
            prompt_text=prompt,
            response_text=localized,
        )
    return localized


def localize_run(
    run_dir: Path,
    *,
    artifacts: tuple[ArtifactKind, ...] = ("cv", "cover-letter"),
    provider: str = "cursor",
    model: str = "",
    no_pdf: bool = False,
    profile_photo: Path | None = None,
    metrics: PipelineMetricsCollector | None = None,
) -> int:
    from cv_generation.run_agent_pipeline import try_export_pdf
    from cv_generation.render_cv_pdf import _looks_like_cover_letter, _render_plain_markdown_pdf

    run_dir = run_dir.expanduser().resolve()
    if not run_dir.is_dir():
        print(f"Run folder not found: {run_dir}", file=sys.stderr)
        return 1

    exit_code = 0
    for artifact in artifacts:
        src_name, out_name = SOURCE_OUTPUT[artifact]
        src_path = run_dir / src_name
        out_path = run_dir / out_name
        if not src_path.is_file():
            print(f"Skip {artifact}: {src_name} not found", file=sys.stderr)
            continue

        source_md = src_path.read_text(encoding="utf-8")
        if artifact == "cv" and looks_like_norwegian_cv(source_md):
            print(
                f"Skip {artifact}: {src_name} already looks Norwegian; "
                f"refusing to overwrite English canonical. "
                f"Move Norwegian content to {out_name} first.",
                file=sys.stderr,
            )
            exit_code = 2
            continue
        if artifact == "cover-letter" and looks_like_norwegian_cover_letter(source_md):
            # Already Norwegian in the English path — move to _no rather than re-translate.
            localized, cl_warnings = postprocess_norwegian_cover_letter(source_md)
            for warning in cl_warnings:
                print(f"  validate: {warning}", file=sys.stderr)
            if out_path.is_file():
                print(f"Skip write: {out_name} already exists; removing Norwegian from {src_name}")
            else:
                out_path.write_text(localized, encoding="utf-8")
                print(f"Wrote: {out_name} (moved from Norwegian {src_name})")
            # English cover_letter.md must stay English-canonical; drop misplaced Norwegian.
            src_path.unlink(missing_ok=True)
            src_pdf = src_path.with_suffix(".pdf")
            if src_pdf.is_file():
                src_pdf.unlink()
            if not no_pdf and out_path.is_file():
                pdf_path = out_path.with_suffix(".pdf")
                pdf_body = out_path.read_text(encoding="utf-8")
                _render_plain_markdown_pdf(
                    out_path,
                    pdf_path,
                    normalize_upper_names=_looks_like_cover_letter(out_path, pdf_body),
                )
                if pdf_path.is_file():
                    print(f"Wrote: {pdf_path.name}")
            continue

        print(f"Localizing {src_name} -> {out_name} ...")
        source_backup = source_md
        try:
            localized = localize_markdown(
                source_md,
                artifact=artifact,
                provider=provider,
                model=model,
                metrics=metrics,
            )
        except RuntimeError as err:
            print(f"Localization failed for {src_name}: {err}", file=sys.stderr)
            exit_code = 2
            continue

        # Cursor local agents can write files; never let them replace English sources.
        if src_path.is_file() and src_path.read_text(encoding="utf-8") != source_backup:
            src_path.write_text(source_backup, encoding="utf-8")
            print(
                f"Restored {src_name}: agent modified the English source during localization.",
                file=sys.stderr,
            )

        if artifact == "cv":
            localized = postprocess_norwegian_cv(localized)
            warnings = validate_localized_cv(source_backup, localized)
            for warning in warnings:
                print(f"  validate: {warning}", file=sys.stderr)
            if looks_like_norwegian_cv(src_path.read_text(encoding="utf-8")):
                src_path.write_text(source_backup, encoding="utf-8")
                print(f"Restored English {src_name} after localization.", file=sys.stderr)
        else:
            localized, cl_warnings = postprocess_norwegian_cover_letter(localized)
            for warning in cl_warnings:
                print(f"  validate: {warning}", file=sys.stderr)

        out_path.write_text(localized, encoding="utf-8")
        print(f"Wrote: {out_name}")

        if no_pdf:
            continue

        pdf_path = out_path.with_suffix(".pdf")
        if artifact == "cv":
            ok, msg = try_export_pdf(
                out_path,
                pdf_path,
                profile_photo=profile_photo,
                document_language="no",
            )
            if ok:
                print(f"Wrote: {pdf_path.name}")
            else:
                print(msg, file=sys.stderr)
                exit_code = 3
        else:
            _render_plain_markdown_pdf(
                out_path,
                pdf_path,
                normalize_upper_names=_looks_like_cover_letter(out_path, localized),
            )
            if pdf_path.is_file():
                print(f"Wrote: {pdf_path.name}")
            else:
                print(f"Cover letter PDF failed: {pdf_path}", file=sys.stderr)
                exit_code = 3

    return exit_code


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Localize CV/cover letter to Norwegian B1")
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument(
        "--artifact",
        choices=("cv", "cover-letter", "both"),
        default="both",
        help="Which artifact to localize (default: both)",
    )
    p.add_argument("--provider", default="cursor", help="Agent backend (cursor, anthropic, openai)")
    p.add_argument("--model", default="", help="Model id (provider-specific)")
    p.add_argument("--no-pdf", action="store_true", help="Skip PDF export")
    p.add_argument("--profile-photo", type=Path, default=None)
    return p.parse_args()


def main() -> int:
    from repo_paths import load_repo_dotenv

    load_repo_dotenv()
    args = parse_args()
    if args.artifact == "both":
        artifacts: tuple[ArtifactKind, ...] = ("cv", "cover-letter")
    elif args.artifact == "cv":
        artifacts = ("cv",)
    else:
        artifacts = ("cover-letter",)
    return localize_run(
        args.run_dir,
        artifacts=artifacts,
        provider=args.provider.strip().lower(),
        model=args.model,
        no_pdf=args.no_pdf,
        profile_photo=args.profile_photo,
    )


if __name__ == "__main__":
    raise SystemExit(main())
