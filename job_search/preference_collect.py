"""Collect preference labels from applications for later score demotion.

This module only gathers and persists signals from Skip/Reject vs positive
statuses. It does not change scoring yet.
"""
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

from job_search.job_db import DEFAULT_DB_PATH, PROJECT_ROOT

NEGATIVE_STATUSES = frozenset({"skipped", "rejected"})
POSITIVE_STATUSES = frozenset(
    {"interested", "drafted", "applied", "interview", "offer"}
)
IGNORED_STATUSES = frozenset({"withdrawn"})

LabelPolarity = Literal["negative", "positive", "ignored"]

DEFAULT_PREFERENCE_PATH = PROJECT_ROOT / "data" / "preference_features.json"

_TOKEN_RE = re.compile(r"[a-z0-9æøåäöü]+", re.IGNORECASE)

# Very common Norwegian/English function words — not useful as preference stems.
_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "av",
        "be",
        "by",
        "de",
        "den",
        "det",
        "eller",
        "en",
        "et",
        "for",
        "fra",
        "i",
        "in",
        "is",
        "med",
        "og",
        "of",
        "on",
        "or",
        "på",
        "som",
        "the",
        "til",
        "to",
        "with",
        "og",
        "vi",
        "vår",
        "er",
        "om",
        "job",
        "stilling",
        "søker",
        "soker",
    }
)


@dataclass(frozen=True)
class LabeledJob:
    uuid: str
    source: str
    track: str
    status: str
    polarity: LabelPolarity
    title: str | None
    employer_name: str | None
    description_text: str | None
    matched_keywords: str | None
    matched_skills: str | None
    score_total: float | None
    updated_at: str | None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def polarity_for_status(status: str | None) -> LabelPolarity | None:
    """Map application status to training polarity, or None if unknown."""
    s = (status or "").strip().casefold()
    if s in NEGATIVE_STATUSES:
        return "negative"
    if s in POSITIVE_STATUSES:
        return "positive"
    if s in IGNORED_STATUSES:
        return "ignored"
    return None


def tokenize_text(text: str | None, *, min_len: int = 3) -> list[str]:
    """Lowercased word tokens suitable as preference stems."""
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for match in _TOKEN_RE.finditer(text):
        tok = match.group(0).casefold()
        if len(tok) < min_len or tok in _STOPWORDS:
            continue
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def normalize_employer(name: str | None) -> str | None:
    s = (name or "").strip().casefold()
    if not s:
        return None
    for suffix in (
        " as",
        " asa",
        " ans",
        " da",
        " norge",
        " norway",
    ):
        if s.endswith(suffix):
            s = s[: -len(suffix)].strip()
    return s or None


def split_csv_terms(value: str | None) -> list[str]:
    if not value:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in value.split(","):
        term = part.strip().casefold()
        if not term or term in seen:
            continue
        seen.add(term)
        out.append(term)
    return out


def load_labeled_jobs(
    conn: sqlite3.Connection,
    *,
    track: str | None = None,
) -> list[LabeledJob]:
    """Load application rows joined to postings (and optional scores)."""
    clauses = ["1=1"]
    params: list[Any] = []
    if track:
        clauses.append("a.track = ?")
        params.append(track)
    where = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT
            a.uuid,
            a.source,
            a.track,
            a.status,
            a.updated_at,
            j.title,
            j.employer_name,
            j.description_text,
            s.matched_keywords,
            s.matched_skills,
            s.score_total
        FROM applications a
        LEFT JOIN job_postings j
            ON j.uuid = a.uuid AND j.source = a.source
        LEFT JOIN job_scores s
            ON s.uuid = a.uuid AND s.source = a.source AND s.track = a.track
        WHERE {where}
        ORDER BY a.updated_at DESC
        """,
        params,
    ).fetchall()

    labeled: list[LabeledJob] = []
    for row in rows:
        polarity = polarity_for_status(row["status"])
        if polarity is None:
            continue
        score = row["score_total"]
        labeled.append(
            LabeledJob(
                uuid=str(row["uuid"]),
                source=str(row["source"]),
                track=str(row["track"]),
                status=str(row["status"]),
                polarity=polarity,
                title=row["title"],
                employer_name=row["employer_name"],
                description_text=row["description_text"],
                matched_keywords=row["matched_keywords"],
                matched_skills=row["matched_skills"],
                score_total=float(score) if score is not None else None,
                updated_at=row["updated_at"],
            )
        )
    return labeled


def _count_features(
    jobs: Iterable[LabeledJob],
    *,
    extractor,
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for job in jobs:
        for term in extractor(job):
            counts[term] += 1
    return counts


def _title_tokens(job: LabeledJob) -> list[str]:
    return tokenize_text(job.title)


def _employer_tokens(job: LabeledJob) -> list[str]:
    emp = normalize_employer(job.employer_name)
    return [emp] if emp else []


def _matched_tokens(job: LabeledJob) -> list[str]:
    return split_csv_terms(job.matched_keywords) + split_csv_terms(job.matched_skills)


def contrast_terms(
    neg_counts: Counter[str],
    pos_counts: Counter[str],
    *,
    min_neg: int = 1,
    min_pos: int = 1,
    limit: int = 40,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Rank terms that skew negative or positive.

    ``contrast`` is ``neg - pos`` (negative list) or ``pos - neg`` (positive list).
    """
    all_terms = set(neg_counts) | set(pos_counts)
    neg_rows: list[dict[str, Any]] = []
    pos_rows: list[dict[str, Any]] = []
    for term in all_terms:
        n = int(neg_counts.get(term, 0))
        p = int(pos_counts.get(term, 0))
        if n >= min_neg and n > p:
            neg_rows.append(
                {
                    "term": term,
                    "neg": n,
                    "pos": p,
                    "contrast": float(n - p),
                }
            )
        if p >= min_pos and p > n:
            pos_rows.append(
                {
                    "term": term,
                    "neg": n,
                    "pos": p,
                    "contrast": float(p - n),
                }
            )
    neg_rows.sort(key=lambda r: (-r["contrast"], -r["neg"], r["term"]))
    pos_rows.sort(key=lambda r: (-r["contrast"], -r["pos"], r["term"]))
    return neg_rows[:limit], pos_rows[:limit]


