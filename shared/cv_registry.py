"""Gitignored CV registry: which anonymized markdown file is active per track.

User-added files live under ``<cv-root>/user/<slug>-{industry,academic}.md``.
The registry never points at real identity data. Demo templates are read-only.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from repo_paths import SHARED_DIR

TRACKS = ("industry", "academic")
REGISTRY_FILENAME = "cv_registry.json"
USER_DIR_NAME = "user"
_PACKAGE_CV_DIR = SHARED_DIR / "cv"
_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def registry_root() -> Path:
    """Directory that holds the registry, demo templates, and ``user/`` CVs."""
    env = os.environ.get("CV_SOURCE_DIR", "").strip()
    if env:
        path = Path(env).expanduser().resolve()
        if path.is_dir():
            return path
    return _PACKAGE_CV_DIR


def registry_path(root: Path | None = None) -> Path:
    return (root or registry_root()) / REGISTRY_FILENAME


def user_dir(root: Path | None = None) -> Path:
    return (root or registry_root()) / USER_DIR_NAME


def slugify(label: str) -> str:
    text = label.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "cv"


def validate_slug(slug: str) -> str:
    cleaned = slugify(slug)
    if not _SLUG_RE.match(cleaned):
        raise ValueError(f"Invalid CV slug: {slug!r}")
    return cleaned


def load_registry(root: Path | None = None) -> dict:
    path = registry_path(root)
    if not path.is_file():
        return {"active": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"active": {}}
    if not isinstance(raw, dict):
        return {"active": {}}
    active = raw.get("active")
    if not isinstance(active, dict):
        active = {}
    return {"active": {str(k): str(v) for k, v in active.items() if v}}


def save_registry(data: dict, root: Path | None = None) -> Path:
    path = registry_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"active": dict((data.get("active") or {}))}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def is_demo_path(path: Path) -> bool:
    return path.name.endswith(".demo.md")


def user_cv_path(slug: str, track: str, root: Path | None = None) -> Path:
    if track not in TRACKS:
        raise ValueError(f"Unknown track: {track}")
    cleaned = validate_slug(slug)
    return user_dir(root) / f"{cleaned}-{track}.md"


def parse_source_id(source_id: str) -> tuple[str, str | None]:
    """Return (kind, slug_or_none). kind is demo | personal | user."""
    text = (source_id or "").strip()
    if text == "demo":
        return "demo", None
    if text == "personal":
        return "personal", None
    if text.startswith("user:"):
        slug = validate_slug(text.split(":", 1)[1])
        return "user", slug
    raise ValueError(f"Unknown CV source id: {source_id!r}")


def format_source_id(kind: str, slug: str | None = None) -> str:
    if kind == "user":
        if not slug:
            raise ValueError("user source id requires a slug")
        return f"user:{validate_slug(slug)}"
    if kind in ("demo", "personal"):
        return kind
    raise ValueError(f"Unknown kind: {kind}")


@dataclass(frozen=True)
class CvSource:
    source_id: str
    kind: str
    track: str
    path: Path
    label: str
    active: bool
    read_only: bool


def _display_name_from_markdown(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"^## Name\s*\n+([^\n#]+)", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    match = re.search(r"^# (Industry|Academic) CV\s*$", text, re.MULTILINE)
    return match.group(0).replace("# ", "").strip() if match else ""


def _personal_path(root: Path, track: str) -> Path | None:
    local = root / f"{track}.md"
    if local.is_file():
        return local
    from shared.cv_loader import resolve_cv_dir

    other = resolve_cv_dir() / f"{track}.md"
    if other.is_file() and other.resolve() != local.resolve():
        return other
    return None


def _demo_path(root: Path, track: str) -> Path | None:
    demo = root / f"{track}.demo.md"
    return demo if demo.is_file() else None


def resolve_source_path(source_id: str, track: str, root: Path | None = None) -> Path | None:
    if track not in TRACKS:
        raise ValueError(f"Unknown track: {track}")
    base = root or registry_root()
    kind, slug = parse_source_id(source_id)
    if kind == "demo":
        return _demo_path(base, track)
    if kind == "personal":
        return _personal_path(base, track)
    assert slug is not None
    path = user_cv_path(slug, track, base)
    return path if path.is_file() else None


def list_sources(track: str, root: Path | None = None) -> list[CvSource]:
    if track not in TRACKS:
        raise ValueError(f"Unknown track: {track}")
    base = root or registry_root()
    active_id = (load_registry(base).get("active") or {}).get(track, "")
    sources: list[CvSource] = []

    demo = _demo_path(base, track)
    if demo is not None:
        label = _display_name_from_markdown(demo) or "Placeholder CV"
        sources.append(
            CvSource(
                source_id="demo",
                kind="demo",
                track=track,
                path=demo,
                label=f"{label} (placeholder)",
                active=active_id == "demo",
                read_only=True,
            )
        )

    personal = _personal_path(base, track)
    if personal is not None:
        label = _display_name_from_markdown(personal) or personal.name
        sources.append(
            CvSource(
                source_id="personal",
                kind="personal",
                track=track,
                path=personal,
                label=f"{label} (local)",
                active=active_id == "personal",
                read_only=False,
            )
        )

    u_dir = user_dir(base)
    if u_dir.is_dir():
        suffix = f"-{track}.md"
        for path in sorted(u_dir.glob(f"*{suffix}")):
            slug = path.name[: -len(suffix)]
            try:
                source_id = format_source_id("user", slug)
            except ValueError:
                continue
            label = _display_name_from_markdown(path) or slug
            sources.append(
                CvSource(
                    source_id=source_id,
                    kind="user",
                    track=track,
                    path=path,
                    label=label,
                    active=active_id == source_id,
                    read_only=False,
                )
            )

    if not active_id:
        # Default precedence (personal over demo) is implied, not a stored choice.
        for src in sources:
            if src.kind == "personal":
                object.__setattr__(src, "active", True)
                break
        else:
            for src in sources:
                if src.kind == "demo":
                    object.__setattr__(src, "active", True)
                    break
    return sources


def resolve_registered_path(track: str, root: Path | None = None) -> Path | None:
    """Explicit registry selection, or None to keep loader default precedence."""
    if track not in TRACKS:
        return None
    base = root or registry_root()
    active_id = (load_registry(base).get("active") or {}).get(track, "")
    if not active_id:
        return None
    try:
        path = resolve_source_path(active_id, track, base)
    except ValueError:
        return None
    return path if path is not None and path.is_file() else None


def set_active(track: str, source_id: str | None, root: Path | None = None) -> dict:
    if track not in TRACKS:
        raise ValueError(f"Unknown track: {track}")
    base = root or registry_root()
    data = load_registry(base)
    active = dict(data.get("active") or {})
    if not source_id:
        active.pop(track, None)
    else:
        path = resolve_source_path(source_id, track, base)
        if path is None or not path.is_file():
            raise FileNotFoundError(f"CV source {source_id!r} not found for {track}")
        active[track] = source_id
    data["active"] = active
    save_registry(data, base)
    return data


def write_user_markdown(slug: str, track: str, markdown: str, root: Path | None = None) -> Path:
    """Write anonymized markdown for a user-added CV. Never writes ``*.demo.md``."""
    path = user_cv_path(slug, track, root)
    if is_demo_path(path):
        raise ValueError("Refusing to write demo templates")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown if markdown.endswith("\n") else markdown + "\n", encoding="utf-8")
    return path


def write_personal_markdown(track: str, markdown: str, root: Path | None = None) -> Path:
    """Update existing gitignored ``{track}.md`` only. Never creates demo files."""
    if track not in TRACKS:
        raise ValueError(f"Unknown track: {track}")
    base = root or registry_root()
    path = _personal_path(base, track)
    if path is None:
        raise FileNotFoundError(f"No local {track}.md to update")
    if is_demo_path(path):
        raise ValueError("Refusing to write demo templates")
    path.write_text(markdown if markdown.endswith("\n") else markdown + "\n", encoding="utf-8")
    return path
