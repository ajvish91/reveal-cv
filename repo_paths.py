"""Repository layout paths (shared by job search and CV generation)."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SHARED_DIR = REPO_ROOT / "shared"
JOB_SEARCH_DIR = REPO_ROOT / "job_search"
CV_GENERATION_DIR = REPO_ROOT / "cv_generation"


def load_repo_dotenv(path: Path | None = None) -> bool:
    """
    Load KEY=VALUE lines from repo .env into os.environ (does not override existing).
    Supports optional ``export `` prefix. Returns True if the file was read.
    """
    env_path = (path or REPO_ROOT / ".env").expanduser()
    if not env_path.is_file():
        return False
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
    if not os.environ.get("CURSOR_API_KEY", "").strip():
        session = os.environ.get("CURR_CURSOR_SESSION", "").strip()
        if session:
            os.environ["CURSOR_API_KEY"] = session
    return True
