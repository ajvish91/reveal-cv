"""Assemble and parse anonymized CV markdown from paired fake/real form fields.

Only **fake** values are written into markdown. Real values belong in the
downloadable mapping JSON and must never be persisted in the git repo.
"""
from __future__ import annotations

import re
from typing import Any

import yaml

from cv_generation.cv_private import (
    ANON_GITHUB_URL,
    ANON_GOOGLE_SCHOLAR_URL,
    ANON_LINKEDIN_URL,
    ANON_ORCID_URL,
    WORK_PERMIT_FAKE_KEYS,
)
from shared.cv_loader import parse_cv_markdown

TRACKS = ("industry", "academic")

_IDENTITY_PAIRS = (
    "name",
    "date_of_birth",
    "email",
    "phone",
    "location",
    "work_permit",
    "github_url",
    "linkedin_url",
    "scholar_url",
    "orcid_url",
)

_URL_META = {
    "github_url": ("_github_url", ANON_GITHUB_URL),
    "linkedin_url": ("_linkedin_url", ANON_LINKEDIN_URL),
    "scholar_url": ("_google_scholar_url", ANON_GOOGLE_SCHOLAR_URL),
    "orcid_url": ("_orcid_url", ANON_ORCID_URL),
}

_CONTACT_LABELS = (
    ("GitHub", "github_url"),
    ("LinkedIn", "linkedin_url"),
    ("Google Scholar", "scholar_url"),
    ("ORCID", "orcid_url"),
    ("Email", "email"),
    ("Phone", "phone"),
    ("Location", "location"),
    ("Work permit", "work_permit"),
)

_MAPPING_INSTRUCTIONS = [
    "Do NOT store this file inside the git repo or paste it to an AI agent.",
    "Keep it outside the project (Download folder or ~/private/cv/cv_identity_mapping.json).",
    "Fake keys match the anonymized markdown the tailoring pipeline uses.",
    "Apply with: ~/private/cv/cv apply <run_id>",
]


def paired(fake: str = "", real: str = "") -> dict[str, str]:
    return {"fake": fake or "", "real": real or ""}


def _as_pair(value: object) -> dict[str, str]:
    if isinstance(value, dict):
        return paired(str(value.get("fake") or ""), str(value.get("real") or ""))
    if isinstance(value, str):
        return paired(value, "")
    return paired()


def _text(value: object) -> str:
    return str(value or "").strip()


def blank_identity() -> dict[str, Any]:
    return {
        "name": paired(),
        "date_of_birth": paired(),
        "email": paired(),
        "phone": paired(),
        "location": paired(),
        "work_permit": paired(),
        "github_url": paired(ANON_GITHUB_URL),
        "linkedin_url": paired(ANON_LINKEDIN_URL),
        "scholar_url": paired(ANON_GOOGLE_SCHOLAR_URL),
        "orcid_url": paired(ANON_ORCID_URL),
        "languages": [{"name": paired(), "level": paired()}],
        "hobbies": [paired()],
        "locations_preferred": [paired()],
        "seniority_years": None,
    }


def blank_track(track: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "profile": "",
        "skills": [],
        "keywords": [],
        "experience": [
            {
                "title": "",
                "employer": paired(),
                "dates": paired(),
                "bullets": [""],
            }
        ],
        "education": [
            {
                "degree": "",
                "school": paired(),
                "years": paired(),
                "field": "",
                "thesis": paired(),
            }
        ],
        "publications": [""],
    }
    if track == "academic":
        payload["teaching"] = ""
    return payload


def blank_form() -> dict[str, Any]:
    return {
        "identity": blank_identity(),
        "industry": blank_track("industry"),
        "academic": blank_track("academic"),
    }


def strip_real_values(value: Any) -> Any:
    """Drop ``real`` keys so API save/get never round-trip identity."""
    if isinstance(value, dict):
        return {k: strip_real_values(v) for k, v in value.items() if k != "real"}
    if isinstance(value, list):
        return [strip_real_values(item) for item in value]
    return value


def _comma_list(items: object) -> list[str]:
    if items is None:
        return []
    if isinstance(items, str):
        return [part.strip() for part in items.split(",") if part.strip()]
    return [str(x).strip() for x in items if str(x).strip()]


