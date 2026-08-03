"""HTTP client for NAV PAM stilling feed (public JWT). Uses certifi for TLS roots."""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.request
from email.utils import format_datetime
from datetime import datetime, timedelta, timezone
from typing import Any

import certifi

FEED_ORIGIN = "https://pam-stilling-feed.nav.no"
PUBLIC_TOKEN_URL = f"{FEED_ORIGIN}/api/publicToken"
RETRYABLE_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _should_retry_http_error(exc: urllib.error.HTTPError) -> bool:
    return exc.code in RETRYABLE_HTTP_CODES


def http_get_json(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    max_attempts: int = 3,
    retry_backoff_s: float = 1.0,
) -> tuple[dict[str, Any], dict[str, str]]:
    req = urllib.request.Request(url, headers=headers or {})
    last_error: Exception | None = None
    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            with urllib.request.urlopen(req, context=_ssl_context(), timeout=120) as resp:
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.read().decode("utf-8")
                if resp.status == 304 or not body.strip():
                    return {}, hdrs
                return json.loads(body), hdrs
        except urllib.error.HTTPError as e:
            if e.code == 304:
                return {}, {k.lower(): v for k, v in e.headers.items()}
            err = e.read().decode("utf-8", errors="replace")
            if _should_retry_http_error(e) and attempt < max_attempts:
                time.sleep(retry_backoff_s * attempt)
                last_error = e
                continue
            raise RuntimeError(f"HTTP {e.code} {url}: {err[:500]}") from e
        except urllib.error.URLError as e:
            last_error = e
            if attempt >= max_attempts:
                raise RuntimeError(f"Request failed for {url}: {e.reason}") from e
            time.sleep(retry_backoff_s * attempt)
    if last_error is not None:
        raise RuntimeError(f"Request failed for {url}: {last_error}")
    raise RuntimeError(f"Request failed for {url}")


def fetch_public_token() -> str:
    req = urllib.request.Request(PUBLIC_TOKEN_URL)
    with urllib.request.urlopen(req, context=_ssl_context(), timeout=60) as resp:
        text = resp.read().decode("utf-8")
    text = text.strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        raise RuntimeError("Empty public token response")
    token = lines[-1]
    if not re.match(r"^[\w\-]+\.[\w\-]+\.[\w\-]+$", token):
        raise RuntimeError(f"Does not look like a JWT: {token[:40]}…")
    return token


class NavFeedSession:
    def __init__(self) -> None:
        self._token = fetch_public_token()

    def refresh_token(self) -> None:
        self._token = fetch_public_token()

    def _request_json(
        self,
        url: str,
        headers: dict[str, str] | None = None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        req_headers = dict(headers or {})
        if self._token:
            req_headers["Authorization"] = f"Bearer {self._token}"
        try:
            return http_get_json(url, req_headers)
        except RuntimeError as e:
            if "HTTP 401 " not in str(e) and "HTTP 403 " not in str(e):
                raise
        self.refresh_token()
        if self._token:
            req_headers["Authorization"] = f"Bearer {self._token}"
        return http_get_json(url, req_headers)

    def fetch_feed_page(
        self,
        path: str,
        *,
        if_modified_since: datetime | None = None,
        etag: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        url = FEED_ORIGIN + path if path.startswith("/") else FEED_ORIGIN + "/" + path
        headers: dict[str, str] = {"Accept": "application/json"}
        if if_modified_since is not None:
            headers["If-Modified-Since"] = rfc1123(if_modified_since)
        if etag:
            headers["If-None-Match"] = etag
        return self._request_json(url, headers)

    def fetch_feed_entry(self, relative_path: str) -> dict[str, Any]:
        url = FEED_ORIGIN + relative_path if relative_path.startswith("/") else FEED_ORIGIN + "/" + relative_path
        data, _ = self._request_json(url, {"Accept": "application/json"})
        return data


def rfc1123(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return format_datetime(dt.astimezone(timezone.utc), usegmt=True)


def fetch_feed_page(
    path: str,
    token: str,
    *,
    if_modified_since: datetime | None = None,
    etag: str | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    session = NavFeedSession()
    session._token = token
    return session.fetch_feed_page(path, if_modified_since=if_modified_since, etag=etag)


def fetch_feed_entry(relative_path: str, token: str) -> dict[str, Any]:
    session = NavFeedSession()
    session._token = token
    return session.fetch_feed_entry(relative_path)


def default_if_modified_since(since_days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=max(1, since_days))
