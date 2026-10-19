#!/usr/bin/env python3
"""Launch the Bootstrap job-search UI (FastAPI + uvicorn)."""
from __future__ import annotations

import argparse
import logging
import os

import uvicorn

from job_search.logging_config import configure_logging

DEFAULT_PORT = 8765


class _DropStreamlitProbeAccessLogs(logging.Filter):
    """Hide leftover Streamlit health pings from uvicorn access logs."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "/_stcore/" not in record.getMessage()


def main() -> None:
    parser = argparse.ArgumentParser(description="Job search web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()
    configure_logging(console=False)
    logging.getLogger("uvicorn.access").addFilter(_DropStreamlitProbeAccessLogs())
    print(f"Job search UI: http://{args.host}:{args.port}/")
    uvicorn.run(
        "job_search.web.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=os.environ.get("UVICORN_LOG_LEVEL", "info"),
    )


if __name__ == "__main__":
    main()