def _yaml_front_matter(identity: dict[str, Any], track: dict[str, Any], track_name: str) -> str:
    languages: dict[str, str] = {}
    for row in identity.get("languages") or []:
        if not isinstance(row, dict):
            continue
        name = _as_pair(row.get("name")).get("fake", "").strip()
        level = _as_pair(row.get("level")).get("fake", "").strip()
        if name:
            languages[name] = level or "Fluent"
    locations = []
    for row in identity.get("locations_preferred") or []:
        fake = _as_pair(row).get("fake", "").strip()
        if fake:
            locations.append(fake)
    hobbies = []
    for row in identity.get("hobbies") or []:
        fake = _as_pair(row).get("fake", "").strip()
        if fake:
            hobbies.append(fake)
    seniority = identity.get("seniority_years")
    try:
        seniority_n = int(seniority) if seniority not in (None, "") else None
    except (TypeError, ValueError):
        seniority_n = None
    meta: dict[str, Any] = {
        "track": track_name,
        "locations_preferred": locations,
        "keywords": _comma_list(track.get("keywords")),
        "skills": _comma_list(track.get("skills")),
    }
    if seniority_n is not None:
        meta["seniority_years"] = seniority_n
    if languages:
        meta["languages"] = languages
    if hobbies:
        meta["hobbies"] = hobbies
    dumped = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
    return (
        "---\n"
        "# Anonymized CV — fake identity only. Real values belong in mapping JSON outside this repo.\n"
        f"{dumped}---\n"
    )


def _contact_lines(identity: dict[str, Any], *, academic: bool) -> list[str]:
    lines = []
    skip = set() if academic else {"scholar_url", "orcid_url"}
    for label, key in _CONTACT_LABELS:
        if key in skip:
            continue
        value = _as_pair(identity.get(key)).get("fake", "").strip()
        if value:
            lines.append(f"- {label}: {value}")
    return lines


def _language_lines(identity: dict[str, Any]) -> list[str]:
    lines = []
    for row in identity.get("languages") or []:
        if not isinstance(row, dict):
            continue
        name = _as_pair(row.get("name")).get("fake", "").strip()
        level = _as_pair(row.get("level")).get("fake", "").strip()
        if not name:
            continue
        lines.append(f"- {name} ({level})" if level else f"- {name}")
    return lines


def _hobby_lines(identity: dict[str, Any]) -> list[str]:
    lines = []
    for row in identity.get("hobbies") or []:
        fake = _as_pair(row).get("fake", "").strip()
        if fake:
            lines.append(f"- {fake}")
    return lines


def _experience_block(track: dict[str, Any]) -> str:
    parts: list[str] = []
    for role in track.get("experience") or []:
        if not isinstance(role, dict):
            continue
        title = _text(role.get("title"))
        employer = _as_pair(role.get("employer")).get("fake", "").strip()
        dates = _as_pair(role.get("dates")).get("fake", "").strip()
        bullets = [str(b).strip() for b in (role.get("bullets") or []) if str(b).strip()]
        if not (title or employer or dates or bullets):
            continue
        chunk = []
        if title:
            chunk.append(f"### {title}")
        if employer:
            chunk.append(employer)
        if dates:
            chunk.append(dates)
        if bullets:
            chunk.append("")
            chunk.extend(f"- {b}" for b in bullets)
        parts.append("\n".join(chunk))
    return "\n\n".join(parts)


def _education_block(track: dict[str, Any]) -> str:
    parts: list[str] = []
    for row in track.get("education") or []:
        if not isinstance(row, dict):
            continue
        degree = _text(row.get("degree"))
        school = _as_pair(row.get("school")).get("fake", "").strip()
        years = _as_pair(row.get("years")).get("fake", "").strip()
        field = _text(row.get("field"))
        thesis = _as_pair(row.get("thesis")).get("fake", "").strip()
        if not (degree or school or years or field or thesis):
            continue
        chunk = []
        if degree:
            chunk.append(f"### {degree}")
        if school:
            chunk.append(school)
        if years:
            chunk.append(years)
        if field:
            chunk.append(field)
        if thesis:
            chunk.append(thesis if thesis.lower().startswith("thesis:") else f"Thesis: {thesis}")
        parts.append("\n".join(chunk))
    return "\n\n".join(parts)


def _publication_block(track: dict[str, Any]) -> str:
    pubs = [str(p).strip() for p in (track.get("publications") or []) if str(p).strip()]
    return "\n".join(f"- {p.lstrip('- ').strip()}" for p in pubs)


