#!/usr/bin/env python3
"""
Scrape TEK Norge member list, then estimate which members have activity in Rogaland
using Brønnøysundregisteret (head office + underenheter) and optional website keyword scan.
"""
from __future__ import annotations

import csv
import html as html_lib
import json
import re
import subprocess
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

TEK_URL = "https://teknorge.no/tek-norges-medlemmer/"
BRREG_SEARCH = "https://data.brreg.no/enhetsregisteret/api/enheter"
BRREG_UNDER = "https://data.brreg.no/enhetsregisteret/api/underenheter"

# Kommunenummer in Rogaland (per 2024 municipal structure, fylke 11)
ROGALAND_KOMMUNENUMMER: frozenset[str] = frozenset(
    {
        "1103",  # Stavanger
        "1106",  # Haugesund
        "1108",  # Sandnes
        "1111",  # Eigersund
        "1112",  # Sokndal
        "1114",  # Bjerkreim
        "1119",  # Hå
        "1120",  # Klepp
        "1121",  # Time
        "1122",  # Gjesdal
        "1124",  # Sola
        "1127",  # Randaberg
        "1130",  # Strand
        "1133",  # Hjelmeland
        "1134",  # Suldal
        "1135",  # Sauda
        "1144",  # Kvitsøy
        "1149",  # Tysvær
        "1151",  # Utsira
        "1154",  # Bokn
        "1159",  # Vindafjord
        "1160",  # Etne
    }
)

# Secondary scan: visible text on member website / kontakt pages
WEB_KEYWORDS = [
    "rogaland",
    "stavanger",
    "sandnes",
    "haugesund",
    "haugaland",
    "bryne",
    "egersund",
    "eigersund",
    "kopervik",
    "karmøy",
    "karmoy",
    "forus",
    "jæren",
    "jaeren",
    "randaberg",
    "sola",
    "klepp",
    "gjesdal",
    "ålgård",
    "algard",
    "hafrsfjord",
    "tananger",
]

KONTAKT_PATHS = ["", "/kontakt", "/no/kontakt", "/contact", "/om-oss/kontakt"]

CURL_BASE = [
    "curl",
    "-sL",
    "--compressed",
    "-A",
    "Mozilla/5.0 (compatible; TEKRogalandCheck/1.0; +local script)",
    "--connect-timeout",
    "15",
    "--max-time",
    "45",
]

# Minimum time between HTTP request starts (shared across threads) to stay polite to APIs/sites.
_rate_lock = threading.Lock()
_rate_next_allowed = 0.0
MIN_REQUEST_INTERVAL = 0.07


def _rate_acquire() -> None:
    global _rate_next_allowed
    with _rate_lock:
        now = time.time()
        wait = _rate_next_allowed - now
        if wait > 0:
            time.sleep(wait)
        _rate_next_allowed = time.time() + MIN_REQUEST_INTERVAL


def curl_bytes(url: str, max_bytes: int = 2_500_000) -> bytes:
    _rate_acquire()
    cmd = CURL_BASE + ["--max-filesize", str(max_bytes), url]
    try:
        return subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        return b""


def curl_json(url: str) -> dict[str, Any] | None:
    raw = curl_bytes(url, max_bytes=2_000_000)
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


