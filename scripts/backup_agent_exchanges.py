#!/usr/bin/env python3
"""Copy Cursor agent transcripts into a local gitignored review pack and index them.

Source (Cursor project store, not git):
  ~/.cursor/projects/.../agent-transcripts/

Destination (this repo, gitignored):
  review_pack/agent-transcripts/
  review_pack/transcript_index.json
  review_pack/transcript_index.md
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from repo_paths import REPO_ROOT


def _default_source() -> Path:
    projects = Path.home() / ".cursor" / "projects"
    matches = sorted(projects.glob("*-job-search-automation/agent-transcripts"))
    return matches[0] if matches else projects / "agent-transcripts"


DEFAULT_SOURCE = _default_source()
PACK = REPO_ROOT / "review_pack"
DEST = PACK / "agent-transcripts"
INDEX_JSON = PACK / "transcript_index.json"
INDEX_MD = PACK / "transcript_index.md"


def _text_from_content(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict):
            t = item.get("text") or item.get("content") or ""
            if isinstance(t, str):
                parts.append(t)
        elif isinstance(item, str):
            parts.append(item)
    return "\n".join(parts)


def first_user_query(jsonl_path: Path, max_chars: int = 240) -> str:
    try:
        with jsonl_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                role = obj.get("role") or ""
                msg = obj.get("message") or {}
                if role != "user" and not (isinstance(msg, dict) and msg.get("role") == "user"):
                    continue
                text = _text_from_content(msg.get("content") if isinstance(msg, dict) else "")
                text = " ".join(text.split())
                if len(text) > max_chars:
                    return text[: max_chars - 1] + "…"
                return text
    except OSError:
        return ""
    return ""


def count_lines(path: Path) -> int:
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def index_transcripts(root: Path) -> list[dict]:
    rows: list[dict] = []
    for jsonl in sorted(root.rglob("*.jsonl")):
        rel = jsonl.relative_to(root).as_posix()
        stat = jsonl.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        rows.append(
            {
                "id": jsonl.stem,
                "path": rel,
                "bytes": stat.st_size,
                "messages_approx": count_lines(jsonl),
                "mtime_utc": mtime.isoformat(timespec="seconds"),
                "first_user_query": first_user_query(jsonl),
            }
        )
    rows.sort(key=lambda r: r["mtime_utc"], reverse=True)
    return rows


def write_index_md(rows: list[dict], dest: Path, source: Path) -> None:
    lines = [
        "# Agent transcript index",
        "",
        "Local backup only. Contains chat text that may include application details.",
        "Do not commit this file or `review_pack/agent-transcripts/`.",
        "",
        f"- Source: `{source}`",
        f"- Copy: `{dest}`",
        f"- Generated: `{datetime.now(timezone.utc).isoformat(timespec='seconds')}`",
        f"- Conversations: **{len(rows)}**",
        "",
        "| When (UTC) | ID | ~msgs | First user message |",
        "|---|---|---:|---|",
    ]
    for row in rows:
        q = row["first_user_query"].replace("|", "\\|")
        lines.append(
            f"| {row['mtime_utc']} | `{row['id']}` | {row['messages_approx']} | {q} |"
        )
    INDEX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--skip-copy", action="store_true", help="Rebuild index only")
    args = parser.parse_args()
    source: Path = args.source.expanduser().resolve()
    if not source.is_dir():
        print(f"source not found: {source}", file=sys.stderr)
        return 1

    PACK.mkdir(parents=True, exist_ok=True)
    if not args.skip_copy:
        if DEST.exists():
            shutil.rmtree(DEST)
        print(f"copying {source} -> {DEST}")
        shutil.copytree(source, DEST)

    rows = index_transcripts(DEST if DEST.is_dir() else source)
    INDEX_JSON.write_text(json.dumps({"source": str(source), "copy": str(DEST), "count": len(rows), "transcripts": rows}, indent=2) + "\n", encoding="utf-8")
    write_index_md(rows, DEST, source)
    print(f"indexed {len(rows)} transcripts")
    print(f"  {INDEX_MD}")
    print(f"  {INDEX_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