def _example_payload(job: LabeledJob) -> dict[str, Any]:
    return {
        "uuid": job.uuid,
        "source": job.source,
        "track": job.track,
        "status": job.status,
        "title": (job.title or "")[:120],
        "employer_name": (job.employer_name or "")[:80],
        "score_total": job.score_total,
        "updated_at": job.updated_at,
    }


def build_preference_collection(
    conn: sqlite3.Connection,
    *,
    track: str | None = None,
    example_limit: int = 25,
    term_limit: int = 40,
    min_neg: int = 1,
    min_pos: int = 1,
) -> dict[str, Any]:
    """Build a serializable preference feature snapshot from labeled applications."""
    jobs = load_labeled_jobs(conn, track=track)
    negatives = [j for j in jobs if j.polarity == "negative"]
    positives = [j for j in jobs if j.polarity == "positive"]
    ignored = [j for j in jobs if j.polarity == "ignored"]

    neg_titles = _count_features(negatives, extractor=_title_tokens)
    pos_titles = _count_features(positives, extractor=_title_tokens)
    neg_emps = _count_features(negatives, extractor=_employer_tokens)
    pos_emps = _count_features(positives, extractor=_employer_tokens)
    neg_matched = _count_features(negatives, extractor=_matched_tokens)
    pos_matched = _count_features(positives, extractor=_matched_tokens)

    title_neg, title_pos = contrast_terms(
        neg_titles, pos_titles, min_neg=min_neg, min_pos=min_pos, limit=term_limit
    )
    emp_neg, emp_pos = contrast_terms(
        neg_emps, pos_emps, min_neg=min_neg, min_pos=min_pos, limit=term_limit
    )
    match_neg, match_pos = contrast_terms(
        neg_matched, pos_matched, min_neg=min_neg, min_pos=min_pos, limit=term_limit
    )

    by_track: Counter[str] = Counter(j.track for j in jobs)
    by_status: Counter[str] = Counter(j.status for j in jobs)

    return {
        "schema_version": 1,
        "collected_at": utc_now_iso(),
        "track": track or "all",
        "label_counts": {
            "negative": len(negatives),
            "positive": len(positives),
            "ignored": len(ignored),
            "total_labeled": len(jobs),
        },
        "status_counts": dict(sorted(by_status.items())),
        "track_counts": dict(sorted(by_track.items())),
        "negative_statuses": sorted(NEGATIVE_STATUSES),
        "positive_statuses": sorted(POSITIVE_STATUSES),
        "title_stems": {"negative": title_neg, "positive": title_pos},
        "employers": {"negative": emp_neg, "positive": emp_pos},
        "matched_terms": {"negative": match_neg, "positive": match_pos},
        "examples": {
            "negative": [_example_payload(j) for j in negatives[:example_limit]],
            "positive": [_example_payload(j) for j in positives[:example_limit]],
        },
    }


def default_preference_path() -> Path:
    return DEFAULT_PREFERENCE_PATH


def save_preference_collection(path: Path, collection: dict[str, Any]) -> Path:
    """Write preference snapshot JSON (creates parent dirs)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(collection, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_preference_collection(path: Path) -> dict[str, Any] | None:
    """Load preference snapshot or return None if missing/invalid."""
    path = Path(path)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def collect_and_save(
    conn: sqlite3.Connection,
    *,
    track: str | None = None,
    path: Path | None = None,
    example_limit: int = 25,
    term_limit: int = 40,
    min_neg: int = 1,
    min_pos: int = 1,
) -> tuple[dict[str, Any], Path]:
    """Build collection and write to ``path`` (default under job_search/data/)."""
    collection = build_preference_collection(
        conn,
        track=track,
        example_limit=example_limit,
        term_limit=term_limit,
        min_neg=min_neg,
        min_pos=min_pos,
    )
    out = Path(path) if path else default_preference_path()
    # When track-scoped, write alongside default with track suffix.
    if track and path is None:
        out = PROJECT_ROOT / "data" / f"preference_features_{track}.json"
    save_preference_collection(out, collection)
    return collection, out
