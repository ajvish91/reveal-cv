#!/usr/bin/env python3
"""
Private CV workflow — deanonymize and render outside the repo.

Your real data lives only under ~/private/cv/ (mapping JSON, photo, output).
All logic stays in this repo; run from the project venv:

  .venv/bin/python -m cv_generation.private_cv setup          # once
  .venv/bin/python -m cv_generation.private_cv edit           # open mapping JSON
  .venv/bin/python -m cv_generation.private_cv sync         # run from repo OR ~/private/cv/sync
  .venv/bin/python -m cv_generation.private_cv sync-keys      # mapping merge only (alias of sync)
  .venv/bin/python -m cv_generation.private_cv apply <run>  # deanonymize CV + supplementary docs + PDF
  .venv/bin/python -m cv_generation.private_cv apply <run1> <run2> ...  # bulk deanonymize
  .venv/bin/python -m cv_generation.private_cv audit <run>  # what still needs mapping

Optional shell alias (created by setup):
  ~/private/cv/cv apply <run_id>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from repo_paths import CV_GENERATION_DIR, REPO_ROOT
from cv_generation.run_naming import enrich_run_folder_name, find_repo_run_by_timestamp

CV_PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_PRIVATE_DIR = Path.home() / "private" / "cv"
EXAMPLE_MAPPING_NAME = "cv_identity_mapping.example.json"
CONFIG_NAME = "config.env"
MAPPING_NAME = "cv_identity_mapping.json"
STUB_CV = "cv"
STUB_SYNC = "sync"
RUN_MAPPING_EN_NAME = "mapping_en_edit.json"
RUN_MAPPING_NO_NAME = "mapping_no_edit.json"


@dataclass
class PrivateConfig:
    repo_root: Path
    cv_package_dir: Path
    private_dir: Path
    mapping_file: Path
    output_dir: Path
    profile_photo: Path

    @property
    def runs_root(self) -> Path:
        return self.cv_package_dir / "cv_runs"

    @property
    def python(self) -> Path:
        venv_py = self.repo_root / ".venv" / "bin" / "python"
        return venv_py if venv_py.is_file() else Path(sys.executable)


def resolve_cv_package_dir(repo_root: Path) -> Path:
    nested = repo_root / "cv_generation"
    if (nested / "private_cv.py").is_file():
        return nested
    if (repo_root / "private_cv.py").is_file():
        return repo_root
    return CV_PACKAGE_DIR


def _expand(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def _detect_private_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return _expand(explicit)
    if os.environ.get("CV_PRIVATE_DIR", "").strip():
        return _expand(os.environ["CV_PRIVATE_DIR"])
    cwd = Path.cwd()
    if (cwd / CONFIG_NAME).is_file():
        return cwd
    return DEFAULT_PRIVATE_DIR


def example_mapping_path(cv_package_dir: Path) -> Path:
    return cv_package_dir / EXAMPLE_MAPPING_NAME


def load_config(private_dir: Path | None = None) -> PrivateConfig:
    priv = _detect_private_dir(private_dir)
    config_path = priv / CONFIG_NAME

    values: dict[str, str] = {}
    if config_path.is_file():
        for line in config_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip().strip('"').strip("'")

    repo = _expand(
        os.environ.get("CV_PROJECT_DIR")
        or values.get("CV_PROJECT_DIR")
        or REPO_ROOT
    )
    cv_pkg = resolve_cv_package_dir(repo)
    mapping = _expand(
        os.environ.get("CV_IDENTITY_MAPPING")
        or values.get("CV_IDENTITY_MAPPING")
        or priv / MAPPING_NAME
    )
    output = _expand(
        os.environ.get("CV_DEANON_OUTPUT")
        or values.get("CV_DEANON_OUTPUT")
        or priv / "deanonymized"
    )
    photo = _expand(
        os.environ.get("CV_PROFILE_PHOTO")
        or values.get("CV_PROFILE_PHOTO")
        or priv / "profile_photo.jpg"
    )
    return PrivateConfig(
        repo_root=repo,
        cv_package_dir=cv_pkg,
        private_dir=priv,
        mapping_file=mapping,
        output_dir=output,
        profile_photo=photo,
    )


def mapping_override_path(
    cfg: PrivateConfig,
    input_dir: Path,
    glob_name: str,
) -> Path | None:
    """Run-local override first, then the same filename in ~/private/cv/."""
    override_name = RUN_MAPPING_NO_NAME if glob_name.lower().endswith("_no.md") else RUN_MAPPING_EN_NAME
    run_local = input_dir / override_name
    if run_local.is_file():
        return run_local
    private_local = cfg.private_dir / override_name
    if private_local.is_file():
        return private_local
    return None


def resolve_mapping_for_artifact(
    cfg: PrivateConfig,
    input_dir: Path,
    glob_name: str,
) -> Path:
    """Use only the relevant English or Norwegian override mapping."""
    override_path = mapping_override_path(cfg, input_dir, glob_name)
    if override_path is not None:
        return override_path
    expected = RUN_MAPPING_NO_NAME if glob_name.lower().endswith("_no.md") else RUN_MAPPING_EN_NAME
    raise SystemExit(
        f"No mapping found for {glob_name}. "
        f"Expected {expected} in either {input_dir} or {cfg.private_dir}."
    )


def write_config(cfg: PrivateConfig) -> None:
    cfg.private_dir.mkdir(parents=True, exist_ok=True)
    text = f"""# Private CV paths (edit if you move folders). Real PII goes in {MAPPING_NAME} only.
