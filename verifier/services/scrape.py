from __future__ import annotations

import re
from typing import Optional, List, Set
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup


def _extract_text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True))


ADDRESS_RE = re.compile(r"\d+\s+[^,\n]+,\s*[^,\n]+,?\s*[A-Z]{2}\s*\d{5}(-\d{4})?", re.I)


def _looks_like_address(text: str) -> bool:
    if not text:
        return False
    if ADDRESS_RE.search(text):
        return True
    # Mild heuristic
    return any(token in text.lower() for token in [' st', ' ave', ' rd', ' blvd', ' suite', 'ste ', ' drive', ' dr '])


def scrape_address_from_site(url: str) -> Optional[str]:
    """Single address scraper (backward compatibility)."""
    addrs = scrape_addresses_from_site(url, max_candidates=1)
    return addrs[0] if addrs else None


def scrape_addresses_from_site(url: str, max_candidates: int = 5) -> List[str]:
    """Scrape multiple address candidates from a single page."""
    try:
        resp = requests.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    except Exception:
        return []
    if resp.status_code >= 400:
        return []
    soup = BeautifulSoup(resp.text, 'lxml')

    candidates: List[str] = []
    
    # Try schema.org postal address
    for scope in soup.select('[itemtype*="PostalAddress"]'):
        txt = _extract_text(scope)
        if txt and len(txt) > 10 and _looks_like_address(txt):
            candidates.append(txt)
            if len(candidates) >= max_candidates:
                return _dedupe_keep_longest(candidates)[:max_candidates]

    # Common address containers
    for selector in ['address', '.address', '#address', '.contact', '#contact', '[href*="/contact"]']:
        for el in soup.select(selector):
            txt = _extract_text(el)
            if _looks_like_address(txt):
                candidates.append(txt)
                if len(candidates) >= max_candidates:
                    return _dedupe_keep_longest(candidates)[:max_candidates]

    if candidates:
        return _dedupe_keep_longest(candidates)[:max_candidates]

    # Fallback: find lines with street number and city/state zip patterns
    text = soup.get_text("\n", strip=True)
    for line in text.splitlines():
        if _looks_like_address(line):
            candidates.append(line.strip())
            if len(candidates) >= max_candidates:
                break
    return _dedupe_keep_longest(candidates)[:max_candidates]


def _dedupe_keep_longest(items: List[str]) -> List[str]:
    """Remove duplicates, keeping the longest version of each."""
    seen = set()
    out: List[str] = []
    for s in sorted(items, key=len, reverse=True):
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


PRIORITY_PATH_HINTS = [
    'store', 'stores', 'location', 'locations', 'branch', 'branches',
    'contact', 'contact-us', 'find-us', 'findus', 'visit-us'
]


def scrape_addresses_with_crawl(base_url: str, max_pages: int = 6, max_candidates: int = 10) -> List[str]:
    """Crawl a few in-domain pages likely to contain addresses and collect candidates.
    Only follows links within the same host and with path hints (stores/locations/contact).
    """
    parsed = urlparse(base_url)
    host = parsed.netloc
    to_visit = [base_url]
    visited: Set[str] = set()
    found: List[str] = []

    while to_visit and len(visited) < max_pages and len(found) < max_candidates:
        cur = to_visit.pop(0)
        if cur in visited:
            continue
        visited.add(cur)
        try:
            r = requests.get(cur, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        except Exception:
            continue
        if r.status_code >= 400:
            continue
        s = BeautifulSoup(r.text, 'lxml')
        # scrape on this page
        page_addrs = scrape_addresses_from_site(cur, max_candidates=max_candidates)
        for a in page_addrs:
            if a not in found:
                found.append(a)
                if len(found) >= max_candidates:
                    break
        # queue relevant links
        for a in s.select('a[href]'):
            href = a.get('href') or ''
            full = urljoin(cur, href)
            p = urlparse(full)
            if p.netloc != host:
                continue
            if any(h in (p.path or '').lower() for h in PRIORITY_PATH_HINTS):
                if full not in visited and full not in to_visit:
                    to_visit.append(full)

    return _dedupe_keep_longest(found)[:max_candidates]
