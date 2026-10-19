"""FINN application deadline helpers shared by ingest and refresh."""
from __future__ import annotations

from typing import Any

from job_search.deadline_utils import coerce_expires_value, is_expired
from job_search.finn_job_client import FINN_EXPIRED_SENTINEL

SOURCE = "finn_no"


def expires_and_status_from_finn_detail(detail: dict[str, Any]) -> tuple[str | None, str]:
    """Return ``(expires, status)`` from a FINN detail payload.

    FINN often shows ``Fristen er utløpt`` with Søknadsfrist ``Snarest`` (no date).
    In that case we store ``FINN_EXPIRED_SENTINEL`` so hide-expired and ACTIVE
    filters work even without a calendar deadline.
    """
    expires = coerce_expires_value(detail.get("validThrough"))
    listing_expired = bool(detail.get("listingExpired"))
    if listing_expired:
        # Non-dated text like "Snarest" must not block the sentinel.
        if not is_expired(expires):
            expires = FINN_EXPIRED_SENTINEL
        return expires, "INACTIVE"
    if is_expired(expires):
        return expires, "INACTIVE"
    return expires, "ACTIVE"


def apply_expires_update(
    conn,
    *,
    uuid: str,
    source: str = SOURCE,
    expires: str | None,
    status: str,
    fetched_at: str | None = None,
) -> None:
    """Persist deadline/status for one posting."""
    from job_search.job_db import utc_now_iso

    conn.execute(
        """
        UPDATE job_postings
        SET expires = ?, status = ?, fetched_at = ?
        WHERE uuid = ? AND source = ?
        """,
        (expires, status, fetched_at or utc_now_iso(), uuid, source),
    )
    conn.commit()
