"""Shared urllib TLS + retry helpers for NAV/FINN HTTP clients."""
from __future__ import annotations

import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable

import certifi

RETRYABLE_HTTP_CODES: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})


def ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def should_retry_http_error(exc: urllib.error.HTTPError) -> bool:
    return exc.code in RETRYABLE_HTTP_CODES


def http_get_bytes(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    max_attempts: int = 3,
    retry_backoff_s: float = 1.0,
    timeout: float = 120,
    on_retry: Callable[[BaseException, int, int], None] | None = None,
) -> tuple[bytes, dict[str, str], int]:
    """
    GET with certifi TLS roots and retries on transient HTTP/network errors.

    Returns ``(body, headers_lowercased, status)``.
    Re-raises the last ``HTTPError`` / ``URLError`` when attempts are exhausted
    (callers wrap into domain-specific errors / handle 304).
    """
    req = urllib.request.Request(url, headers=headers or {})
    last_error: BaseException | None = None
    attempts = max(1, max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, context=ssl_context(), timeout=timeout) as resp:
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                return resp.read(), hdrs, int(resp.status)
        except urllib.error.HTTPError as e:
            last_error = e
            if should_retry_http_error(e) and attempt < attempts:
                if on_retry is not None:
                    on_retry(e, attempt, attempts)
                time.sleep(retry_backoff_s * attempt)
                continue
            raise
        except urllib.error.URLError as e:
            last_error = e
            if attempt >= attempts:
                raise
            if on_retry is not None:
                on_retry(e, attempt, attempts)
            time.sleep(retry_backoff_s * attempt)
    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Request failed for {url}")
