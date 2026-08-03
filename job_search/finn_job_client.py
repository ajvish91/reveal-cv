"""HTTP client for FINN.no job search (HTML scrape + JSON-LD detail parse)."""
from __future__ import annotations

import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import certifi
from selectolax.parser import HTMLParser

from job_search.logging_config import get_logger

log = get_logger("job_search.ingest_finn")

FINN_ORIGIN = "https://www.finn.no"
USER_AGENT = "job-search-automation/0.1 (personal job search; local script)"
RETRYABLE_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}
FINNKODE_RE = re.compile(r"/job/ad/(\d+)")
JOB_POSTING_TYPE = "JobPosting"
DATE_POSTED_RE = re.compile(r'datePosted\\",\\"([^"]+)\\"')
VALID_THROUGH_RE = re.compile(r'validThrough\\",\\"([^"]+)\\"')


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _should_retry_http_error(exc: urllib.error.HTTPError) -> bool:
    return exc.code in RETRYABLE_HTTP_CODES


def http_get_text(
    url: str,
    headers: dict[str, str] | None = None,
    *,
    max_attempts: int = 3,
    retry_backoff_s: float = 1.0,
) -> tuple[str, dict[str, str]]:
    req_headers = {"User-Agent": USER_AGENT, **(headers or {})}
    req = urllib.request.Request(url, headers=req_headers)
    last_error: Exception | None = None
    for attempt in range(1, max(1, max_attempts) + 1):
        try:
            with urllib.request.urlopen(req, context=_ssl_context(), timeout=120) as resp:
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
                body = resp.read().decode("utf-8", errors="replace")
                return body, hdrs
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            if _should_retry_http_error(e) and attempt < max_attempts:
                log.warning(
                    "HTTP %d for %s attempt %d/%d; retrying",
                    e.code,
                    url,
                    attempt,
                    max_attempts,
                )
                time.sleep(retry_backoff_s * attempt)
                last_error = e
                continue
            log.error("HTTP %d for %s: %s", e.code, url, err[:200])
            raise RuntimeError(f"HTTP {e.code} {url}: {err[:500]}") from e
        except urllib.error.URLError as e:
            last_error = e
            if attempt >= max_attempts:
                log.error("request failed for %s after %d attempts: %s", url, max_attempts, e.reason)
                raise RuntimeError(f"Request failed for {url}: {e.reason}") from e
            log.warning(
                "URL error for %s attempt %d/%d: %s; retrying",
                url,
                attempt,
                max_attempts,
                e.reason,
            )
            time.sleep(retry_backoff_s * attempt)
    if last_error is not None:
        raise RuntimeError(f"Request failed for {url}: {last_error}")
    raise RuntimeError(f"Request failed for {url}")


def build_search_url(query: str, *, page: int = 1, employment: str = "fulltime") -> str:
    params: dict[str, str] = {"q": query}
    if page > 1:
        params["page"] = str(page)
    path = f"/job/{employment}/search.html"
    return FINN_ORIGIN + path + "?" + urllib.parse.urlencode(params)


def build_job_url(finnkode: str) -> str:
    return f"{FINN_ORIGIN}/job/ad/{finnkode}"


def extract_finnkode(href: str | None) -> str | None:
    if not href:
        return None
    match = FINNKODE_RE.search(href)
    return match.group(1) if match else None


def _card_text(node: Any, selectors: tuple[str, ...]) -> str | None:
    for sel in selectors:
        found = node.css_first(sel)
        if found is not None:
            text = found.text(strip=True)
            if text:
                return text
    return None


def parse_search_cards(html: str) -> list[dict[str, str | None]]:
    """Extract job cards from a FINN search results page."""
    tree = HTMLParser(html)
    seen: set[str] = set()
    cards: list[dict[str, str | None]] = []

    for article in tree.css("article"):
        link = article.css_first('a[href*="/job/ad/"]')
        if link is None:
            continue
        href = link.attributes.get("href", "")
        finnkode = extract_finnkode(href)
        if not finnkode or finnkode in seen:
            continue
        seen.add(finnkode)

        title = link.text(strip=True) or None
        employer = _card_text(
            article,
            (
                '[data-testid="company-name"]',
                ".sf-search-ad__company",
                ".text-caption strong",
                ".company",
            ),
        )
        location = _card_text(
            article,
            (
                '[data-testid="location"]',
                ".sf-search-ad__location",
                "footer .job-card__pills li span",
                ".location",
            ),
        )
        snippet = _card_text(
            article,
            (
                ".job-card__body h3",
                "h3.h4",
            ),
        )
        cards.append(
            {
                "finnkode": finnkode,
                "title": title,
                "employer_guess": employer,
                "location_guess": location,
                "description_snippet": snippet,
                "url": build_job_url(finnkode),
            }
        )

    if cards:
        return cards

    # Fallback: any /job/ad/ links on the page (e.g. minimal markup in tests).
    for link in tree.css('a[href*="/job/ad/"]'):
        href = link.attributes.get("href", "")
        finnkode = extract_finnkode(href)
        if not finnkode or finnkode in seen:
            continue
        seen.add(finnkode)
        cards.append(
            {
                "finnkode": finnkode,
                "title": link.text(strip=True) or None,
                "employer_guess": None,
                "location_guess": None,
                "description_snippet": None,
                "url": build_job_url(finnkode),
            }
        )
    return cards