CV_PROJECT_DIR="{cfg.repo_root}"
CV_PRIVATE_DIR="{cfg.private_dir}"
CV_IDENTITY_MAPPING="{cfg.mapping_file}"
CV_DEANON_OUTPUT="{cfg.output_dir}"
CV_PROFILE_PHOTO="{cfg.profile_photo}"
"""
    (cfg.private_dir / CONFIG_NAME).write_text(text, encoding="utf-8")


def load_raw_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SystemExit(f"Expected JSON object in {path}")
    return raw


def save_raw_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


@dataclass
class MappingSyncResult:
    added_keys: list[str]
    added_meta: list[str]
    refreshed_instructions: bool
    only_in_private: list[str]
    example_path: Path


def merge_mapping_from_example(cfg: PrivateConfig) -> MappingSyncResult:
    """
    Merge repo template into private mapping.

    - New keys from the example are appended with template values.
    - Existing keys in your private file are never changed (your PII is kept).
    - ``_instructions`` is refreshed from the repo (not personal data).
    - Other ``_*`` metadata keys are added only if missing.
    """
    example_path = example_mapping_path(cfg.cv_package_dir)
    if not example_path.is_file():
        raise SystemExit(f"Missing template: {example_path}")

    if not cfg.mapping_file.is_file():
        save_raw_json(cfg.mapping_file, load_raw_json(example_path))
        example = load_raw_json(example_path)
        return MappingSyncResult(
            added_keys=[k for k in example if not k.startswith("_")],
            added_meta=[k for k in example if k.startswith("_") and k != "_instructions"],
            refreshed_instructions="_instructions" in example,
            only_in_private=[],
            example_path=example_path,
        )

    example = load_raw_json(example_path)
    private = load_raw_json(cfg.mapping_file)

    added_keys: list[str] = []
    added_meta: list[str] = []
    refreshed_instructions = False

    for key, value in example.items():
        if key.startswith("_"):
            if key == "_instructions":
                if private.get(key) != value:
                    refreshed_instructions = True
                private[key] = value
            elif key not in private:
                private[key] = value
                added_meta.append(key)
            continue
        if key not in private:
            private[key] = value
            added_keys.append(key)

    save_raw_json(cfg.mapping_file, private)

    only_in_private = sorted(
        k for k in private if not k.startswith("_") and k not in example
    )
    return MappingSyncResult(
        added_keys=added_keys,
        added_meta=added_meta,
        refreshed_instructions=refreshed_instructions,
        only_in_private=only_in_private,
        example_path=example_path,
    )


def ensure_repo_package_installed(cfg: PrivateConfig) -> bool:
    """Install repo as editable package so `python -m cv_generation.private_cv` works from ~/private/cv."""
    try:
        import cv_generation  # noqa: F401
        return True
    except ModuleNotFoundError:
        pass
    proc = subprocess.run(
        [str(cfg.python), "-m", "pip", "install", "-e", str(cfg.repo_root), "-q"],
        cwd=str(cfg.repo_root),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print(
            "Warning: could not pip install -e the project; "
            "stubs set PYTHONPATH as fallback.",
            file=sys.stderr,
        )
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        return False
    return True


def _stub_pythonpath_export(repo: Path) -> str:
    return f'export PYTHONPATH="{repo}"${{PYTHONPATH:+:$PYTHONPATH}}'


def write_private_stubs(cfg: PrivateConfig) -> None:
    """Refresh ~/private/cv/cv and ~/private/cv/sync so they always call this repo."""
    repo = cfg.repo_root
    py = cfg.python
    pypath = _stub_pythonpath_export(repo)
    for name in (STUB_CV, STUB_SYNC):
        stub = cfg.private_dir / name
        if name == STUB_SYNC:
            body = f"""#!/usr/bin/env bash
# Run from ~/private/cv — syncs mapping keys from the repo template (keeps your values).
set -euo pipefail
cd "$(dirname "$0")"
export CV_PRIVATE_DIR="$(pwd)"
export CV_PROJECT_DIR="{repo}"
{pypath}
exec "{py}" -m cv_generation.private_cv sync "$@"
"""
        else:
            body = f"""#!/usr/bin/env bash
