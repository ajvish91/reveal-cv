"""Run folder naming: ``{timestamp}_{CompanySlug}_{role-slug}``."""
from __future__ import annotations

import json
import re
from pathlib import Path

TIMESTAMP_PREFIX_RE = re.compile(r"^(\d{8}T\d{6}Z)(?:_(.+))?$")
FALLBACK_COMPANY = "Unknown"


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", (text or "").strip().lower()).strip("-")
    return value or "untitled-role"


def company_slug(text: str) -> str:
    """Folder-safe company token, preserving casing (e.g. Storebrand)."""
    return re.sub(r"[^a-zA-Z0-9]+", "", (text or "").strip())


def run_folder_name(timestamp: str, role: str, company: str | None = None) -> str:
    """e.g. ``20260601T122139Z_Storebrand_senior-ai-platform-engineer``."""
    parts = [timestamp]
    co = company_slug(company) if company else ""
    if co:
        parts.append(co)
    parts.append(slugify(role))
    return "_".join(parts)


def parse_run_folder_basename(name: str) -> tuple[str, str | None, str | None]:
    """
    Parse ``{timestamp}_{CompanySlug}_{role-slug}`` or legacy ``{timestamp}_{role-slug}``.

    Returns ``(timestamp, company_slug_or_none, role_slug_or_none)``.
    Non-timestamp names return ``(name, None, None)``.
    """
    stripped = (name or "").strip()
    match = TIMESTAMP_PREFIX_RE.match(stripped)
    if not match:
        return stripped, None, None
    timestamp = match.group(1)
    rest = match.group(2)
    if not rest:
        return timestamp, None, None
    if "_" in rest:
        company, role = rest.split("_", 1)
        return timestamp, company or None, role or None
    return timestamp, None, rest


def folder_includes_company(name: str) -> bool:
    """True when the basename has a company segment between timestamp and role."""
    _, company, _ = parse_run_folder_basename(name)
    return bool(company)


def parse_company_from_job_posting(text: str) -> str | None:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("company:"):
            value = stripped.split(":", 1)[1].strip()
            return value or None
    return None


def parse_role_from_job_posting(text: str) -> str | None:
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("role:"):
            value = stripped.split(":", 1)[1].strip()
            return value or None
    return None


def _load_json_object(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def read_run_company(run_dir: Path) -> str | None:
    """Best-effort company from parser output, tasks, or job_posting.txt."""
    for path in (
        run_dir / "01_jd_parser_output.json",
        run_dir / "06_assembler_output.json",
    ):
        data = _load_json_object(path)
        company = data.get("company")
        if isinstance(company, str) and company.strip():
            return company.strip()
        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            company = metadata.get("company")
            if isinstance(company, str) and company.strip():
                return company.strip()

    task = _load_json_object(run_dir / "01_jd_parser_task.json")
    context = task.get("context")
    if isinstance(context, dict):
        job_meta = context.get("job_meta")
        if isinstance(job_meta, dict):
            company = job_meta.get("company")
            if isinstance(company, str) and company.strip():
                return company.strip()

    posting = run_dir / "job_posting.txt"
    if posting.is_file():
        return parse_company_from_job_posting(posting.read_text(encoding="utf-8"))

    return None


def read_run_role(run_dir: Path) -> str | None:
    for path in (
        run_dir / "01_jd_parser_output.json",
        run_dir / "06_assembler_output.json",
    ):
        data = _load_json_object(path)
        role = data.get("role_title")
        if isinstance(role, str) and role.strip():
            return role.strip()
        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            role = metadata.get("role_title")
            if isinstance(role, str) and role.strip():
                return role.strip()

    task = _load_json_object(run_dir / "01_jd_parser_task.json")
    context = task.get("context")
    if isinstance(context, dict):
        job_meta = context.get("job_meta")
        if isinstance(job_meta, dict):
            role = job_meta.get("role_title")
            if isinstance(role, str) and role.strip():
                return role.strip()

    posting = run_dir / "job_posting.txt"
    if posting.is_file():
        return parse_role_from_job_posting(posting.read_text(encoding="utf-8"))

    return None


def resolve_company_for_folder(*, company_arg: str | None, job_text: str) -> str:
    """Company for new run folders; never empty."""
    for candidate in (
        (company_arg or "").strip(),
        parse_company_from_job_posting(job_text) or "",
    ):
        if candidate:
            return candidate
    return FALLBACK_COMPANY


def enrich_run_folder_name(source_run_id: str, run_dir: Path) -> str:
    """
    Output folder basename with company when the repo run folder omitted it.

    Existing ``{timestamp}_{Company}_{role}`` names are preserved.
    Legacy ``{timestamp}_{role}`` names become ``{timestamp}_{Company}_{role}``
    when company metadata is available in the run folder.
    """
    timestamp, folder_company, role_slug = parse_run_folder_basename(source_run_id)
    if folder_company:
        return source_run_id

    company = read_run_company(run_dir)
    if not company:
        return source_run_id

    role = role_slug or slugify(read_run_role(run_dir) or "untitled-role")
    return run_folder_name(timestamp, role, company)


def find_repo_run_by_timestamp(runs_root: Path, name: str) -> Path | None:
    """Find the single cv_runs folder sharing a UTC timestamp prefix."""
    timestamp, _, _ = parse_run_folder_basename(name)
    if not TIMESTAMP_PREFIX_RE.match(timestamp):
        return None
    matches = sorted(
        path
        for path in runs_root.glob(f"{timestamp}_*")
        if path.is_dir() and (path / "final_cv.md").is_file()
    )
    if not matches:
        return None
    for path in matches:
        if path.name == name:
            return path
    if len(matches) == 1:
        return matches[0]
    return matches[0]
