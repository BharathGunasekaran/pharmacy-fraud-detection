from __future__ import annotations

from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from typing import Optional, Tuple, Iterable, List
import re
import requests
from django.conf import settings


_geocoder = Nominatim(user_agent="pharmacy_verifier_app", timeout=10)


def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    try:
        loc = _geocoder.geocode(address, addressdetails=False, exactly_one=True)
        if not loc:
            return None
        return (loc.latitude, loc.longitude)
    except Exception:
        return None


def geocode_all(address: str, limit: int = 5) -> List[Tuple[float, float]]:
    try:
        locs = _geocoder.geocode(address, addressdetails=False, exactly_one=False, limit=limit)
        if not locs:
            return []
        return [(l.latitude, l.longitude) for l in locs]
    except Exception:
        return []


NEAR_LANDMARK_RE = re.compile(r"\b(near|opp\.?|opposite|beside|behind|above)\b.+", re.I)


def simplify_address(address: str) -> str:
    # Remove landmark phrases like "near Hotel ..."
    s = NEAR_LANDMARK_RE.sub("", address)
    # Collapse extra spaces and commas
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r",\s+,", ", ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_city_hint(address: str) -> Optional[str]:
    # Heuristic: pick last two comma-separated tokens before postal code
    parts = [p.strip() for p in address.split(',') if p.strip()]
    if not parts:
        return None
    # Drop trailing PIN code token if present
    if re.search(r"\b\d{6}\b", parts[-1]):
        parts = parts[:-1]
    if len(parts) >= 2:
        return ", ".join(parts[-2:])
    return parts[-1] if parts else None


def address_is_city_like(address: Optional[str]) -> bool:
    if not address:
        return False
    s = address.strip()
    # City-like if it contains no street number and <= 3 comma-separated tokens
    if re.search(r"\d", s):
        return False
    parts = [p.strip() for p in s.split(',') if p.strip()]
    return len(parts) <= 3


def geocode_best(address: str) -> Optional[Tuple[float, float]]:
    # Try exact
    c = geocode_address(address)
    if c:
        return c
    # Fallback to Google Geocoding if available
    g = google_geocode(address)
    if g:
        return g
    # Try simplified (remove landmarks)
    simplified = simplify_address(address)
    if simplified and simplified != address:
        c = geocode_address(simplified)
        if c:
            return c
        g = google_geocode(simplified)
        if g:
            return g
    # Try city/state hint only
    city = extract_city_hint(address)
    if city:
        c = geocode_address(city)
        if c:
            return c
        g = google_geocode(city)
        if g:
            return g
    # Try multi-candidate and pick first (as a last resort)
    many = geocode_all(simplified or address, limit=5)
    return many[0] if many else None


def google_geocode(address: str) -> Optional[Tuple[float, float]]:
    api_key = getattr(settings, 'MAPS_API_KEY', '')
    if not api_key:
        return None
    try:
        resp = requests.get(
            'https://maps.googleapis.com/maps/api/geocode/json',
            params={'address': address, 'key': api_key},
            timeout=10,
        )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        if data.get('status') != 'OK':
            return None
        res = data.get('results') or []
        if not res:
            return None
        loc = res[0]['geometry']['location']
        return (loc['lat'], loc['lng'])
    except Exception:
        return None


def search_place(query: str) -> Optional[Tuple[float, float]]:
    try:
        loc = _geocoder.geocode(query, addressdetails=False, exactly_one=True)
        if not loc:
            return None
        return (loc.latitude, loc.longitude)
    except Exception:
        return None


def distance_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return geodesic(a, b).km


def pick_nearest(target: Tuple[float, float], candidates: Iterable[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    best = None
    best_d = None
    for c in candidates:
        try:
            d = distance_km(target, c)
        except Exception:
            continue
        if best_d is None or d < best_d:
            best = c
            best_d = d
    return best