def assemble_markdown(identity: dict[str, Any], track: dict[str, Any], track_name: str) -> str:
    """Build anonymized markdown for one track. Uses fake fields only."""
    identity = identity or {}
    track = track or {}
    name = _as_pair(identity.get("name")).get("fake", "").strip()
    dob = _as_pair(identity.get("date_of_birth")).get("fake", "").strip()
    profile = str(track.get("profile") or "").strip()
    skills = ", ".join(_comma_list(track.get("skills")))
    contact = "\n".join(_contact_lines(identity, academic=track_name == "academic"))
    languages = "\n".join(_language_lines(identity))
    hobbies = "\n".join(_hobby_lines(identity))
    experience = _experience_block(track)
    education = _education_block(track)
    publications = _publication_block(track)
    teaching = str(track.get("teaching") or "").strip()

    sections: list[str] = []
    if track_name == "academic":
        sections.append("# Academic CV")
        if profile:
            sections.extend(["## Summary", profile])
        if contact:
            sections.extend(["## Contact", contact])
        if education:
            sections.extend(["## Education", education])
        if publications:
            sections.extend(["## Research and publications", publications])
        if teaching:
            sections.extend(["## Teaching and supervision", teaching])
        if experience:
            sections.extend(["## Experience", experience])
        if languages:
            sections.extend(["## Languages", languages])
        if hobbies:
            sections.extend(["## Hobbies", hobbies])
    else:
        sections.append("# Industry CV")
        if name:
            sections.extend(["## Name", name])
        if profile:
            sections.extend(["## Profile", profile])
        if dob:
            sections.extend(["## Date of birth", dob])
        if contact:
            sections.extend(["## Contact", contact])
        if skills:
            sections.extend(["## Skills", skills])
        if languages:
            sections.extend(["## Languages", languages])
        if experience:
            sections.extend(["## Experience", experience])
        if education:
            sections.extend(["## Education", education])
        if publications:
            sections.extend(["## Selected Publications", publications])
        if hobbies:
            sections.extend(["## Hobbies", hobbies])

    body = "\n\n".join(sections).strip() + "\n"
    return _yaml_front_matter(identity, track, track_name) + "\n" + body


def _split_sections(body: str) -> dict[str, str]:
    parts = re.split(r"^## ", body, flags=re.MULTILINE)
    out: dict[str, str] = {}
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        title = lines[0].strip()
        out[title] = "\n".join(lines[1:]).strip()
    return out


def _parse_contact(block: str) -> dict[str, str]:
    found: dict[str, str] = {}
    label_to_key = {label.lower(): key for label, key in _CONTACT_LABELS}
    for line in block.splitlines():
        match = re.match(r"^-\s*([^:]+):\s*(.*)$", line.strip())
        if not match:
            continue
        key = label_to_key.get(match.group(1).strip().lower())
        if key:
            found[key] = match.group(2).strip()
    return found


def _parse_language_lines(block: str) -> list[dict[str, Any]]:
    rows = []
    for line in block.splitlines():
        text = line.strip()
        if not text.startswith("-"):
            continue
        text = text[1:].strip()
        match = re.match(r"^(.+?)\s*\((.+)\)\s*$", text)
        if match:
            rows.append({"name": paired(match.group(1).strip()), "level": paired(match.group(2).strip())})
        elif text:
            rows.append({"name": paired(text), "level": paired()})
    return rows or [{"name": paired(), "level": paired()}]


def _parse_bullet_lines(block: str) -> list[str]:
    items = []
    for line in block.splitlines():
        text = line.strip()
        if text.startswith("-"):
            items.append(text[1:].strip())
        elif text:
            items.append(text)
    return items


def _parse_experience(block: str) -> list[dict[str, Any]]:
    if not block.strip():
        return blank_track("industry")["experience"]
    chunks = re.split(r"^### ", block, flags=re.MULTILINE)
    roles = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = chunk.splitlines()
        title = lines[0].strip()
        rest = lines[1:]
        bullets: list[str] = []
        meta: list[str] = []
        in_bullets = False
        for line in rest:
            stripped = line.strip()
            if stripped.startswith("-"):
                in_bullets = True
                bullets.append(stripped[1:].strip())
            elif in_bullets and stripped:
                bullets.append(stripped)
            elif stripped:
                meta.append(stripped)
        employer = meta[0] if meta else ""
        dates = meta[1] if len(meta) > 1 else ""
        roles.append(
            {
                "title": title,
                "employer": paired(employer),
                "dates": paired(dates),
                "bullets": bullets or [""],
            }
        )
    return roles or blank_track("industry")["experience"]


