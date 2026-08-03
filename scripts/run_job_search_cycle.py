#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[1]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from job_search.logging_config import configure_logging, get_logger

log = get_logger("job_search.cycle")


def run_step(label: str, command: list[str]) -> None:
    log.info("step %s command=%s", label, " ".join(shlex.quote(part) for part in command))
    print(f"[job-search] {label}: {' '.join(shlex.quote(part) for part in command)}")
    subprocess.run(command, check=True)
    log.info("step %s complete", label)


def main() -> int:
    log_path = configure_logging(console=True)
    log.info("job search cycle start log_file=%s", log_path)

    parser = argparse.ArgumentParser(
        description="Run the daily NAV + FINN ingest + score cycle with the repository defaults.",
    )
    parser.add_argument("--db", default="", help="SQLite path passed through to ingest + score")
    parser.add_argument("--track", choices=("academic", "industry", "both"), default="both")
    parser.add_argument("--print-top", type=int, default=10, help="Top scored jobs to print after scoring")
    parser.add_argument("--skip-ingest", action="store_true", help="Skip all ingest steps")
    parser.add_argument("--skip-nav-ingest", action="store_true", help="Skip NAV ingest (FINN still runs)")
    parser.add_argument("--skip-finn-ingest", action="store_true", help="Skip FINN ingest (NAV still runs)")
    parser.add_argument("--skip-score", action="store_true", help="Skip the score step")
    parser.add_argument(
        "--ingest-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="Extra argument forwarded to job_search.ingest_nav_jobs (repeatable)",
    )
    parser.add_argument(
        "--finn-ingest-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="Extra argument forwarded to job_search.ingest_finn_jobs (repeatable)",
    )
    parser.add_argument(
        "--score-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="Extra argument forwarded to job_search.score_jobs (repeatable)",
    )
    args = parser.parse_args()

    if not args.skip_ingest:
        if not args.skip_nav_ingest:
            ingest_cmd = [sys.executable, "-m", "job_search.ingest_nav_jobs"]
            if args.db:
                ingest_cmd.extend(["--db", args.db])
            ingest_cmd.extend(args.ingest_arg)
            run_step("ingest-nav", ingest_cmd)

        if not args.skip_finn_ingest:
            finn_cmd = [sys.executable, "-m", "job_search.ingest_finn_jobs"]
            if not any(arg == "--search-track" for arg in args.finn_ingest_arg):
                finn_cmd.extend(["--search-track", "both"])
            if args.db:
                finn_cmd.extend(["--db", args.db])
            finn_cmd.extend(args.finn_ingest_arg)
            run_step("ingest-finn", finn_cmd)

    if not args.skip_score:
        score_cmd = [
            sys.executable,
            "-m",
            "job_search.score_jobs",
            "--track",
            args.track,
            "--print-top",
            str(args.print_top),
        ]
        if args.db:
            score_cmd.extend(["--db", args.db])
        score_cmd.extend(args.score_arg)
        run_step("score", score_cmd)

    log.info("job search cycle complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
