"""Central logging configuration for the job_search package."""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_LOG_PATH = PROJECT_ROOT / "data" / "job_search.log"

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

_CONFIGURED = False


def _resolve_level(level: str | int) -> int:
    env = os.environ.get("JOB_SEARCH_LOG_LEVEL", "").strip().upper()
    if env:
        resolved = getattr(logging, env, None)
        if isinstance(resolved, int):
            return resolved
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        resolved = getattr(logging, level.upper(), None)
        if isinstance(resolved, int):
            return resolved
    return logging.INFO


def configure_logging(
    level: str | int = logging.INFO,
    log_file: str | Path | None = None,
    *,
    max_bytes: int = 2_000_000,
    backup_count: int = 3,
    console: bool = True,
) -> Path:
    """Configure the ``job_search`` logger tree (file + optional stderr)."""
    global _CONFIGURED

    log_path = Path(log_file).expanduser() if log_file else DEFAULT_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)

    resolved_level = _resolve_level(level)
    formatter = logging.Formatter(LOG_FORMAT)

    root = logging.getLogger("job_search")
    if _CONFIGURED:
        for handler in list(root.handlers):
            root.removeHandler(handler)
            handler.close()
    root.setLevel(resolved_level)
    root.propagate = False

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(resolved_level)
    root.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.setLevel(resolved_level)
        root.addHandler(stream_handler)

    _CONFIGURED = True
    root.debug("logging configured level=%s file=%s", logging.getLevelName(resolved_level), log_path)
    return log_path


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the ``job_search`` namespace."""
    if not name.startswith("job_search"):
        name = f"job_search.{name}"
    return logging.getLogger(name)


def log_json_summary(logger: logging.Logger, label: str, payload: dict) -> None:
    """Log an ingest/score summary dict (also printed to stdout by callers)."""
    import json

    try:
        text = json.dumps(payload, ensure_ascii=False)
    except (TypeError, ValueError):
        text = str(payload)
    logger.info("%s %s", label, text)


def tail_log_file(log_file: Path | None = None, *, lines: int = 50) -> str:
    """Return the last *lines* from the job search log (read-only)."""
    path = Path(log_file).expanduser() if log_file else DEFAULT_LOG_PATH
    if not path.is_file():
        return ""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    rows = content.splitlines()
    if len(rows) <= lines:
        return content
    return "\n".join(rows[-lines:])
