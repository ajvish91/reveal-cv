#!/usr/bin/env python3
"""Merge YAML front matter lists into CV markdown body (languages, hobbies)."""
from __future__ import annotations

import re


def _replace_section_bullets(body: str, section_title: str, bullets: list[str]) -> str:
    """Replace bullet list under ## Section until the next ## heading."""
    if not bullets:
        return body
    block = "\n".join(f"- {line.lstrip('- ').strip()}" for line in bullets if line.strip()) + "\n"
    pattern = rf"(^## {re.escape(section_title)}\s*\n)(.*?)(?=^## |\Z)"
    if re.search(pattern, body, flags=re.MULTILINE | re.DOTALL):
        return re.sub(pattern, rf"\1{block}", body, count=1, flags=re.MULTILINE | re.DOTALL)
    return body.rstrip() + f"\n\n## {section_title}\n\n{block}"


def _language_bullets(languages: dict[str, str]) -> list[str]:
    return [f"{name} ({level})" for name, level in languages.items() if str(name).strip()]


def _hobby_bullets(hobbies: list | str) -> list[str]:
    if isinstance(hobbies, str):
        return [h.strip() for h in hobbies.split(",") if h.strip()]
    return [str(h).strip() for h in hobbies if str(h).strip()]


def enrich_body_from_front_matter(body: str, front_matter: dict) -> str:
    """Apply languages and hobbies from YAML front matter into markdown sections."""
    langs = front_matter.get("languages")
    if isinstance(langs, dict) and langs:
        body = _replace_section_bullets(body, "Languages", _language_bullets(langs))

    hobbies = front_matter.get("hobbies")
    if hobbies:
        body = _replace_section_bullets(body, "Hobbies", _hobby_bullets(hobbies))

    return body.rstrip() + "\n"


def full_cv_markdown(front_matter: dict, body: str) -> str:
    """Rebuild file text with front matter + enriched body for run sync."""
    import yaml

    fm = {k: v for k, v in front_matter.items() if not str(k).startswith("_")}
    body = enrich_body_from_front_matter(body, front_matter)
    if not fm:
        return body + "\n"
    return "---\n" + yaml.dump(fm, default_flow_style=False, sort_keys=False).rstrip() + "\n---\n\n" + body + "\n"