def _unwrap_json_ld_payload(data: Any) -> Any:
    if isinstance(data, dict) and "script:ld+json" in data and len(data) == 1:
        return data["script:ld+json"]
    return data


def _collect_schema_objects(data: Any, out: list[dict[str, Any]]) -> None:
    data = _unwrap_json_ld_payload(data)
    if isinstance(data, list):
        for item in data:
            _collect_schema_objects(item, out)
        return
    if not isinstance(data, dict):
        return
    out.append(data)
    graph = data.get("@graph")
    if isinstance(graph, list):
        for item in graph:
            _collect_schema_objects(item, out)


def _iter_json_ld_objects(html: str) -> list[dict[str, Any]]:
    tree = HTMLParser(html)
    objects: list[dict[str, Any]] = []
    for script in tree.css('script[type="application/ld+json"]'):
        raw = script.text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            log.debug("JSON-LD parse failure in script tag")
            continue
        _collect_schema_objects(data, objects)
    return objects


def _is_job_posting(obj: dict[str, Any]) -> bool:
    obj_type = obj.get("@type")
    if obj_type == JOB_POSTING_TYPE:
        return True
    if isinstance(obj_type, list):
        return JOB_POSTING_TYPE in obj_type
    return False


def _org_name(org: Any) -> str | None:
    if isinstance(org, dict):
        name = org.get("name")
        return str(name).strip() if name else None
    if isinstance(org, str):
        return org.strip() or None
    return None


def _first_place(job_location: Any) -> dict[str, Any] | None:
    if isinstance(job_location, list):
        for item in job_location:
            if isinstance(item, dict):
                return item
        return None
    if isinstance(job_location, dict):
        return job_location
    return None


def _address_fields(job_location: Any) -> tuple[str | None, str | None]:
    place = _first_place(job_location)
    if not place:
        return None, None
    address = place.get("address")
    if not isinstance(address, dict):
        return None, None
    municipal = (address.get("addressLocality") or "").strip() or None
    county = (address.get("addressRegion") or "").strip() or None
    return municipal, county


def _meta_content(tree: HTMLParser, *, prop: str | None = None, name: str | None = None) -> str | None:
    for meta in tree.css("meta"):
        if prop and meta.attributes.get("property") == prop:
            value = (meta.attributes.get("content") or "").strip()
            return value or None
        if name and meta.attributes.get("name") == name:
            value = (meta.attributes.get("content") or "").strip()
            return value or None
    return None


def _parse_og_title_segments(og_title: str | None) -> tuple[str | None, str | None, str | None]:
    if not og_title:
        return None, None, None
    main = og_title.split("|", 1)[0].strip()
    parts = [part.strip() for part in main.split("·") if part.strip()]
    if len(parts) >= 3:
        return parts[0], parts[1], parts[2]
    if len(parts) == 2:
        return parts[0], parts[1], None
    if parts:
        return parts[0], None, None
    return None, None, None


def _detail_title(tree: HTMLParser) -> str | None:
    for h1 in tree.css("h1"):
        text = h1.text(strip=True)
        if not text:
            continue
        lowered = text.casefold()
        if "finn.no" in lowered or "mulighetenes marked" in lowered:
            continue
        return text
    return None