def extract_content_html(page_html: str) -> str:
    m = re.search(
        r'<div class="the-content">(.*?)(?:<p><em>Sist oppdatert:|<div class="clearfix"></div>\s*</div>\s*</div>\s*</section>)',
        page_html,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        raise ValueError("Could not find .the-content block on TEK members page")
    return m.group(1)


def parse_members(html_chunk: str) -> list[tuple[str, str | None]]:
    """Returns list of (display_name, website_url_or_none)."""
    members: list[tuple[str, str | None]] = []
    for m in re.finditer(r"<p>(.*?)</p>\s*", html_chunk, re.DOTALL | re.IGNORECASE):
        inner = m.group(1).strip()
        if not inner or inner.lower().startswith("<em"):
            continue
        am = re.search(
            r'<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            inner,
            re.DOTALL | re.IGNORECASE,
        )
        if am:
            url = html_lib.unescape(am.group(1).strip())
            name = html_lib.unescape(re.sub(r"<[^>]+>", "", am.group(2)))
            rest = inner[am.end() :]
            rest_text = html_lib.unescape(re.sub(r"<[^>]+>", "", rest)).strip()
            if rest_text:
                name = f"{name} {rest_text}".strip()
        else:
            url = None
            name = html_lib.unescape(re.sub(r"<[^>]+>", "", inner))
        name = re.sub(r"\s+", " ", name).strip()
        if name:
            members.append((name, url))
    return members


def norm_name(s: str) -> str:
    s = s.upper()
    s = s.replace("Æ", "A").replace("Ø", "O").replace("Å", "A")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return s.strip()


def brreg_query_name(name: str) -> dict[str, Any] | None:
    q = name
    for suffix in (
        " ASA",
        " AS",
        " ANS",
        " DA",
        " SA",
        " NUF",
    ):
        if q.upper().endswith(suffix):
            q = q[: -len(suffix)].strip()
            break
    q = q.split("/")[0].strip()
    params = urllib.parse.urlencode({"navn": q, "size": 30})
    return curl_json(f"{BRREG_SEARCH}?{params}")


def pick_enhet(data: dict[str, Any], wanted_norm: str) -> dict[str, Any] | None:
    enheter = data.get("_embedded", {}).get("enheter") or []
    if not enheter:
        return None
    best: tuple[int, dict[str, Any]] | None = None
    for e in enheter:
        n = norm_name(e.get("navn") or "")
        score = 0
        if n == wanted_norm:
            score = 100
        elif n.startswith(wanted_norm) or wanted_norm.startswith(n):
            score = 85
        elif wanted_norm in n or n in wanted_norm:
            score = 60
        of = (e.get("organisasjonsform") or {}).get("kode") or ""
        if of in ("ASA", "AS", "NUF", "KF", "SF"):
            score += 5
        if best is None or score > best[0]:
            best = (score, e)
    if len(enheter) == 1:
        return enheter[0]
    if best and best[0] >= 80:
        return best[1]
    return None


def addr_rogaland(addr: dict[str, Any] | None) -> str | None:
    if not addr or addr.get("landkode") not in (None, "NO"):
        return None
    kn = addr.get("kommunenummer")
    if kn in ROGALAND_KOMMUNENUMMER:
        kommune = addr.get("kommune") or ""
        return f"{kommune} ({kn})".strip()
    return None


def collect_brreg_org_addresses(enhet: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    for key in ("forretningsadresse", "postadresse"):
        hint = addr_rogaland(enhet.get(key))
        if hint:
            hits.append(f"{key}:{hint}")
    return hits


def fetch_all_underenheter(orgnr: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    page = 0
    while True:
        params = urllib.parse.urlencode({"overordnetEnhet": orgnr, "size": 100, "page": page})
        data = curl_json(f"{BRREG_UNDER}?{params}")
        if not data:
            break
        chunk = data.get("_embedded", {}).get("underenheter") or []
        out.extend(chunk)
        pg = data.get("page") or {}
        if page >= int(pg.get("totalPages", 1)) - 1:
            break
        page += 1
    return out


def rogaland_from_brreg(display_name: str) -> tuple[bool, str]:
    wanted = norm_name(display_name)
    data = brreg_query_name(display_name)
    if not data:
        return False, ""
    enhet = pick_enhet(data, wanted)
    if not enhet:
        return False, ""
    orgnr = enhet.get("organisasjonsnummer")
    reasons: list[str] = collect_brreg_org_addresses(enhet)

    if orgnr:
        for u in fetch_all_underenheter(str(orgnr)):
            ba = addr_rogaland(u.get("beliggenhetsadresse"))
            if ba:
                reasons.append(f"underenhet:{ba}")
            pa = addr_rogaland(u.get("postadresse"))
            if pa:
                reasons.append(f"underenhet_post:{pa}")
    if reasons:
        return True, "; ".join(sorted(set(reasons)))
    return False, ""


def strip_tags(html: str) -> str:
    t = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    t = re.sub(r"(?is)<style.*?>.*?</style>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return html_lib.unescape(t)


def web_has_rogaland(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)
    origin = urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))

    found_kw: set[str] = set()
    for path in KONTAKT_PATHS:
        if path:
            fetch_url = origin.rstrip("/") + path
        else:
            fetch_url = url
        raw = curl_bytes(fetch_url, max_bytes=900_000)
        if not raw:
            continue
        text = strip_tags(raw.decode("utf-8", errors="replace")).casefold()
        for kw in WEB_KEYWORDS:
            if kw.casefold() in text:
                found_kw.add(kw)
        if found_kw:
            break

    if found_kw:
        return True, f"website:{origin} keywords={','.join(sorted(found_kw))}"
    return False, ""


@dataclass
class Row:
    name: str
    website: str
    in_rogaland: bool
    evidence: str


def analyze_member(args: tuple[int, str, str | None]) -> tuple[int, Row]:
    i, name, site = args
    evidence_parts: list[str] = []
    ok = False
    br_ok, br_ev = rogaland_from_brreg(name)
    if br_ok:
        ok = True
        evidence_parts.append(f"Brreg:{br_ev}")

    if not ok and site:
        w_ok, w_ev = web_has_rogaland(site)
        if w_ok:
            ok = True
            evidence_parts.append(w_ev)

    site_s = site or ""
    ev = " | ".join(evidence_parts) if evidence_parts else (
        "no match" if site else "no website + no Brreg Rogaland match"
    )
    return i, Row(name=name, website=site_s, in_rogaland=ok, evidence=ev)


def main() -> int:
    raw = curl_bytes(TEK_URL).decode("utf-8", errors="replace")
    if "the-content" not in raw:
        print("Failed to download TEK members page", file=sys.stderr)
        return 1
    chunk = extract_content_html(raw)
    members = parse_members(chunk)
    n = len(members)
    print(f"Found {n} TEK members; checking Rogaland ({MIN_REQUEST_INTERVAL}s min request spacing, parallel workers)…", file=sys.stderr)

    rows: list[Row | None] = [None] * n
    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(analyze_member, (i, name, site)) for i, (name, site) in enumerate(members)]
        for fut in as_completed(futures):
            idx, row = fut.result()
            rows[idx] = row
            done += 1
            if done % 40 == 0 or done == n:
                print(f"  …{done}/{n}", file=sys.stderr)

    rows_list: list[Row] = [r for r in rows if r is not None]

    base = Path(__file__).resolve().parent
    rogaland_csv = base / "teknorge_medlemmer_rogaland.csv"
    all_csv = base / "teknorge_medlemmer_rogaland_all_results.csv"

    with open(rogaland_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company_name", "website", "evidence"])
        for r in rows_list:
            if r.in_rogaland:
                w.writerow([r.name, r.website, r.evidence])

    with open(all_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["company_name", "website", "in_rogaland", "evidence"])
        for r in rows_list:
            w.writerow([r.name, r.website, "yes" if r.in_rogaland else "no", r.evidence])
    n_yes = sum(1 for r in rows_list if r.in_rogaland)
    print(f"Done. Rogaland: {n_yes} / {n}", file=sys.stderr)
    print(rogaland_csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
