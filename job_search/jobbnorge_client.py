"""HTTP client for Jobbnorge.no (public search API + PDF job text)."""
from __future__ import annotations

import io
import json
import re
from typing import Any

from pypdf import PdfReader

from job_search.deadline_utils import parse_deadline
from job_search.http_utils import http_get_bytes
from job_search.logging_config import get_logger

log = get_logger("job_search.ingest_jobbnorge")

PUBLIC_JOBS_URL = "https://publicapi.jobbnorge.no/v1/jobs"
PDF_URL_TEMPLATE = "https://www.jobbnorge.no/en/available-jobs/joblisting/pdf/{job_id}"
LISTING_URL_TEMPLATE = "https://www.jobbnorge.no/ledige-stillinger/stilling/{job_id}"
APPLY_URL_TEMPLATE = "https://jobseeker.jobbnorge.no/client/apply/{job_id}"
USER_AGENT = "job-search-automation/0.1 (personal job search; local script)"

_OPEN_DEADLINE = frozenset({"løpende", "lopende", "ongoing", "løpande"})
_US_DATE_IN_PDF_RE = re.compile(
    r"Deadline:\s*(\d{1,2})/(\d{1,2})/(\d{4})",
    re.IGNORECASE,
)


def listing_url(job_id: int | str) -> str:
    return LISTING_URL_TEMPLATE.format(job_id=int(job_id))


def apply_url(job_id: int | str) -> str:
    return APPLY_URL_TEMPLATE.format(job_id=int(job_id))


def pdf_url(job_id: int | str) -> str:
    return PDF_URL_TEMPLATE.format(job_id=int(job_id))


def normalize_api_deadline(raw: str | None) -> str | None:
    """Map Jobbnorge card deadline (e.g. ``25.09.2026``) to ISO date when possible."""
    if not raw:
        return None
    text = raw.strip()
    if text.casefold() in _OPEN_DEADLINE:
        return None
    parsed = parse_deadline(text)
    if parsed is not None:
        return parsed.isoformat()
    return text


def deadline_from_pdf_text(text: str) -> str | None:
    match = _US_DATE_IN_PDF_RE.search(text or "")
    if not match:
        return None
    month, day, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    try:
        from datetime import date

        return date(year, month, day).isoformat()
    except ValueError:
        return None


class JobbnorgeClient:
    def __init__(self, *, sleep_s: float = 0.35) -> None:
        self.sleep_s = sleep_s

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": USER_AGENT, "Accept": "application/json"}

    def fetch_job_catalog(self) -> list[dict[str, Any]]:
        body, _, _status = http_get_bytes(
            PUBLIC_JOBS_URL,
            self._headers(),
            timeout=180,
        )
        data = json.loads(body.decode("utf-8"))
        if not isinstance(data, list):
            raise RuntimeError(f"Unexpected Jobbnorge catalog payload: {type(data)!r}")
        return data

    def fetch_pdf_text(self, job_id: int | str) -> str:
        url = pdf_url(job_id)
        body, _, _status = http_get_bytes(url, {"User-Agent": USER_AGENT}, timeout=120)
        reader = PdfReader(io.BytesIO(body))
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
