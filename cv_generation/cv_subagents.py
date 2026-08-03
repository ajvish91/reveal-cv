#!/usr/bin/env python3
"""
Subagent definitions for CV tailoring automation.

Each agent has:
- clear purpose
- required input keys
- expected output schema (JSON-like)
"""
from __future__ import annotations

from dataclasses import dataclass

from cv_generation.cv_style import (
    ATS_EMPHASIS_HINT,
    BULLET_CHRONOLOGY_HINT,
    BULLET_TAILOR_EMPHASIS_HINT,
    INSTITUTION_INTEGRITY_HINT,
    PROFILE_LENGTH_HINT,
    SKILLS_LINE_HINT,
    SUMMARY_LENGTH_HINT,
)


@dataclass(frozen=True)
class SubagentSpec:
    name: str
    purpose: str
    required_inputs: tuple[str, ...]
    output_schema: dict
    prompt_template: str


SUBAGENT_SPECS: tuple[SubagentSpec, ...] = (
    SubagentSpec(
        name="jd_parser",
        purpose="Extract role details and must-have requirements from raw job text.",
        required_inputs=("job_text",),
        output_schema={
            "role_title": "string",
            "company": "string|null",
            "location": "string|null",
            "must_have_skills": "string[]",
            "nice_to_have_skills": "string[]",
            "domain_keywords": "string[]",
            "seniority": "junior|mid|senior|staff|principal|unknown",
        },
        prompt_template=(
            "You are JD Parser. Read the job posting and return strict JSON only. "
            "Do not invent facts. Keep skills lowercase, deduplicated."
        ),
    ),
    SubagentSpec(
        name="keyword_ranker",
        purpose="Rank JD keywords by impact for ATS relevance.",
        required_inputs=("jd_parser_output", "candidate_keywords", "candidate_skills"),
        output_schema={
            "priority_keywords": [{"term": "string", "weight": "number", "source": "must|nice|domain"}],
            "missing_keywords": "string[]",
            "overlap_score": "number",
        },
        prompt_template=(
            "You are Keyword Ranker. Rank terms by hiring impact and ATS value. "
            "Favor must-have terms. Return strict JSON."
        ),
    ),
    SubagentSpec(
        name="track_selector",
        purpose="Choose best CV track (industry or academic).",
        required_inputs=("jd_parser_output", "industry_cv_text", "academic_cv_text"),
        output_schema={
            "selected_track": "industry|academic",
            "confidence": "number",
            "rationale": "string",
        },
        prompt_template=(
            "You are Track Selector. Choose either industry or academic CV. "
            "Optimize for role fit and transferability."
        ),
    ),
    SubagentSpec(
        name="bullet_tailor",
        purpose="Rewrite profile and experience bullets per role for the target job, without fabrication.",
        required_inputs=("selected_cv_text", "priority_keywords", "role_title"),
        output_schema={
            "tailored_summary": "string",
            "experience_roles": [
                {
                    "role_key": "string",
                    "role": "string",
                    "company": "string",
                    "duration": "string",
                    "bullets": "string[]",
                }
            ],
            "removed_claims": "string[]",
        },
        prompt_template=(
            "You are Bullet Tailor. Rewrite the Profile (as tailored_summary) and experience bullets "
            "for relevance to the job. Return strict JSON with experience_roles: one object per "
            "experience entry in the source CV, in the same reverse-chronological order. Each object "
            "must include role, company, duration exactly as in the source, plus role_key "
            "(role|company|duration, lowercase, pipe-separated) and bullets. "
            "You MUST include every experience role from the source; do not omit roles. "
            "You MUST return at least as many bullets per role as the source (you may rephrase, "
            "reorder for impact, or merge wording, but do not delete bullets). "
            "Do not edit Education, Publications, Hobbies, Contact, Skills, Languages, or Date of birth. "
            f"{SKILLS_LINE_HINT} "
            "removed_claims must be empty unless you are flagging phrasing you intentionally avoided "
            "(not dropped content). Never invent metrics, titles, dates, or employers. "
            f"{BULLET_CHRONOLOGY_HINT} "
            f"{INSTITUTION_INTEGRITY_HINT} "
            f"{BULLET_TAILOR_EMPHASIS_HINT} {PROFILE_LENGTH_HINT} {SUMMARY_LENGTH_HINT} "
            "Put ATS keywords in experience bullets, not a keyword-dense Profile or Summary."
        ),
    ),
    SubagentSpec(
        name="ats_checker",
        purpose="Check formatting and keyword coverage against ATS constraints.",
        required_inputs=("tailored_cv_markdown", "priority_keywords"),
        output_schema={
            "ats_score": "number",
            "found_keywords": "string[]",
            "missing_keywords": "string[]",
            "format_warnings": "string[]",
            "pass": "boolean",
        },
        prompt_template=(
            "You are ATS Checker. Check parseability and relevance. "
            "Flag tables, columns, icons, emoji, images, or dense formatting. "
            f"{ATS_EMPHASIS_HINT}"
        ),
    ),
    SubagentSpec(
        name="assembler",
        purpose="Validate assembled CV metadata (final markdown is built programmatically).",
        required_inputs=("tailored_cv_markdown", "selected_track", "job_meta"),
        output_schema={
            "artifact_name": "string",
            "metadata": {"track": "string", "company": "string|null", "role_title": "string"},
            "validation_warnings": "string[]",
        },
        prompt_template=(
            "You are Assembler. The final CV markdown is already assembled in prior_outputs. "
            "Return artifact_name (slug from company and role) and metadata only. "
            "List any validation_warnings if sections are missing or experience order looks wrong. "
            "Do not rewrite or shorten the CV."
        ),
    ),
)


def as_markdown() -> str:
    lines: list[str] = ["# CV Tailoring Subagents", ""]
    for spec in SUBAGENT_SPECS:
        lines.append(f"## {spec.name}")
        lines.append(f"- Purpose: {spec.purpose}")
        lines.append(f"- Required inputs: {', '.join(spec.required_inputs)}")
        lines.append(f"- Prompt: {spec.prompt_template}")
        lines.append("- Output schema:")
        for key, val in spec.output_schema.items():
            lines.append(f"  - {key}: {val}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"