def parse_job_detail_html(html: str) -> dict[str, Any] | None:
    """Fallback detail parse when JSON-LD JobPosting is missing."""
    tree = HTMLParser(html)
    title = _detail_title(tree)
    og_title = _meta_content(tree, prop="og:title")
    og_title_title, og_location, og_employer = _parse_og_title_segments(og_title)
    if not title:
        title = og_title_title

    employer = og_employer
    company_link = tree.css_first('a[href*="/job/company/"]')
    if company_link is not None:
        link_text = company_link.text(strip=True)
        if link_text:
            employer = link_text

    desc_parts = [node.text(strip=True) for node in tree.css(".import-decoration") if node.text(strip=True)]
    description = "\n\n".join(desc_parts) if desc_parts else None
    if not description:
        description = _meta_content(tree, name="description") or _meta_content(tree, prop="og:description")

    municipal, county = og_location, None
    if not municipal:
        breadcrumb_items = [
            node.text(strip=True)
            for node in tree.css('script[type="application/ld+json"]')
            if node.text(strip=True)
        ]
        for raw in breadcrumb_items:
            try:
                payload = _unwrap_json_ld_payload(json.loads(raw))
            except json.JSONDecodeError:
                log.debug("breadcrumb JSON-LD parse failure")
                continue
            if not isinstance(payload, dict) or payload.get("@type") != "BreadcrumbList":
                continue
            elements = payload.get("itemListElement")
            if not isinstance(elements, list):
                continue
            for element in reversed(elements):
                if not isinstance(element, dict):
                    continue
                item = element.get("item")
                if isinstance(item, dict):
                    name = (item.get("name") or "").strip()
                    if name and name.casefold() not in {"finn", "jobb", "søk"}:
                        municipal = name
                        break
            if municipal:
                break

    date_posted = None
    match = DATE_POSTED_RE.search(html)
    if match:
        date_posted = match.group(1)
    valid_through = None
    match = VALID_THROUGH_RE.search(html)
    if match:
        valid_through = match.group(1)

    if not any((title, employer, description, municipal, county, date_posted, valid_through)):
        return None

    return {
        "title": title,
        "description": description,
        "employer_name": employer,
        "municipal": municipal,
        "county": county,
        "datePosted": date_posted,
        "validThrough": valid_through,
        "raw": {"parse_source": "html"},
    }


def parse_job_posting_json_ld(html: str) -> dict[str, Any] | None:
    for obj in _iter_json_ld_objects(html):
        if not _is_job_posting(obj):
            continue
        municipal, county = _address_fields(obj.get("jobLocation"))
        return {
            "title": (obj.get("title") or "").strip() or None,
            "description": obj.get("description"),
            "employer_name": _org_name(obj.get("hiringOrganization")),
            "municipal": municipal,
            "county": county,
            "datePosted": obj.get("datePosted"),
            "validThrough": obj.get("validThrough"),
            "raw": obj,
        }
    return None


def merge_job_detail(json_ld: dict[str, Any] | None, html_detail: dict[str, Any] | None) -> dict[str, Any] | None:
    if json_ld is None and html_detail is None:
        return None
    if json_ld is None:
        return dict(html_detail)
    if html_detail is None:
        return dict(json_ld)

    merged = dict(html_detail)
    for key, value in json_ld.items():
        if value not in (None, "", []):
            merged[key] = value
    if not merged.get("description"):
        merged["description"] = html_detail.get("description")
    if not merged.get("title"):
        merged["title"] = html_detail.get("title")
    if not merged.get("employer_name"):
        merged["employer_name"] = html_detail.get("employer_name")
    if not merged.get("municipal"):
        merged["municipal"] = html_detail.get("municipal")
    if not merged.get("county"):
        merged["county"] = html_detail.get("county")
    if not merged.get("datePosted"):
        merged["datePosted"] = html_detail.get("datePosted")
    if not merged.get("validThrough"):
        merged["validThrough"] = html_detail.get("validThrough")
    raw = {"json_ld": json_ld.get("raw"), "html": html_detail.get("raw")}
    merged["raw"] = raw
    return merged


class FinnJobSession:
    def __init__(self, *, sleep_s: float = 0.3) -> None:
        self.sleep_s = max(0.0, sleep_s)
        self._last_request_at: float | None = None

    def _rate_limit(self) -> None:
        if self.sleep_s <= 0:
            return
        if self._last_request_at is not None:
            elapsed = time.monotonic() - self._last_request_at
            if elapsed < self.sleep_s:
                time.sleep(self.sleep_s - elapsed)
        self._last_request_at = time.monotonic()

    def fetch_text(self, url: str) -> str:
        self._rate_limit()
        body, _ = http_get_text(url)
        return body

    def search_jobs(
        self,
        query: str,
        *,
        page: int = 1,
        employment: str = "fulltime",
    ) -> list[dict[str, str | None]]:
        url = build_search_url(query, page=page, employment=employment)
        html = self.fetch_text(url)
        return parse_search_cards(html)

    def fetch_job_detail(self, finnkode: str) -> dict[str, Any]:
        url = build_job_url(finnkode)
        html = self.fetch_text(url)
        parsed = merge_job_detail(parse_job_posting_json_ld(html), parse_job_detail_html(html))
        if parsed is None:
            raise RuntimeError(f"No job detail content on {url}")
        parsed["finnkode"] = finnkode
        parsed["url"] = url
        return parsed
