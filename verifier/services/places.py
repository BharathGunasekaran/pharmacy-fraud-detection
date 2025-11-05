from __future__ import annotations

from typing import List, Optional, Dict, Any, Tuple
import requests
import re
from django.conf import settings


def _normalize_name(name: str) -> str:
    s = name.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def text_search_pharmacy(query: str, region: Optional[str] = None) -> List[Dict[str, Any]]:
    api_key = getattr(settings, 'MAPS_API_KEY', '')
    if not api_key:
        return []
    try:
        params = {
            'query': query,
            'type': 'pharmacy',
            'key': api_key,
        }
        if region:
            params['region'] = region
        resp = requests.get('https://maps.googleapis.com/maps/api/place/textsearch/json', params=params, timeout=10)
        if resp.status_code >= 400:
            return []
        data = resp.json()
        if data.get('status') not in ('OK', 'ZERO_RESULTS'):
            return []
        return data.get('results') or []
    except Exception:
        return []


def find_best_storefront(pharmacy_name: str, address: str) -> Optional[Tuple[float, float, str, str]]:
    """Return (lat, lng, name, formatted_address) of the best-matching pharmacy storefront.
    Uses Places Text Search to match chain branches precisely.
    """
    name_n = _normalize_name(pharmacy_name)
    # Tolerate common plural/singular variants (walgreen vs walgreens)
    alt_tokens = {name_n, name_n + 's'}

    # Bias region based on simple heuristics
    region = 'us' if any(tok in name_n for tok in ['walgreen', 'cvs', 'rite aid']) else None

    # Compose focused query
    q = f"{pharmacy_name} {address}"
    results = text_search_pharmacy(q, region=region)
    if not results:
        return None

    best = None
    best_score = -1
    for r in results:
        name = r.get('name') or ''
        fmt = r.get('formatted_address') or ''
        nm = _normalize_name(name)
        score = 0
        if any(tok in nm for tok in alt_tokens):
            score += 3
        if 'pharmacy' in nm:
            score += 1
        # Prefer closer to provided address by Google prominence (higher rating/user_ratings_total)
        score += min(int(r.get('user_ratings_total') or 0), 500) / 500.0
        # Prefer open businesses
        if (r.get('business_status') or '').lower() == 'operational':
            score += 0.5
        if score > best_score:
            best_score = score
            loc = r['geometry']['location']
            best = (loc['lat'], loc['lng'], name, fmt)

    return best


def nearby_brand_storefront(lat: float, lng: float, brand: str, radius: int = 1500) -> Optional[Tuple[float, float, str, str]]:
    api_key = getattr(settings, 'MAPS_API_KEY', '')
    if not api_key:
        return None
    try:
        resp = requests.get(
            'https://maps.googleapis.com/maps/api/place/nearbysearch/json',
            params={
                'location': f'{lat},{lng}',
                'radius': radius,
                'type': 'pharmacy',
                'keyword': brand,
                'key': api_key,
            },
            timeout=10,
        )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        if data.get('status') not in ('OK', 'ZERO_RESULTS'):
            return None
        results = data.get('results') or []
        if not results:
            return None
        norm_brand = _normalize_name(brand)
        best = None
        best_score = -1
        for r in results:
            name = r.get('name') or ''
            nm = _normalize_name(name)
            score = 0
            if norm_brand in nm:
                score += 3
            score += min(int(r.get('user_ratings_total') or 0), 500) / 500.0
            if (r.get('business_status') or '').lower() == 'operational':
                score += 0.5
            if score > best_score:
                best_score = score
                loc = r['geometry']['location']
                best = (loc['lat'], loc['lng'], name, r.get('vicinity') or '')
        return best
    except Exception:
        return None