# Run from ~/private/cv — deanonymize/render via repo CLI (update-safe).
set -euo pipefail
cd "$(dirname "$0")"
export CV_PRIVATE_DIR="$(pwd)"
export CV_PROJECT_DIR="{repo}"
{pypath}
exec "{py}" -m cv_generation.private_cv "$@"
"""
        stub.write_text(body, encoding="utf-8")
        stub.chmod(0o755)


def print_mapping_sync_report(result: MappingSyncResult, mapping_file: Path) -> None:
    print(f"Template:  {result.example_path}")
    print(f"Your file: {mapping_file}\n")

    if result.added_keys:
        print(f"Added {len(result.added_keys)} new key(s) (your existing values unchanged):")
        for key in result.added_keys:
            print(f"  + {key}")
    else:
        print("Mapping keys: already up to date with the repo template.")

    if result.added_meta:
        print(f"\nAdded metadata: {', '.join(result.added_meta)}")

    if result.refreshed_instructions:
        print("\nRefreshed _instructions from repo (no PII).")

    if result.only_in_private:
        print(
            f"\n{len(result.only_in_private)} key(s) only in your private file "
            "(kept as-is; may be custom or removed from template):"
        )
        for key in result.only_in_private[:12]:
            print(f"  · {key}")
        if len(result.only_in_private) > 12:
            print(f"  ... and {len(result.only_in_private) - 12} more")


def cmd_setup(_: argparse.Namespace) -> int:
    cfg = load_config()
    cfg.private_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    write_config(cfg)

    created_mapping = False
    example_path = example_mapping_path(cfg.cv_package_dir)
    if not cfg.mapping_file.is_file():
        if not example_path.is_file():
            print(f"Missing template: {example_path}", file=sys.stderr)
            return 1
        save_raw_json(cfg.mapping_file, load_raw_json(example_path))
        created_mapping = True

    ensure_repo_package_installed(cfg)
    write_private_stubs(cfg)

    print(f"Private folder:  {cfg.private_dir}")
    print(f"Config:          {cfg.private_dir / CONFIG_NAME}")
    print(f"Mapping:         {cfg.mapping_file}" + (" (created — fill with real values)" if created_mapping else ""))
    print(f"Output:          {cfg.output_dir}")
    print(f"Shortcuts:       {cfg.private_dir / STUB_CV}")
    print(f"                 {cfg.private_dir / STUB_SYNC}")
    print()
    print("Next steps:")
    print(f"  cd {cfg.private_dir} && ./sync")
    print(f"  ./cv edit")
    print(f"  ./cv apply cv_runs/<run_id>")
    return 0


def cmd_edit(_: argparse.Namespace) -> int:
    cfg = load_config()
    if not cfg.mapping_file.is_file():
        print(f"No mapping file at {cfg.mapping_file}. Run: private_cv.py setup", file=sys.stderr)
        return 1
    editor = os.environ.get("EDITOR", "nano")
    return subprocess.call([editor, str(cfg.mapping_file)])


def cmd_sync_keys(args: argparse.Namespace) -> int:
    return cmd_sync(args)


def cmd_refresh(args: argparse.Namespace) -> int:
    """After a repo renovation: update config, stubs, and mapping keys from the template."""
    args.refresh_project_dir = True
    return cmd_sync(args)


def _copy_cv_sources_to(dest_dir: Path, profiles: list) -> None:
    from shutil import copy2

    dest_dir.mkdir(parents=True, exist_ok=True)
    for pr in profiles:
        # Always write industry.md / academic.md (not .demo.md) in destination dirs.
        target = dest_dir / f"{pr.track}.md"
        copy2(pr.source_path, target)
        print(f"  {pr.source_path} -> {target}")


def cmd_export_cv_sources(_: argparse.Namespace) -> int:
    """Copy current resolved CV markdown into ~/private/cv/cv/."""
    from shared.cv_loader import load_default_profiles, resolve_cv_dir

    cfg = load_config()
    dest = cfg.private_dir / "cv"

    profiles = load_default_profiles()
    if not profiles:
        print("No industry/academic CV found.", file=sys.stderr)
        print(f"  Looked in: {resolve_cv_dir()}", file=sys.stderr)
        return 1

    _copy_cv_sources_to(dest, profiles)
    print(f"\nPrivate CV sources: {dest}")
    print("Personal files shared/cv/industry.md and academic.md are gitignored.")
    return 0


def cmd_recover_cv_sources(args: argparse.Namespace) -> int:
    """
    Restore industry.md + academic.md from the newest cv_runs/*/cv_*_source.md snapshots.
    Writes to ~/private/cv/cv/ and optionally shared/cv/ (gitignored).
    """
    from shutil import copy2

    from repo_paths import CV_GENERATION_DIR
    from shared.cv_loader import _PACKAGE_CV_DIR

    runs_dir = CV_GENERATION_DIR / "cv_runs"
    if not runs_dir.is_dir():
        print(f"No cv_runs directory: {runs_dir}", file=sys.stderr)
        return 1

    candidates = sorted(
        (p for p in runs_dir.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    pairs = (
        ("industry", "cv_industry_source.md"),
        ("academic", "cv_academic_source.md"),
    )
    chosen: Path | None = None
    for run_dir in candidates:
        if all((run_dir / fname).is_file() for _, fname in pairs):
            chosen = run_dir
            break

    if chosen is None:
        print("No run folder with both cv_industry_source.md and cv_academic_source.md.", file=sys.stderr)
        return 1

    cfg = load_config()
    private_cv = cfg.private_dir / "cv"
    if private_cv.is_file():
        print(f"Warning: {private_cv} is a file, not a directory — skipping private copy.", file=sys.stderr)
        private_dest: Path | None = None
    else:
        private_dest = private_cv
        private_dest.mkdir(parents=True, exist_ok=True)
    shared_cv = _PACKAGE_CV_DIR
    write_shared = not getattr(args, "no_shared", False)

    print(f"Recovering from cv_runs/{chosen.name}/")
    for track, fname in pairs:
        src = chosen / fname
        dest_dirs: list[Path] = []
        if private_dest is not None:
            dest_dirs.append(private_dest)
        if write_shared:
            dest_dirs.append(shared_cv)
        for dest_dir in dest_dirs:
            target = dest_dir / f"{track}.md"
            copy2(src, target)
            print(f"  {src.name} -> {target}")

    print("\nRecovered files are anonymized master CVs (e.g. MITCH EVANS placeholders).")
    print("Deanonymize on apply via ~/private/cv/cv_identity_mapping.json.")
    if private_dest is not None:
        print(f"Private: {private_dest}")
    if write_shared:
        print(f"Local (gitignored): {shared_cv}/industry.md, academic.md")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    cfg = load_config()
    if not cfg.repo_root.is_dir():
        print(f"Project not found: {cfg.repo_root}", file=sys.stderr)
        print("Fix CV_PROJECT_DIR in config.env or re-run setup from the repo.", file=sys.stderr)
        return 1

    if getattr(args, "refresh_project_dir", False):
        cfg = PrivateConfig(
            repo_root=REPO_ROOT,
            cv_package_dir=CV_GENERATION_DIR,
            private_dir=cfg.private_dir,
            mapping_file=cfg.mapping_file,
            output_dir=cfg.output_dir,
            profile_photo=cfg.profile_photo,
        )

    cfg.private_dir.mkdir(parents=True, exist_ok=True)
    cfg.output_dir.mkdir(parents=True, exist_ok=True)
    write_config(cfg)
    print(f"Config:  {cfg.private_dir / CONFIG_NAME}")

    result = merge_mapping_from_example(cfg)
    print_mapping_sync_report(result, cfg.mapping_file)
    _warn_legacy_degree_mapping_keys(cfg.mapping_file)

    ensure_repo_package_installed(cfg)
    write_private_stubs(cfg)
    print(f"\nShortcuts updated: {cfg.private_dir / STUB_CV}, {cfg.private_dir / STUB_SYNC}")

    if result.added_keys:
        print(f"\nFill new placeholder values in: {cfg.mapping_file}")
        print(f"  ./cv edit   # from {cfg.private_dir}")
    return 0


def _prefer_repo_run_source(
    cfg: PrivateConfig, resolved: Path, run_id: str
) -> tuple[Path, str]:
    """
    If the user pointed at deanonymized output (only English artifacts), use the
    anonymized repo run folder so *_no.md sources are found.
    """
    try:
        resolved.resolve().relative_to(cfg.output_dir.resolve())
    except ValueError:
        return resolved, run_id

    repo_run = cfg.runs_root / run_id
    if not (repo_run / "final_cv.md").is_file():
        matched = find_repo_run_by_timestamp(cfg.runs_root, run_id)
        if matched is not None:
            repo_run = matched
    if (repo_run / "final_cv.md").is_file():
        print(
            f"Using repo source cv_runs/{repo_run.name} "
            f"(not {cfg.output_dir.name}/{run_id}; Norwegian sources live in the repo run).",
            file=sys.stderr,
        )
        return repo_run, repo_run.name
    return resolved, run_id


def resolve_run_dir(cfg: PrivateConfig, run_arg: str) -> tuple[Path, str]:
    raw = run_arg.strip()
    if not raw:
        raise SystemExit("Run id or path is required.")

    path_arg = Path(raw).expanduser()
    if path_arg.is_file() and path_arg.name == "final_cv.md":
        path_arg = path_arg.parent
    if path_arg.is_dir():
        resolved = path_arg.resolve()
        if (resolved / "final_cv.md").is_file():
            return _prefer_repo_run_source(cfg, resolved, resolved.name)

    sub = raw.removeprefix("cv_runs/").strip("/")
    if Path(sub).name != sub:
        by_name = cfg.runs_root / Path(sub).name
        if (by_name / "final_cv.md").is_file():
            return by_name, by_name.name
        sub = Path(sub).name

    direct = cfg.runs_root / sub
    if (direct / "final_cv.md").is_file():
        return direct, sub

    by_timestamp = find_repo_run_by_timestamp(cfg.runs_root, sub)
    if by_timestamp is not None:
        if by_timestamp.name != sub:
            print(f"Resolved run folder: cv_runs/{by_timestamp.name}")
        return by_timestamp, by_timestamp.name

    matches = sorted(
        d for d in cfg.runs_root.glob(f"{sub}*") if d.is_dir() and (d / "final_cv.md").is_file()
    )
    if len(matches) == 1:
        resolved = matches[0].name
        print(f"Resolved run folder: cv_runs/{resolved}")
        return matches[0], resolved
    if len(matches) > 1:
        print(f"Multiple runs match '{sub}':", file=sys.stderr)
        for d in matches:
            print(f"  cv_runs/{d.name}", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(f"Missing {direct / 'final_cv.md'} — generate the CV in the project first.")


def _warn_legacy_degree_mapping_keys(mapping_file: Path) -> None:
    """Old template keys replaced the whole ### line and broke education parsing in PDFs."""
    from cv_generation.deanonymize_cvs import is_placeholder_value

    if not mapping_file.is_file():
        return
    raw = load_raw_json(mapping_file)
    legacy = {
        "### M.Sc., Computing": "M.Sc., Computing",
        "### B.Eng.": "B.Eng.",
    }
    warnings: list[str] = []
    for old_key, new_key in legacy.items():
        if old_key not in raw:
            continue
        value = raw[old_key]
        if not isinstance(value, str):
            continue
        if is_placeholder_value(old_key, value.strip()):
            continue
        warnings.append(f"  ! Remove {old_key!r} and use {new_key!r} → <your degree title> instead.")
    if warnings:
        print("\nMapping fix needed (master's/bachelor's may be missing from PDF):", file=sys.stderr)
        for line in warnings:
            print(line, file=sys.stderr)
        print(f"  Edit: {mapping_file}\n  Then: ./cv sync && ./cv apply <run>\n", file=sys.stderr)


def _warn_education_parse(
    cfg: PrivateConfig,
    source_md: Path,
    deanon_md: Path,
    *,
    label: str = "deanonymized CV",
) -> None:
    """Compare education entry counts in source vs deanonymized markdown (PDF parser)."""
    try:
        from cv_generation.cv_pdf_renderer import parse_cv_markdown
    except ImportError:
        return

    if not source_md.is_file() or not deanon_md.is_file():
        return

    src_n = len(parse_cv_markdown(source_md.read_text(encoding="utf-8")).education)
    out_n = len(parse_cv_markdown(deanon_md.read_text(encoding="utf-8")).education)
    if src_n and out_n < src_n:
        print(
            f"\nWarning ({label}): parsed {out_n} education entries, "
            f"expected {src_n} from the anonymized CV.",
            file=sys.stderr,
        )
        print(
            "  Degree mapping values must stay as separate lines under ## Education "
            "(one block per degree; do not merge into one line).",
            file=sys.stderr,
        )
        print(
            "  Check keys like '### M.Sc., Computing' and '### B.Eng.' in:",
            file=sys.stderr,
        )
        print(f"    {cfg.mapping_file}", file=sys.stderr)
        print(f"  Open {deanon_md} and verify ## Education still has three blocks.\n", file=sys.stderr)


def run_deanonymize(
    cfg: PrivateConfig,
    input_dir: Path,
    output_dir: Path,
    *,
    dry_run: bool = False,
    strict: bool = True,
    glob: str = "final_cv.md",
) -> int:
    mapping_file = resolve_mapping_for_artifact(cfg, input_dir, glob)
    if not mapping_file.is_file():
        print(
            f"No mapping found for {glob}: expected {mapping_file}.",
            file=sys.stderr,
        )
        return 1
    os.environ["CV_IDENTITY_MAPPING"] = str(mapping_file)
    cmd = [
        str(cfg.python),
        str(cfg.cv_package_dir / "deanonymize_cvs.py"),
        "--mapping",
        str(mapping_file),
        "--input-dir",
        str(input_dir),
        "--glob",
        glob,
        "--output-dir",
        str(output_dir),
    ]
    if dry_run:
        cmd.append("--dry-run")
    if strict and not dry_run:
        cmd.append("--strict")
    return subprocess.call(cmd, cwd=str(cfg.cv_package_dir))


def run_render_pdf(cfg: PrivateConfig, markdown: Path, *, plain: bool | None = None) -> int:
    from cv_generation.cv_application_artifacts import is_plain_pdf_markdown

    mapping_for_render = mapping_override_path(cfg, markdown.parent, markdown.name)
    if mapping_for_render is not None:
        os.environ["CV_IDENTITY_MAPPING"] = str(mapping_for_render)
    elif cfg.mapping_file.is_file():
        os.environ["CV_IDENTITY_MAPPING"] = str(cfg.mapping_file)
    else:
        os.environ.pop("CV_IDENTITY_MAPPING", None)
    pdf = markdown.with_suffix(".pdf")
    cmd = [
        str(cfg.python),
        str(cfg.cv_package_dir / "render_cv_pdf.py"),
        str(markdown),
        "-o",
        str(pdf),
    ]
    use_plain = plain if plain is not None else is_plain_pdf_markdown(markdown)
    if use_plain:
        cmd.append("--plain")
    if cfg.profile_photo.is_file() and not use_plain:
        cmd.extend(["--profile-photo", str(cfg.profile_photo)])
        print(f"Using profile photo: {cfg.profile_photo}")
    return subprocess.call(cmd, cwd=str(cfg.cv_package_dir))


def _apply_supplementary_artifacts(
    cfg: PrivateConfig,
    input_dir: Path,
    deanon_out: Path,
    *,
    dry_run: bool,
    md_only: bool,
    render_pdf: bool = True,
) -> int:
    """Deanonymize cover letter, application letter, research proposal, etc. when present."""
    from cv_generation.cv_application_artifacts import supplementary_artifact_filenames

    exit_code = 0
    for filename in supplementary_artifact_filenames():
        src = input_dir / filename
        if not src.is_file():
            continue
        code = run_deanonymize(
            cfg,
            input_dir,
            deanon_out,
            dry_run=dry_run,
            strict=False,
            glob=filename,
        )
        if code != 0:
            print(f"Deanonymize failed for {filename} (exit {code}).", file=sys.stderr)
            exit_code = code
            continue
        if dry_run:
            continue
        deanon_md = deanon_out / filename
        if not deanon_md.is_file():
            print(
                f"Expected {deanon_md} after deanonymize (no output written for {filename}).",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        print(f"Deanonymized {filename}: {deanon_md}")
        if md_only or not render_pdf:
            continue
        pdf_code = run_render_pdf(cfg, deanon_md)
        if pdf_code != 0:
            exit_code = pdf_code
    return exit_code


def resolve_deanon_output_dir(
    cfg: PrivateConfig,
    input_dir: Path,
    run_id: str,
    *,
    announce: bool = True,
) -> Path:
    """Deanonymized output folder; enriches legacy run ids with company metadata."""
    output_name = enrich_run_folder_name(run_id, input_dir)
    if announce and output_name != run_id:
        print(f"Deanonymized output folder: {output_name}")
    return cfg.output_dir / output_name


def apply_one_run(cfg: PrivateConfig, run_arg: str, *, dry_run: bool, md_only: bool) -> int:
    """Deanonymize a single cv_runs folder; return exit code."""
    input_dir, run_id = resolve_run_dir(cfg, run_arg)
    if cfg.mapping_file.is_file():
        _warn_legacy_degree_mapping_keys(cfg.mapping_file)
    deanon_out = resolve_deanon_output_dir(cfg, input_dir, run_id)
    cv_code = run_deanonymize(
        cfg,
        input_dir,
        deanon_out,
        dry_run=dry_run,
        strict=not dry_run,
        glob="final_cv.md",
    )

    supp_code = _apply_supplementary_artifacts(
        cfg,
        input_dir,
        deanon_out,
        dry_run=dry_run,
        md_only=md_only,
        render_pdf=not md_only,
    )

    if dry_run:
        return cv_code if cv_code != 0 else supp_code

    cv_strict_failed = cv_code != 0
    if cv_strict_failed:
        print(
            "\nEnglish CV deanonymize incomplete (--strict). "
            "Fill the mapping keys still listed as anonymized text above, then re-run apply. "
            "Continuing with supplementary artifacts and Norwegian files.",
            file=sys.stderr,
        )

    deanon_md = deanon_out / "final_cv.md"
    if deanon_md.is_file():
        if not cv_strict_failed:
            print(f"Deanonymized markdown: {deanon_md}")
        _warn_education_parse(cfg, input_dir / "final_cv.md", deanon_md)
    elif not cv_strict_failed:
        print(f"Expected {deanon_md}", file=sys.stderr)
        return 1

    loc_code = _apply_localized_artifacts(
        cfg,
        input_dir,
        deanon_out,
        dry_run=dry_run,
        md_only=md_only,
        render_pdf=not md_only,
    )

    if md_only:
        if cv_code != 0:
            return cv_code
        if supp_code != 0:
            return supp_code
        return loc_code

    code = 0
    if not cv_strict_failed and deanon_md.is_file():
        code = run_render_pdf(cfg, deanon_md)
        if code == 0:
            _warn_education_parse(cfg, input_dir / "final_cv.md", deanon_md, label="after PDF render")

    if cv_code != 0:
        return cv_code
    if supp_code != 0:
        return supp_code
    if code != 0:
        return code
    return loc_code


def cmd_apply(args: argparse.Namespace) -> int:
    cfg = load_config()
    runs: list[str] = list(args.runs)
    if not runs:
        print("At least one run id is required.", file=sys.stderr)
        return 1

    exit_code = 0
    output_dirs: list[Path] = []
    for run_arg in runs:
        print(f"\n======== {run_arg} ========")
        try:
            input_dir, run_id = resolve_run_dir(cfg, run_arg)
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            exit_code = 1
            continue
        code = apply_one_run(cfg, run_arg, dry_run=args.dry_run, md_only=args.md_only)
        if code != 0:
            exit_code = code
        elif not args.dry_run:
            output_dirs.append(
                resolve_deanon_output_dir(cfg, input_dir, run_id, announce=False)
            )

    if len(runs) > 1 and not args.dry_run:
        print("\n======== Bulk apply summary ========")
        if output_dirs:
            print(f"Output under {cfg.output_dir}/")
            for path in output_dirs:
                print(f"  {path}")
        else:
            print("No runs completed successfully.", file=sys.stderr)

    return exit_code


def _apply_localized_artifacts(
    cfg: PrivateConfig,
    input_dir: Path,
    deanon_out: Path,
    *,
    dry_run: bool,
    md_only: bool,
    render_pdf: bool = True,
) -> int:
    """Deanonymize and render Norwegian *_no.md artifacts when present."""
    exit_code = 0
    # Never use --strict on localized files: mapping keys are English-canonical
    # (section labels, dates) and will not all appear in *_no.md.
    pairs = ("final_cv_no.md", "cover_letter_no.md", "reference_projects_no.md")
    present = [name for name in pairs if (input_dir / name).is_file()]
    missing = [name for name in pairs if name not in present]
    if missing and not dry_run:
        print(
            "Norwegian artifacts not in run folder (skipped): "
            + ", ".join(missing),
            file=sys.stderr,
        )
        if "final_cv_no.md" in missing:
            print(
                "  final_cv_no.md is not in the repo run folder — apply only copies files that "
                "already exist there.\n"
                "  Generate it, then apply again:\n"
                f"    cd {cfg.private_dir} && ./cv localize {input_dir.name}",
                file=sys.stderr,
            )
    if present and not dry_run:
        print(f"Norwegian sources in {input_dir}: {', '.join(present)}")
    for glob_name in pairs:
        src = input_dir / glob_name
        if not src.is_file():
            continue
        code = run_deanonymize(
            cfg,
            input_dir,
            deanon_out,
            dry_run=dry_run,
            strict=False,
            glob=glob_name,
        )
        if code != 0:
            print(f"Deanonymize failed for {glob_name} (exit {code}).", file=sys.stderr)
            exit_code = code
            continue
        if dry_run:
            continue
        deanon_md = deanon_out / glob_name
        if not deanon_md.is_file():
            print(
                f"Expected {deanon_md} after deanonymize "
                f"(no output written for {glob_name}).",
                file=sys.stderr,
            )
            exit_code = 1
            continue
        print(f"Deanonymized markdown: {deanon_md}")
        if md_only or not render_pdf:
            continue
        pdf_code = run_render_pdf(cfg, deanon_md)
        if pdf_code != 0:
            exit_code = pdf_code
    return exit_code


def cmd_localize(args: argparse.Namespace) -> int:
    """Create Norwegian *_no.md in the repo run folder (required before apply can copy them)."""
    from cv_generation.cv_norwegian import localize_run

    cfg = load_config()
    input_dir, run_id = resolve_run_dir(cfg, args.run)
    artifact = getattr(args, "artifact", "cv")
    if artifact == "both":
        artifacts: tuple[str, ...] = ("cv", "cover-letter")
    else:
        artifacts = (artifact,)  # type: ignore[assignment]

    print(f"Repo run: cv_runs/{run_id}")
    code = localize_run(
        input_dir,
        artifacts=artifacts,  # type: ignore[arg-type]
        provider=args.provider.strip().lower(),
        model=args.model,
        no_pdf=args.no_pdf,
        profile_photo=cfg.profile_photo if cfg.profile_photo.is_file() else None,
    )
    if code == 0 and (input_dir / "final_cv_no.md").is_file():
        print(f"\nNext: cd {cfg.private_dir} && ./cv apply {run_id}")
    return code


def cmd_pdf(args: argparse.Namespace) -> int:
    cfg = load_config()
    md = _expand(args.markdown)
    if not md.is_file():
        print(f"Not found: {md}", file=sys.stderr)
        return 1
    return run_render_pdf(cfg, md)


def _audit_markdown(path: Path, active: dict[str, str], skipped: list[str], raw: dict) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    print(f"\n--- {path.name} ---")
    found_active = [k for k in active if k in text]
    unfilled = [k for k in raw if not k.startswith("_") and k in text and k in skipped]
    if found_active:
        print(f"Will replace ({len(found_active)}):")
        for k in found_active[:15]:
            print(f"  ✓ {k!r}")
        if len(found_active) > 15:
            print(f"  ... and {len(found_active) - 15} more")
    else:
        print("No mapping keys found in file (may already be deanonymized or use different placeholders).")
    if unfilled:
        print(f"Still placeholder values ({len(unfilled)}):")
        for k in unfilled:
            tag = " ← fix name here" if k in ("ALEX RIVERA", "MITCH EVANS", "AI SPECIALIST") else ""
            print(f"  ! {k!r}{tag}")


def cmd_audit(args: argparse.Namespace) -> int:
    from cv_generation.cv_application_artifacts import (
        CV_MARKDOWN,
        supplementary_artifact_filenames,
    )
    from cv_generation.deanonymize_cvs import load_mapping

    cfg = load_config()
    input_dir, _ = resolve_run_dir(cfg, args.run)
    md_path = input_dir / CV_MARKDOWN

    if not cfg.mapping_file.is_file():
        print(f"No mapping at {cfg.mapping_file}", file=sys.stderr)
        return 1

    active, skipped = load_mapping(cfg.mapping_file)
    raw = load_raw_json(cfg.mapping_file)

    print(f"CV: {md_path}")
    print(f"Mapping: {cfg.mapping_file}\n")

    if not md_path.is_file():
        print(f"Missing {md_path}", file=sys.stderr)
        return 1

    text = md_path.read_text(encoding="utf-8")

    found_active = [k for k in active if k in text]
    missing_active = [k for k in active if k not in text]
    skipped_in_cv = [k for k in skipped if k in text]
    unfilled = [k for k in raw if not k.startswith("_") and k in text and k in skipped]

    print(f"Will replace ({len(found_active)}):")
    for k in found_active[:30]:
        print(f"  ✓ {k!r} → {active[k]!r}")
    if len(found_active) > 30:
        print(f"  ... and {len(found_active) - 30} more")

    if missing_active:
        print(f"\nIn mapping but not in CV ({len(missing_active)}) — safe to remove or keep:")
        for k in missing_active[:15]:
            print(f"  · {k!r}")
        if len(missing_active) > 15:
            print(f"  ... and {len(missing_active) - 15} more")

    if unfilled:
        print(f"\nStill in CV but mapping value is a placeholder ({len(unfilled)}) — edit mapping:")
        for k in unfilled:
            tag = " ← fix name here" if k in ("ALEX RIVERA", "MITCH EVANS", "AI SPECIALIST") else ""
            print(f"  ! {k!r}{tag}")
        print(f"\n  ./cv edit   # file: {cfg.mapping_file}")

    # Suggest keys from example that appear in CV but are absent from mapping file
    example_path = example_mapping_path(cfg.cv_package_dir)
    if example_path.is_file():
        example = load_raw_json(example_path)
        need_key = [
            k
            for k in example
            if not k.startswith("_") and k in text and k not in raw
        ]
        if need_key:
            print(f"\nIn CV but missing from your mapping file ({len(need_key)}) — run sync-keys:")
            for k in need_key[:20]:
                print(f"  + {k!r}")

    for filename in supplementary_artifact_filenames():
        _audit_markdown(input_dir / filename, active, skipped, raw)

    return 0


def cmd_all_runs(args: argparse.Namespace) -> int:
    cfg = load_config()
    runs = sorted(cfg.runs_root.glob("*/final_cv.md"))
    if not runs:
        print(f"No runs under {cfg.runs_root}", file=sys.stderr)
        return 1
    exit_code = 0
    for md in runs:
        run_id = md.parent.name
        print(f"\n======== cv_runs/{run_id} ========")
        ns = argparse.Namespace(runs=[f"cv_runs/{run_id}"], dry_run=args.dry_run, md_only=args.md_only)
        if cmd_apply(ns) != 0:
            exit_code = 1
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Private CV deanonymize/render (PII stays in ~/private/cv/)",
    )
    p.add_argument(
        "--private-dir",
        type=Path,
        default=None,
        help=f"Override private folder (default: {DEFAULT_PRIVATE_DIR})",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("setup", help="Create ~/private/cv, config, mapping template, and cv shortcut")

    sub.add_parser(
        "export-cv-sources",
        help="Copy resolved industry.md + academic.md to ~/private/cv/cv/",
    )

    rec_p = sub.add_parser(
        "recover-cv-sources",
        help="Restore industry.md + academic.md from latest cv_runs snapshot",
    )
    rec_p.add_argument(
        "--no-shared",
        action="store_true",
        help="Only write ~/private/cv/cv/, not shared/cv/",
    )

    sub.add_parser("edit", help=f"Open {MAPPING_NAME} in $EDITOR")

    sync_p = sub.add_parser(
        "sync",
        help="Merge new mapping keys from repo template; refresh config and ~/private/cv shortcuts",
    )
    sync_p.add_argument(
        "--refresh-project-dir",
        action="store_true",
        help="Point CV_PROJECT_DIR at the repo that contains cv_generation/",
    )

    sub.add_parser(
        "refresh",
        help="After repo layout changes: sync --refresh-project-dir + update ~/private/cv shortcuts",
    )

    sub.add_parser(
        "sync-keys",
        help="Alias for sync (mapping merge only)",
    )

    audit_p = sub.add_parser("audit", help="Show mapping coverage for a run's final_cv.md")
    audit_p.add_argument("run", help="cv_runs/<id> or <id>")

    apply_p = sub.add_parser(
        "apply",
        help="Deanonymize final_cv.md + supplementary docs (cover/application letter, research proposal) + PDF",
    )
    apply_p.add_argument(
        "runs",
        nargs="+",
        help="One or more cv_runs/<id> folder basenames (e.g. 20260713T120000Z_Company_role)",
    )
    apply_p.add_argument("--dry-run", action="store_true", help="Preview replacements only")
    apply_p.add_argument("--md-only", action="store_true", help="Skip PDF render")

    loc_p = sub.add_parser(
        "localize",
        help="Generate Norwegian final_cv_no.md (and/or cover_letter_no.md) in the repo run",
    )
    loc_p.add_argument("run", help="cv_runs/<id> or <id>")
    loc_p.add_argument(
        "--artifact",
        choices=("cv", "cover-letter", "both"),
        default="cv",
        help="Which file to localize (default: cv only — use when cover_letter_no.md already exists)",
    )
    loc_p.add_argument("--provider", default="cursor", help="Agent backend (cursor, anthropic, openai)")
    loc_p.add_argument("--model", default="", help="Model id (provider-specific)")
    loc_p.add_argument("--no-pdf", action="store_true", help="Skip anonymized PDF in repo run")

    pdf_p = sub.add_parser("pdf", help="Render PDF from existing deanonymized markdown")
    pdf_p.add_argument("markdown", type=Path, help="Path to final_cv.md")

    all_p = sub.add_parser("all-runs", help="Apply to every cv_runs/*/final_cv.md")
    all_p.add_argument("--dry-run", action="store_true")
    all_p.add_argument("--md-only", action="store_true")

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.private_dir:
        os.environ["CV_PRIVATE_DIR"] = str(_expand(args.private_dir))

    handlers = {
        "setup": cmd_setup,
        "export-cv-sources": cmd_export_cv_sources,
        "recover-cv-sources": cmd_recover_cv_sources,
        "edit": cmd_edit,
        "sync": cmd_sync,
        "refresh": cmd_refresh,
        "sync-keys": cmd_sync_keys,
        "audit": cmd_audit,
        "apply": cmd_apply,
        "localize": cmd_localize,
        "pdf": cmd_pdf,
        "all-runs": cmd_all_runs,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
