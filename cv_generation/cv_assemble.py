#!/usr/bin/env python3
"""
Deterministic CV assembly: merge bullet_tailor output into the source template
without dropping roles, sections, or bullets unless explicitly allowed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from cv_generation.cv_pdf_renderer import CvContent, EducationItem, ExperienceItem, parse_cv_markdown
from cv_generation.cv_style import (
    SKILLS_SIDEBAR_MAX,
    normalize_profile_paragraphs,
    normalize_summary_bullets,
)
from cv_generation.cv_tracks import cv_track_from_title


def designation_from_job_role(role_title: str) -> str:
    """Headline under the name on the CV/PDF (e.g. ML/AI Engineer -> ML/AI ENGINEER)."""
    text = re.sub(r"\s+", " ", (role_title or "").strip())
    return text.upper() if text else ""


def resolve_job_role_title(run_dir: Path) -> str:
    """Role from JD parser output, then job_posting.txt, then task job_meta."""
    jd_path = run_dir / "01_jd_parser_output.json"
    if jd_path.is_file():
        try:
            role = json.loads(jd_path.read_text(encoding="utf-8")).get("role_title")
            if isinstance(role, str) and role.strip():
                return role.strip()
        except (json.JSONDecodeError, OSError):
            pass

    posting_path = run_dir / "job_posting.txt"
    if posting_path.is_file():
        try:
            for line in posting_path.read_text(encoding="utf-8").splitlines():
                if line.lower().startswith("role:"):
                    role = line.split(":", 1)[1].strip()
                    if role:
                        return role
        except OSError:
            pass

    for task_name in ("01_jd_parser_task.json", "06_assembler_task.json"):
        task_path = run_dir / task_name
        if not task_path.is_file():
            continue
        try:
            ctx = json.loads(task_path.read_text(encoding="utf-8")).get("context") or {}
            job_meta = ctx.get("job_meta") if isinstance(ctx, dict) else None
            if isinstance(job_meta, dict):
                role = job_meta.get("role_title")
                if isinstance(role, str) and role.strip():
                    return role.strip()
        except (json.JSONDecodeError, OSError):
            pass
    return ""


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _degree_kind(degree: str) -> str | None:
    d = _norm(degree)
    if "ph.d" in d or "phd" in d or "doctor" in d:
        return "phd"
    if "m.sc" in d or "msc" in d or "master" in d:
        return "msc"
    if "b.eng" in d or "bachelor" in d:
        return "beng"
    return None


def _education_institutions_by_degree(education: list[EducationItem]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in education:
        kind = _degree_kind(item.degree)
        institute = (item.institute or "").strip()
        if kind and institute:
            mapping[kind] = institute
    return mapping


def _phd_experience_employer(experience: list[ExperienceItem]) -> str | None:
    for item in experience:
        role = _norm(item.role)
        if "postdoc" in role or "post-doc" in role:
            continue
        if re.search(r"\bph\.?\s*d\.?\b", role) or "phd student" in role:
            company = (item.company or "").strip()
            if company:
                return company
    return None


def _teaching_institution_suffix(item: str) -> str | None:
    text = (item or "").strip()
    if " — " not in text:
        return None
    suffix = text.rsplit(" — ", 1)[1].strip()
    if not suffix:
        return None
    if "(" in suffix:
        suffix = suffix.split("(", 1)[0].strip()
    return suffix or None


def _collect_institution_names(cv: CvContent) -> set[str]:
    names: set[str] = set()
    for item in cv.education:
        if item.institute.strip():
            names.add(item.institute.strip())
    for item in cv.experience:
        if item.company.strip():
            names.add(item.company.strip())
    for item in cv.teaching:
        inst = _teaching_institution_suffix(item)
        if inst:
            names.add(inst)
    return names


def validate_institution_consistency(
    source_markdown: str,
    *,
    assembled_markdown: str | None = None,
    bullet_tailor_output: dict[str, Any] | None = None,
) -> list[str]:
    """
    Cross-check degree institutions, experience employers, and teaching hosts.

    Returns human-readable warnings when institutions are swapped, relabeled, or
    inconsistent between Education and the Ph.D. experience role.
    """
    warnings: list[str] = []
    source = parse_cv_markdown(source_markdown)
    edu_by_degree = _education_institutions_by_degree(source.education)
    phd_employer = _phd_experience_employer(source.experience)

    phd_institute = edu_by_degree.get("phd")
    if phd_institute and phd_employer and _norm(phd_institute) != _norm(phd_employer):
        warnings.append(
            "Source CV mismatch: Ph.D. Education institution "
            f"('{phd_institute}') differs from Ph.D. experience employer "
            f"('{phd_employer}')."
        )

    if bullet_tailor_output:
        for item in extract_experience_roles(bullet_tailor_output):
            company = str(item.get("company") or "").strip()
            role = str(item.get("role") or "").strip()
            if not company or not role:
                continue
            duration = str(item.get("duration") or "")
            key = experience_role_key(role, company, duration)
            source_match = next(
                (
                    exp
                    for exp in source.experience
                    if experience_role_key(exp.role, exp.company, exp.duration) == key
                ),
                None,
            )
            if source_match is None:
                source_match = next(
                    (
                        exp
                        for exp in source.experience
                        if _norm(exp.role) == _norm(role)
                        and (
                            not duration.strip()
                            or _norm(exp.duration) == _norm(duration)
                        )
                    ),
                    None,
                )
            if source_match and _norm(source_match.company) != _norm(company):
                warnings.append(
                    f"Bullet tailor relabeled employer for '{role}': "
                    f"source '{source_match.company}' vs tailored '{company}'."
                )

    if assembled_markdown:
        assembled = parse_cv_markdown(assembled_markdown)
        for kind, institute in _education_institutions_by_degree(assembled.education).items():
            source_institute = edu_by_degree.get(kind)
            if source_institute and _norm(source_institute) != _norm(institute):
                warnings.append(
                    f"Assembled CV changed {kind.upper()} institution: "
                    f"source '{source_institute}' vs assembled '{institute}'."
                )

        for src, out in zip(source.experience, assembled.experience):
            if _norm(src.company) != _norm(out.company):
                warnings.append(
                    f"Assembled CV changed experience employer for '{src.role}': "
                    f"source '{src.company}' vs assembled '{out.company}'."
                )

        for src_item, out_item in zip(source.teaching, assembled.teaching):
            src_inst = _teaching_institution_suffix(src_item)
            out_inst = _teaching_institution_suffix(out_item)
            if src_inst and out_inst and _norm(src_inst) != _norm(out_inst):
                warnings.append(
                    "Assembled CV changed teaching institution: "
                    f"source '{src_inst}' vs assembled '{out_inst}'."
                )
            elif _norm(src_item) != _norm(out_item) and (src_inst or out_inst):
                warnings.append(
                    "Assembled CV changed teaching entry: "
                    f"source '{src_item}' vs assembled '{out_item}'."
                )

    return warnings


def _skill_relevance_score(skill: str, priority_terms: list[str]) -> int:
    s = _norm(skill)
    score = 0
    for term in priority_terms:
        t = _norm(term)
        if not t:
            continue
        if t == s:
            score += 10
        elif t in s or s in t:
            score += 5
        else:
            for word in t.split():
                if len(word) > 2 and word in s:
                    score += 1
    return score


def select_tailored_skills(
    source_skills: list[str],
    priority_terms: list[str] | None = None,
    *,
    max_count: int = SKILLS_SIDEBAR_MAX,
) -> list[str]:
    """Keep at most max_count skills, preferring terms that match ranked JD keywords."""
    cleaned = [s.strip() for s in source_skills if isinstance(s, str) and s.strip()]
    if not cleaned:
        return []
    terms = [str(t).strip() for t in (priority_terms or []) if str(t).strip()]
    if len(cleaned) <= max_count and not terms:
        return cleaned[:max_count]
    ranked = sorted(
        enumerate(cleaned),
        key=lambda pair: (-_skill_relevance_score(pair[1], terms), pair[0]),
    )
    return [skill for _, skill in ranked[:max_count]]


def experience_role_key(role: str, company: str, duration: str = "") -> str:
    parts = [_norm(role), _norm(company)]
    if duration.strip():
        parts.append(_norm(duration))
    return "|".join(p for p in parts if p)


def _match_tailored_role(
    source: ExperienceItem,
    tailored_roles: list[dict[str, Any]],
    used: set[int],
) -> dict[str, Any] | None:
    key = experience_role_key(source.role, source.company, source.duration)
    for idx, item in enumerate(tailored_roles):
        if idx in used:
            continue
        item_key = str(item.get("role_key") or "").strip()
        if item_key and item_key == key:
            used.add(idx)
            return item
        if experience_role_key(
            str(item.get("role") or ""),
            str(item.get("company") or ""),
            str(item.get("duration") or ""),
        ) == key:
            used.add(idx)
            return item
    for idx, item in enumerate(tailored_roles):
        if idx in used:
            continue
        if _norm(str(item.get("role") or "")) == _norm(source.role) and _norm(
            str(item.get("company") or "")
        ) == _norm(source.company):
            used.add(idx)
            return item
    return None


def _coerce_bullets(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(b).strip() for b in value if isinstance(b, str) and str(b).strip()]


def _parse_legacy_tailored_bullets(flat: list[str]) -> list[dict[str, Any]]:
    """Best-effort parse 'Company — Role: bullet' lines from legacy bullet_tailor output."""
    roles: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}
    for line in flat:
        if not isinstance(line, str) or not line.strip():
            continue
        text = line.strip()
        if " — " in text and ": " in text:
            head, bullet = text.split(": ", 1)
            company_role = head.split(" — ", 1)
            if len(company_role) == 2:
                company, role = company_role
                key = experience_role_key(role, company)
                entry = by_key.setdefault(
                    key,
                    {"role": role.strip(), "company": company.strip(), "duration": "", "bullets": []},
                )
                entry["bullets"].append(bullet.strip())
                continue
        roles.append({"role": "", "company": "", "duration": "", "bullets": [text]})
    return list(by_key.values()) + roles


def extract_experience_roles(bullet_tailor_output: dict[str, Any]) -> list[dict[str, Any]]:
    roles = bullet_tailor_output.get("experience_roles")
    if isinstance(roles, list) and roles:
        return [r for r in roles if isinstance(r, dict)]
    legacy = bullet_tailor_output.get("tailored_bullets")
    if isinstance(legacy, list) and legacy:
        return _parse_legacy_tailored_bullets(legacy)
    return []


def merge_experience_bullets(
    source_roles: list[ExperienceItem],
    tailored_roles: list[dict[str, Any]],
    *,
    allow_fewer_bullets: bool = False,
) -> tuple[list[ExperienceItem], list[str]]:
    """
    Merge tailored bullets into source roles (same order as source).
    Never drop a role. By default, never drop bullets — pad from source when tailor returns fewer.
    """
    warnings: list[str] = []
    used: set[int] = set()
    merged: list[ExperienceItem] = []

    for source in source_roles:
        tailored = _match_tailored_role(source, tailored_roles, used)
        if tailored is None:
            merged.append(source)
            warnings.append(
                f"No tailored match for role '{source.role}' at '{source.company}'; kept source bullets."
            )
            continue

        new_bullets = _coerce_bullets(tailored.get("bullets"))
        if not new_bullets:
            merged.append(source)
            warnings.append(
                f"Empty tailored bullets for '{source.role}' at '{source.company}'; kept source bullets."
            )
            continue

        if allow_fewer_bullets or len(new_bullets) >= len(source.bullets):
            final_bullets = new_bullets
        else:
            final_bullets = new_bullets + source.bullets[len(new_bullets) :]
            warnings.append(
                f"Restored {len(source.bullets) - len(new_bullets)} bullet(s) for "
                f"'{source.role}' at '{source.company}' (tailor returned fewer than source)."
            )

        merged.append(
            ExperienceItem(
                role=source.role,
                company=source.company,
                duration=source.duration,
                bullets=final_bullets,
            )
        )

    if len(merged) < len(source_roles):
        warnings.append("Internal error: merged experience shorter than source.")
    return merged, warnings


def _apply_profile_length_limits(cv: CvContent, warnings: list[str]) -> None:
    """Trim Profile / Summary so PDF main column stays within a practical page budget."""
    if cv.summary_bullets:
        limited, profile_warnings = normalize_summary_bullets(cv.summary_bullets)
        cv.summary_bullets = limited
        warnings.extend(profile_warnings)
        return

    if cv.profile_paragraphs:
        limited, profile_warnings = normalize_profile_paragraphs(cv.profile_paragraphs)
        cv.profile_paragraphs = limited
        cv.profile = "\n\n".join(limited)
        warnings.extend(profile_warnings)
        return

    if cv.profile.strip():
        limited, profile_warnings = normalize_profile_paragraphs([cv.profile.strip()])
        cv.profile_paragraphs = limited
        cv.profile = "\n\n".join(limited)
        warnings.extend(profile_warnings)


def apply_bullet_tailor(
    source_markdown: str,
    bullet_tailor_output: dict[str, Any],
    *,
    allow_fewer_bullets: bool = False,
    apply_tailored_profile: bool = False,
    apply_tailored_experience: bool = False,
) -> tuple[CvContent, list[str]]:
    """
    Merge bullet_tailor output into the source CV.

    By default the source template (cv/industry.md) keeps profile, skills, and
    experience bullets. Set apply_tailored_profile / apply_tailored_experience to
    True to apply agent rewrites from a bullet_tailor run.
    """
    source = parse_cv_markdown(source_markdown)
    warnings: list[str] = []

    if apply_tailored_profile:
        summary = bullet_tailor_output.get("tailored_summary")
        if isinstance(summary, str) and summary.strip():
            text = summary.strip()
            is_academic = cv_track_from_title(source.title) == "academic"
            bullet_lines = [
                ln[2:].strip()
                for ln in text.splitlines()
                if ln.strip().startswith("- ")
            ]
            if is_academic and bullet_lines:
                source.summary_bullets = bullet_lines
                source.profile = ""
                source.profile_paragraphs = []
            else:
                source.profile = text
                paras = [p.strip() for p in text.split("\n\n") if p.strip()]
                source.profile_paragraphs = paras if len(paras) > 1 else [text]

    if apply_tailored_experience:
        tailored_roles = extract_experience_roles(bullet_tailor_output)
        source.experience, warnings = merge_experience_bullets(
            source.experience,
            tailored_roles,
            allow_fewer_bullets=allow_fewer_bullets,
        )
    _apply_profile_length_limits(source, warnings)
    return source, warnings


def render_cv_markdown(cv: CvContent) -> str:
    track = cv_track_from_title(cv.title)
    is_academic = track == "academic"
    lines: list[str] = [f"# {cv.title or 'Industry CV'}", ""]

    if cv.full_name:
        lines.extend(["## Name", "", cv.full_name, ""])
    if cv.role_title and not is_academic:
        lines.extend(["## Role", "", cv.role_title, ""])

    if is_academic and cv.summary_bullets:
        lines.append("## Summary")
        lines.append("")
        for bullet in cv.summary_bullets:
            lines.append(f"- {bullet}")
        lines.append("")
    elif cv.profile or cv.profile_paragraphs:
        lines.append("## Profile")
        lines.append("")
        paras = cv.profile_paragraphs or [p for p in cv.profile.split("\n\n") if p.strip()]
        if not paras and cv.profile.strip():
            paras = [cv.profile.strip()]
        for para in paras:
            lines.append(para.strip())
            lines.append("")

    if cv.date_of_birth:
        lines.extend(["## Date of birth", "", cv.date_of_birth, ""])

    if cv.contact:
        lines.append("## Contact")
        lines.append("")
        for item in cv.contact:
            lines.append(f"- {item}")
        lines.append("")

    if cv.skills:
        lines.append("## Skills")
        lines.append("")
        lines.append("; ".join(cv.skills))
        lines.append("")

    if cv.languages and not is_academic:
        lines.append("## Languages")
        lines.append("")
        for lang in cv.languages:
            lines.append(f"- {lang}")
        lines.append("")

    if is_academic and cv.education:
        lines.append("## Education")
        lines.append("")
        for edu in cv.education:
            if edu.degree and edu.institute and not edu.field and not edu.thesis:
                lines.append(
                    f"- {edu.degree}, {edu.institute} ({edu.duration})."
                    if edu.duration
                    else f"- {edu.degree}, {edu.institute}."
                )
                continue
            lines.append(f"### {edu.degree}")
            if edu.institute:
                lines.append(edu.institute)
            if edu.duration:
                lines.append(edu.duration)
            if edu.field:
                lines.append(edu.field)
            if edu.thesis:
                lines.append(f"Thesis: {edu.thesis}")
            lines.append("")

    if is_academic and cv.research_publications:
        lines.append("## Research and publications")
        lines.append("")
        for line in cv.research_publications:
            if line.startswith("- "):
                lines.append(line)
            else:
                lines.append(line)
        lines.append("")

    if is_academic and cv.teaching:
        lines.append("## Teaching and supervision")
        lines.append("")
        for item in cv.teaching:
            lines.append(f"- {item}")
        lines.append("")

    exp_heading = "## Research experience" if is_academic else "## Experience"
    if cv.experience:
        lines.append(exp_heading)
        lines.append("")
        for item in cv.experience:
            lines.append(f"### {item.company or item.role}")
            if item.role and item.company:
                lines.append(item.role)
            if item.duration:
                lines.append(item.duration)
            lines.append("")
            for bullet in item.bullets:
                lines.append(f"- {bullet}")
            lines.append("")

    if not is_academic and cv.education:
        lines.append("## Education")
        lines.append("")
        for edu in cv.education:
            if edu.degree and edu.institute and not edu.field and not edu.thesis:
                lines.append(
                    f"- {edu.degree}, {edu.institute} ({edu.duration})."
                    if edu.duration
                    else f"- {edu.degree}, {edu.institute}."
                )
                continue
            lines.append(f"### {edu.degree}")
            if edu.institute:
                lines.append(edu.institute)
            if edu.duration:
                lines.append(edu.duration)
            if edu.field:
                lines.append(edu.field)
            if edu.thesis:
                lines.append(f"Thesis: {edu.thesis}")
            lines.append("")

    if cv.publications:
        lines.append("## Selected Publications")
        lines.append("")
        for pub in cv.publications:
            lines.append(f"- {pub}")
            lines.append("")

    if is_academic and cv.languages:
        lines.append("## Languages")
        lines.append("")
        for lang in cv.languages:
            lines.append(f"- {lang}")
        lines.append("")

    if cv.hobbies:
        lines.append("## Hobbies")
        lines.append("")
        for hobby in cv.hobbies:
            lines.append(f"- {hobby}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def normalize_bullet_tailor_output(
    source_markdown: str,
    bullet_tailor_output: dict[str, Any],
    *,
    allow_fewer_bullets: bool = False,
    apply_tailored_profile: bool = False,
    apply_tailored_experience: bool = False,
) -> dict[str, Any]:
    """Enforce preservation rules and return canonical experience_roles for persistence."""
    cv, warnings = apply_bullet_tailor(
        source_markdown,
        bullet_tailor_output,
        allow_fewer_bullets=allow_fewer_bullets,
        apply_tailored_profile=apply_tailored_profile,
        apply_tailored_experience=apply_tailored_experience,
    )
    experience_roles = [
        {
            "role_key": experience_role_key(item.role, item.company, item.duration),
            "role": item.role,
            "company": item.company,
            "duration": item.duration,
            "bullets": list(item.bullets),
        }
        for item in cv.experience
    ]
    removed = bullet_tailor_output.get("removed_claims")
    if cv.summary_bullets:
        tailored_summary = "\n".join(f"- {bullet}" for bullet in cv.summary_bullets)
    else:
        tailored_summary = cv.profile
    return {
        "tailored_summary": tailored_summary,
        "experience_roles": experience_roles,
        "removed_claims": removed if isinstance(removed, list) else [],
        "_merge_warnings": warnings,
    }


def assemble_final_cv_markdown(
    source_markdown: str,
    bullet_tailor_output: dict[str, Any],
    *,
    allow_fewer_bullets: bool = False,
    apply_tailored_profile: bool = False,
    apply_tailored_experience: bool = False,
    job_role_title: str | None = None,
    priority_terms: list[str] | None = None,
) -> tuple[str, list[str]]:
    cv, warnings = apply_bullet_tailor(
        source_markdown,
        bullet_tailor_output,
        allow_fewer_bullets=allow_fewer_bullets,
        apply_tailored_profile=apply_tailored_profile,
        apply_tailored_experience=apply_tailored_experience,
    )
    if cv.skills:
        trimmed = select_tailored_skills(cv.skills, priority_terms)
        if len(trimmed) < len(cv.skills):
            warnings.append(
                f"Trimmed Skills from {len(cv.skills)} to {len(trimmed)} role-relevant terms."
            )
        cv.skills = trimmed
    if job_role_title and job_role_title.strip() and cv_track_from_title(cv.title) != "academic":
        cv.role_title = designation_from_job_role(job_role_title)
    rendered = render_cv_markdown(cv)
    warnings.extend(
        validate_institution_consistency(
            source_markdown,
            assembled_markdown=rendered,
            bullet_tailor_output=bullet_tailor_output if apply_tailored_experience else None,
        )
    )
    return rendered, warnings


def build_assembler_output(
    cv_markdown: str,
    *,
    track: str,
    company: str | None,
    role_title: str,
    company_slug: str = "",
    validation_warnings: list[str] | None = None,
) -> dict[str, Any]:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", (company_slug or company or "company").strip().lower()).strip("_")
    role_slug = re.sub(r"[^a-zA-Z0-9]+", "_", role_title.strip().lower()).strip("_")
    artifact = f"cv_{slug}_{role_slug}_{track}.md" if slug else f"cv_{role_slug}_{track}.md"
    return {
        "cv_markdown": cv_markdown.rstrip() + "\n",
        "artifact_name": artifact,
        "metadata": {
            "track": track,
            "company": company,
            "role_title": role_title,
        },
        "validation_warnings": list(validation_warnings or []),
    }
