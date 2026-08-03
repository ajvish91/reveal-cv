"""Cross-source job deduplication (NAV Arbeidsplassen + FINN.no)."""
from __future__ import annotations

import re
from typing import Any

import pandas as pd

# Prefer NAV for official application URLs when the same role appears on both sites.
SOURCE_PRIORITY: tuple[str, ...] = ("nav_arbeidsplassen", "finn_no")


def normalize_text(value: str | None) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    s = (value or "").strip().casefold()
    s = re.sub(r"[^\w\s]+", " ", s, flags=re.UNICODE)
    return re.sub(r"\s+", " ", s).strip()


def dedup_key(employer_name: str | None, title: str | None) -> str:
    return f"{normalize_text(employer_name)}|{normalize_text(title)}"


def _source_rank(source: str) -> int:
    try:
        return SOURCE_PRIORITY.index(source)
    except ValueError:
        return len(SOURCE_PRIORITY)


def _row_link(row: pd.Series) -> str:
    for col in ("application_url", "link"):
        val = row.get(col)
        if val is not None and not (isinstance(val, float) and pd.isna(val)):
            text = str(val).strip()
            if text:
                return text
    return ""


def _pick_primary_index(group: pd.DataFrame) -> int:
    """Highest score wins; tie-break toward NAV."""
    ordered = group.sort_values(
        by=["score_total", "score_base"],
        ascending=[False, False],
    )
    top_score = ordered.iloc[0]["score_total"]
    tied = ordered[ordered["score_total"] == top_score]
    for src in SOURCE_PRIORITY:
        matches = tied[tied["source"] == src]
        if not matches.empty:
            return int(matches.index[0])
    return int(ordered.index[0])


def _merge_duplicate_fields(group: pd.DataFrame, primary_idx: int) -> dict[str, Any]:
    primary = group.loc[primary_idx]
    sources = sorted(group["source"].unique(), key=_source_rank)
    alt_notes: list[str] = []

    nav_rows = group[group["source"] == "nav_arbeidsplassen"]
    nav_apply = ""
    nav_link = ""
    if not nav_rows.empty:
        nav = nav_rows.iloc[0]
        nav_apply = _row_link(nav)
        nav_link = str(nav.get("link") or "").strip()

    for idx, row in group.iterrows():
        if idx == primary_idx:
            continue
        link = _row_link(row)
        label = str(row.get("source") or "unknown")
        alt_notes.append(f"{label}: {link or row.get('uuid', '')}")

    application_url = primary.get("application_url")
    link = primary.get("link")
    if not nav_rows.empty:
        if nav_apply:
            application_url = nav_apply
        if str(primary.get("source") or "") == "finn_no" and nav_link:
            alt_notes.insert(0, f"nav listing: {nav_link}")

    duplicate_note = "; ".join(alt_notes) if alt_notes else None
    return {
        "sources": ", ".join(sources),
        "application_url": application_url,
        "link": link,
        "duplicate_note": duplicate_note,
    }


def dedupe_jobs_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Collapse rows that share the same normalized employer + title.

    Keeps the highest-scoring row (NAV wins ties). When duplicates exist, prefers
  NAV ``application_url`` and records alternate links in ``duplicate_note``.
    """
    if df.empty:
        return df

    work = df.copy()
    work["_dedup_key"] = work.apply(
        lambda r: dedup_key(r.get("employer_name"), r.get("title")),
        axis=1,
    )

    rows: list[pd.Series] = []
    for _key, group in work.groupby("_dedup_key", sort=False):
        if len(group) == 1:
            row = group.iloc[0].copy()
            row["sources"] = row.get("source")
            row["duplicate_note"] = None
            rows.append(row)
            continue

        primary_idx = _pick_primary_index(group)
        merged = _merge_duplicate_fields(group, primary_idx)
        row = group.loc[primary_idx].copy()
        for field, value in merged.items():
            row[field] = value
        rows.append(row)

    out = pd.DataFrame(rows).drop(columns=["_dedup_key"], errors="ignore")
    return out.sort_values(
        by=["score_total", "score_base"],
        ascending=[False, False],
    ).reset_index(drop=True)
