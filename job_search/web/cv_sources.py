"""CV page helpers: list, load, save fake markdown; optional mapping write outside the repo."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_paths import REPO_ROOT
from shared.cv_form import (
    assemble_markdown,
    blank_form,
    mapping_from_form,
    merge_identity,
    parse_identity_and_track,
    strip_real_values,
)
from shared.cv_loader import _load_default_profiles_cached
from shared.cv_registry import (
    TRACKS,
    format_source_id,
    is_demo_path,
    list_sources,
    parse_source_id,
    registry_root,
    resolve_source_path,
    set_active,
    slugify,
    validate_slug,
    write_personal_markdown,
    write_user_markdown,
)


def _invalidate_profiles() -> None:
    _load_default_profiles_cached.cache_clear()


def sources_payload() -> dict[str, Any]:
    tracks: dict[str, Any] = {}
    for track in TRACKS:
        items = []
        for src in list_sources(track):
            items.append(
                {
                    "id": src.source_id,
                    "kind": src.kind,
                    "label": src.label,
                    "filename": src.path.name,
                    "active": src.active,
                    "read_only": src.read_only,
                }
            )
        tracks[track] = {"sources": items}
    return {"tracks": tracks}


def blank_payload() -> dict[str, Any]:
    form = blank_form()
    return {
        "source_id": None,
        "kind": "new",
        "identity": strip_real_values(form["identity"]),
        "industry": strip_real_values(form["industry"]),
        "academic": strip_real_values(form["academic"]),
        "markdown": {"industry": "", "academic": ""},
    }


def _read_track(source_id: str, track: str) -> tuple[dict[str, Any], dict[str, Any], str]:
    path = resolve_source_path(source_id, track)
    if path is None or not path.is_file():
        return {}, {}, ""
    markdown = path.read_text(encoding="utf-8")
    identity, fields = parse_identity_and_track(markdown, track)
    return identity, fields, markdown


def document_payload(source_id: str) -> dict[str, Any]:
    kind, _slug = parse_source_id(source_id)
    industry_id, industry, industry_md = _read_track(source_id, "industry")
    academic_id, academic, academic_md = _read_track(source_id, "academic")
    if not industry_md and not academic_md:
        raise FileNotFoundError(f"No CV files for {source_id}")
    identity = merge_identity(industry_id or {}, academic_id or {})
    form = blank_form()
    return {
        "source_id": source_id,
        "kind": kind,
        "identity": strip_real_values(identity or form["identity"]),
        "industry": strip_real_values(industry or form["industry"]),
        "academic": strip_real_values(academic or form["academic"]),
        "markdown": {"industry": industry_md, "academic": academic_md},
    }


def _assert_not_demo(path: Path) -> None:
    if is_demo_path(path):
        raise ValueError("Refusing to write demo templates. Save as a new CV instead.")


def save_fake_cv(
    *,
    source_id: str | None,
    slug: str | None,
    identity: dict[str, Any],
    industry: dict[str, Any] | None,
    academic: dict[str, Any] | None,
    activate: dict[str, bool] | None = None,
) -> dict[str, Any]:
    identity = strip_real_values(identity or {})
    industry = strip_real_values(industry) if industry is not None else None
    academic = strip_real_values(academic) if academic is not None else None
    if not industry and not academic:
        raise ValueError("Provide industry and/or academic fake CV fields.")

    kind = None
    user_slug = None
    if source_id:
        kind, user_slug = parse_source_id(source_id)
        if kind == "demo":
            raise ValueError("Refusing to write demo templates. Save as a new CV instead.")
    else:
        kind = "user"
        user_slug = validate_slug(slug or slugify((identity.get("name") or {}).get("fake") or "cv"))

    written: dict[str, str] = {}
    for track, fields in (("industry", industry), ("academic", academic)):
        if fields is None:
            continue
        markdown = assemble_markdown(identity, fields, track)
        if kind == "personal":
            if resolve_source_path("personal", track) is None:
                continue
            path = write_personal_markdown(track, markdown)
        else:
            assert user_slug is not None
            path = write_user_markdown(user_slug, track, markdown)
        _assert_not_demo(path)
        written[track] = path.name

    result_id = source_id if kind == "personal" else format_source_id("user", user_slug or "cv")
    for track, included in (activate or {}).items():
        if track not in TRACKS:
            continue
        if included:
            set_active(track, result_id)
        elif (load_active().get(track) == result_id):
            set_active(track, None)
    _invalidate_profiles()
    return {
        "ok": True,
        "source_id": result_id,
        "written": written,
        "active": load_active(),
    }


def load_active() -> dict[str, str]:
    from shared.cv_registry import load_registry

    return dict(load_registry().get("active") or {})


def activate_source(track: str, source_id: str | None) -> dict[str, Any]:
    set_active(track, source_id or None)
    _invalidate_profiles()
    return {"ok": True, "active": load_active()}


def mapping_path_outside_repo() -> Path:
    from cv_generation.private_cv import load_config

    cfg = load_config()
    path = cfg.mapping_file.expanduser().resolve()
    repo = REPO_ROOT.resolve()
    try:
        path.relative_to(repo)
    except ValueError:
        return path
    raise ValueError("Refusing to write the identity mapping inside the git repository.")


def save_mapping_outside_repo(mapping: dict[str, Any]) -> dict[str, Any]:
    from cv_generation.private_cv import load_raw_json, save_raw_json

    path = mapping_path_outside_repo()
    cleaned: dict[str, Any] = {}
    for key, value in (mapping or {}).items():
        if not isinstance(key, str) or not key.strip():
            continue
        if key == "_instructions" and isinstance(value, list):
            cleaned[key] = [str(item) for item in value]
            continue
        if isinstance(value, str):
            cleaned[key] = value
    if not cleaned:
        raise ValueError("Mapping JSON has no string entries to save.")
    existing = load_raw_json(path) if path.is_file() else {}
    if not isinstance(existing, dict):
        existing = {}
    merged = dict(existing)
    merged.update(cleaned)
    save_raw_json(path, merged)
    return {"ok": True, "path": str(path)}


def preview_markdown(identity: dict[str, Any], industry: dict[str, Any] | None, academic: dict[str, Any] | None) -> dict[str, str]:
    identity = strip_real_values(identity or {})
    out: dict[str, str] = {}
    if industry is not None:
        out["industry"] = assemble_markdown(identity, strip_real_values(industry), "industry")
    if academic is not None:
        out["academic"] = assemble_markdown(identity, strip_real_values(academic), "academic")
    return out


def preview_mapping(identity: dict[str, Any], industry: dict[str, Any] | None, academic: dict[str, Any] | None) -> dict[str, Any]:
    """Server-side mapping builder for tests. The UI builds JSON in the browser."""
    return mapping_from_form(identity or {}, industry, academic)