def _parse_education_structured(block: str) -> list[dict[str, Any]]:
    chunks = re.split(r"^### ", block, flags=re.MULTILINE)
    rows = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            continue
        degree = lines[0]
        school = years = field = thesis = ""
        extra = lines[1:]
        if extra:
            school = extra[0]
        if len(extra) > 1:
            years = extra[1]
        for item in extra[2:]:
            if item.lower().startswith("thesis:"):
                thesis = item.split(":", 1)[1].strip()
            elif not field:
                field = item
        rows.append(
            {
                "degree": degree,
                "school": paired(school),
                "years": paired(years),
                "field": field,
                "thesis": paired(thesis),
            }
        )
    return rows


def _parse_education_compact(block: str) -> list[dict[str, Any]]:
    rows = []
    for line in block.splitlines():
        text = line.strip()
        if not text.startswith("-"):
            continue
        text = text[1:].strip()
        match = re.match(
            r"\*\*(.+?)\*\*\s+[—–-]+\s+(.+?)(?:\.\s*Thesis:\s*\*?(.+?)\*?)?\.?\s*$",
            text,
        )
        if not match:
            rows.append(
                {
                    "degree": text,
                    "school": paired(),
                    "years": paired(),
                    "field": "",
                    "thesis": paired(),
                }
            )
            continue
        thesis = (match.group(3) or "").strip().strip("*").strip()
        rows.append(
            {
                "degree": match.group(1).strip(),
                "school": paired(match.group(2).strip().rstrip(".")),
                "years": paired(),
                "field": "",
                "thesis": paired(thesis),
            }
        )
    return rows


def _parse_education(block: str) -> list[dict[str, Any]]:
    if not block.strip():
        return blank_track("industry")["education"]
    if re.search(r"^### ", block, re.MULTILINE):
        rows = _parse_education_structured(block)
    else:
        rows = _parse_education_compact(block)
    return rows or blank_track("industry")["education"]


