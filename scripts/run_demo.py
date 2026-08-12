#!/usr/bin/env python3
"""
End-to-end demo of the job-search + CV pipeline using fictional data only.

No API keys required for --assemble (default). Uses:
  - shared/cv/demo_only/  (ALEX RIVERA demo CV)
  - cv_generation/jobs/demo_northline_ml_engineer.txt
  - cv_generation/demo/northline_ml_engineer/  (committed sample run)

Usage (from repo root):
  .venv/bin/python scripts/run_demo.py              # walkthrough + verify
  .venv/bin/python scripts/run_demo.py --assemble   # rebuild final_cv.md (no LLM)
  .venv/bin/python scripts/run_demo.py --pdf        # render final_cv.pdf
  .venv/bin/python scripts/run_demo.py --prepare    # refresh tasks + re-copy seed outputs
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from cv_generation.agent_contract import OUTPUT_ORDER
from repo_paths import CV_GENERATION_DIR, REPO_ROOT, SHARED_DIR

DEMO_CV_DIR = SHARED_DIR / "cv" / "demo_only"
DEMO_JOB = CV_GENERATION_DIR / "jobs" / "demo_northline_ml_engineer.txt"
DEMO_RUN = CV_GENERATION_DIR / "demo" / "northline_ml_engineer"
SEED_DIR = CV_GENERATION_DIR / "demo" / "seed"
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"

# Seed covers parser → ATS (assembler is built by --assemble / manual provider).
AGENT_OUTPUTS = OUTPUT_ORDER[:5]


def _run(cmd: list[str], env: dict[str, str] | None = None) -> int:
    print("$", " ".join(cmd))
    merged = os.environ.copy()
    if env:
        merged.update(env)
    merged["CV_SOURCE_DIR"] = str(DEMO_CV_DIR)
    merged["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep + merged.get("PYTHONPATH", "")
    return subprocess.call(cmd, cwd=REPO_ROOT, env=merged)


def ensure_demo_cv_dir() -> None:
    if not DEMO_CV_DIR.is_dir():
        raise SystemExit(f"Missing demo CV dir: {DEMO_CV_DIR}")
    for name in ("industry.md", "academic.md"):
        if not (DEMO_CV_DIR / name).is_file():
            raise SystemExit(f"Missing {DEMO_CV_DIR / name}")


def missing_agent_outputs(run_dir: Path) -> list[str]:
    return [n for n in AGENT_OUTPUTS if not (run_dir / n).is_file()]


def copy_seed_outputs(run_dir: Path) -> None:
    for name in AGENT_OUTPUTS:
        src = SEED_DIR / name
        if not src.is_file():
            raise SystemExit(f"Missing seed file: {src}")
        shutil.copy2(src, run_dir / name)
        print(f"  seeded {name}")


def prepare_run(force: bool) -> int:
    ensure_demo_cv_dir()
    cmd = [
        str(PYTHON),
        "-m",
        "cv_generation.run_cv_tailoring",
        "--job-file",
        str(DEMO_JOB),
        "--company",
        "Northline Labs",
        "--role",
        "ML Engineer",
        "--run-dir",
        str(DEMO_RUN),
    ]
    if force:
        cmd.append("--force")
    code = _run(cmd)
    if code != 0:
        return code
    print("\nCopying committed seed agent outputs (fictional, no LLM):")
    copy_seed_outputs(DEMO_RUN)
    return assemble_run()


def assemble_run() -> int:
    if not DEMO_RUN.is_dir():
        print(f"Demo run missing. Run: {PYTHON.name} scripts/run_demo.py --prepare", file=sys.stderr)
        return 1
    missing = missing_agent_outputs(DEMO_RUN)
    if missing:
        print(f"Missing outputs in demo run: {', '.join(missing)}", file=sys.stderr)
        print("Run with --prepare or copy files from cv_generation/demo/seed/", file=sys.stderr)
        return 1
    return _run(
        [
            str(PYTHON),
            "-m",
            "cv_generation.run_agent_pipeline",
            "--run-dir",
            str(DEMO_RUN),
            "--provider",
            "manual",
        ]
    )


def render_pdf() -> int:
    final_md = DEMO_RUN / "final_cv.md"
    if not final_md.is_file():
        print("final_cv.md not found; run --assemble first.", file=sys.stderr)
        return 1
    return _run(
        [
            str(PYTHON),
            "-m",
            "cv_generation.run_agent_pipeline",
            "--run-dir",
            str(DEMO_RUN),
            "--render-only",
        ]
    )


def print_walkthrough() -> None:
    print(
        """
╔══════════════════════════════════════════════════════════════════╗
║  Job search automation — DEMO (fictional ALEX RIVERA / Northline) ║
╚══════════════════════════════════════════════════════════════════╝

Pipeline overview
─────────────────
  1. Job posting (text)     → cv_generation/jobs/demo_northline_ml_engineer.txt
  2. Prepare run workspace  → cv_generation/demo/northline_ml_engineer/
  3. Subagents (JSON steps) → 01_jd_parser … 05_ats_checker (seeded for demo)
  4. Assemble final CV      → final_cv.md + tailored_cv.md (deterministic)
  5. Optional PDF           → final_cv.pdf (--pdf)
  6. Job search (optional)  → NAV ingest → score → Streamlit dashboard

Demo CV source (never your real profile):
  shared/cv/demo_only/industry.md
  shared/cv/demo_only/academic.md

Sample run folder (safe to commit):
"""
    )
    print(f"  {DEMO_RUN.relative_to(REPO_ROOT)}/")
    print("\nKey artifacts to open after --assemble:")
    for name in (
        "job_posting.txt",
        "03_track_selector_output.json",
        "04_bullet_tailor_output.json",
        "05_ats_checker_output.json",
        "final_cv.md",
        "cover_letter.md",
    ):
        path = DEMO_RUN / name
        mark = "✓" if path.is_file() else "·"
        print(f"  {mark} {name}")

    print(
        """
Commands
────────
  .venv/bin/python scripts/run_demo.py --prepare   # refresh tasks + seed JSON + assemble
  .venv/bin/python scripts/run_demo.py --assemble  # rebuild final_cv.md only
  .venv/bin/python scripts/run_demo.py --pdf       # render PDF locally

Full docs: docs/DEMO.md

Job search stack (separate terminal, needs network for NAV):
  .venv/bin/python -m job_search.ingest_nav_jobs --since-days 7 --max-pages 1
  .venv/bin/python -m job_search.score_jobs
  .venv/bin/streamlit run job_search/dashboard.py
"""
    )


def main() -> int:
    p = argparse.ArgumentParser(description="Run fictional end-to-end CV demo")
    p.add_argument("--prepare", action="store_true", help="Recreate demo run folder and seed agent outputs")
    p.add_argument("--assemble", action="store_true", help="Run deterministic assembler → final_cv.md")
    p.add_argument("--pdf", action="store_true", help="Render final_cv.pdf from final_cv.md")
    p.add_argument("--force", action="store_true", help="With --prepare, overwrite demo run dir")
    args = p.parse_args()

    if not PYTHON.is_file():
        print(f"Create venv first: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt", file=sys.stderr)
        return 1

    if args.prepare:
        return prepare_run(force=args.force)
    if args.pdf:
        return render_pdf()
    if args.assemble:
        ensure_demo_cv_dir()
        return assemble_run()

    print_walkthrough()
    ensure_demo_cv_dir()
    if not DEMO_RUN.is_dir():
        print("\nDemo run not initialized. Running --prepare …\n")
        return prepare_run(force=True)

    missing = missing_agent_outputs(DEMO_RUN)
    if missing or not (DEMO_RUN / "final_cv.md").is_file():
        print("\nRefreshing assembly …\n")
        if missing:
            copy_seed_outputs(DEMO_RUN)
        return assemble_run()

    print("\nDemo run looks complete. Use --assemble to rebuild final_cv.md or --pdf for PDF.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