def parse_identity_and_track(markdown: str, track_name: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse fake fields from anonymized markdown. Real columns stay empty."""
    front, body = parse_cv_markdown(markdown)
    identity = blank_identity()
    track = blank_track(track_name)
    sections = _split_sections(body)

    name_block = sections.get("Name", "").strip()
    if name_block:
        identity["name"] = paired(name_block.splitlines()[0].strip())
    if sections.get("Date of birth"):
        identity["date_of_birth"] = paired(sections["Date of birth"].splitlines()[0].strip())

    contact = _parse_contact(sections.get("Contact", ""))
    for key, value in contact.items():
        identity[key] = paired(value)

    if "Languages" in sections:
        identity["languages"] = _parse_language_lines(sections["Languages"])
    elif isinstance(front.get("languages"), dict):
        identity["languages"] = [
            {"name": paired(str(k)), "level": paired(str(v))}
            for k, v in front["languages"].items()
        ]

    hobby_block = sections.get("Hobbies", "")
    if hobby_block:
        identity["hobbies"] = [paired(item) for item in _parse_bullet_lines(hobby_block)] or [paired()]
    elif isinstance(front.get("hobbies"), list):
        identity["hobbies"] = [paired(str(x)) for x in front["hobbies"]] or [paired()]

    locs = front.get("locations_preferred") or []
    if isinstance(locs, str):
        locs = [locs]
    identity["locations_preferred"] = [paired(str(x)) for x in locs] or [paired()]
    if front.get("seniority_years") is not None:
        try:
            identity["seniority_years"] = int(front["seniority_years"])
        except (TypeError, ValueError):
            identity["seniority_years"] = None

    track["profile"] = (sections.get("Profile") or sections.get("Summary") or "").strip()
    skills_block = sections.get("Skills", "")
    track["skills"] = _comma_list(skills_block.replace("\n", ", ") if skills_block else front.get("skills"))
    track["keywords"] = _comma_list(front.get("keywords"))
    track["experience"] = _parse_experience(sections.get("Experience", ""))
    track["education"] = _parse_education(sections.get("Education", ""))
    pub_block = sections.get("Selected Publications") or sections.get("Research and publications") or ""
    track["publications"] = _parse_bullet_lines(pub_block) or [""]
    if track_name == "academic":
        track["teaching"] = sections.get("Teaching and supervision", "").strip()
    return identity, track


def merge_identity(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    """Fill empty fake identity fields from a second track."""
    merged = blank_identity()
    for key in _IDENTITY_PAIRS:
        first = _as_pair(primary.get(key))
        second = _as_pair(secondary.get(key))
        merged[key] = paired(first["fake"] or second["fake"], first["real"] or second["real"])

    def _list_or_other(key: str, filled) -> list:
        first_list = primary.get(key) or []
        second_list = secondary.get(key) or []
        if any(filled(item) for item in first_list):
            return first_list
        if any(filled(item) for item in second_list):
            return second_list
        return first_list or second_list or merged[key]

    merged["languages"] = _list_or_other(
        "languages",
        lambda row: bool(_as_pair((row or {}).get("name") if isinstance(row, dict) else {}).get("fake")),
    )
    merged["hobbies"] = _list_or_other("hobbies", lambda row: bool(_as_pair(row).get("fake")))
    merged["locations_preferred"] = _list_or_other(
        "locations_preferred", lambda row: bool(_as_pair(row).get("fake"))
    )
    merged["seniority_years"] = primary.get("seniority_years")
    if merged["seniority_years"] in (None, ""):
        merged["seniority_years"] = secondary.get("seniority_years")
    return merged


def mapping_from_form(identity: dict[str, Any], industry: dict[str, Any] | None, academic: dict[str, Any] | None) -> dict[str, Any]:
    """Build fake→real mapping JSON. Empty or identical pairs are omitted."""
    out: dict[str, Any] = {"_instructions": list(_MAPPING_INSTRUCTIONS)}

    def add(fake: str, real: str) -> None:
        fake_s = (fake or "").strip()
        real_s = (real or "").strip()
        if fake_s and real_s and fake_s != real_s:
            out[fake_s] = real_s

    ident = identity or {}
    for key in _IDENTITY_PAIRS:
        pair = _as_pair(ident.get(key))
        if key in _URL_META:
            meta_key, anon = _URL_META[key]
            real = pair["real"].strip()
            if real.startswith(("http://", "https://")) and not real.startswith("REPLACE_WITH_"):
                out[meta_key] = real
            add(pair["fake"] or anon, real)
            continue
        add(pair["fake"], pair["real"])

    work_permit = _as_pair(ident.get("work_permit"))
    if work_permit["real"].strip():
        for fake in WORK_PERMIT_FAKE_KEYS:
            add(fake, work_permit["real"])

    for row in ident.get("languages") or []:
        if not isinstance(row, dict):
            continue
        name = _as_pair(row.get("name"))
        level = _as_pair(row.get("level"))
        add(name["fake"], name["real"])
        fake_line = ""
        if name["fake"]:
            fake_line = f"- {name['fake']}" + (f" ({level['fake']})" if level["fake"] else "")
        real_line = ""
        if name["real"] or level["real"]:
            real_name = name["real"] or name["fake"]
            real_level = level["real"] or level["fake"]
            real_line = f"- {real_name}" + (f" ({real_level})" if real_level else "")
        add(fake_line, real_line)

    for row in ident.get("hobbies") or []:
        pair = _as_pair(row)
        add(pair["fake"], pair["real"])
        add(f"- {pair['fake']}" if pair["fake"] else "", f"- {pair['real']}" if pair["real"] else "")

    for row in ident.get("locations_preferred") or []:
        pair = _as_pair(row)
        add(pair["fake"], pair["real"])

    for track in (industry, academic):
        if not track:
            continue
        for role in track.get("experience") or []:
            if not isinstance(role, dict):
                continue
            add(_as_pair(role.get("employer"))["fake"], _as_pair(role.get("employer"))["real"])
            add(_as_pair(role.get("dates"))["fake"], _as_pair(role.get("dates"))["real"])
        for row in track.get("education") or []:
            if not isinstance(row, dict):
                continue
            add(_as_pair(row.get("school"))["fake"], _as_pair(row.get("school"))["real"])
            add(_as_pair(row.get("years"))["fake"], _as_pair(row.get("years"))["real"])
            add(_as_pair(row.get("thesis"))["fake"], _as_pair(row.get("thesis"))["real"])
    return out
