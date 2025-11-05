from __future__ import annotations

from typing import Optional, Tuple

INSURED_BRANDS = {
    'walgreens', 'walgreen', 'cvs', 'rite aid', 'apollopharmacy', 'apollo pharmacy', 'boots',
}


def is_insured_brand(name: Optional[str]) -> bool:
    if not name:
        return False
    n = name.lower().strip()
    return any(b in n for b in INSURED_BRANDS)


def classify_result(
    input_address_coords: Optional[Tuple[float, float]],
    scraped_address_coords: Optional[Tuple[float, float]],
    found_any_location: bool,
    threshold_km: float = 1.0,
    pano_found: bool = False,
    storefront_found: bool = False,
    city_like_input: bool = False,
) -> str:
    # If we located a storefront via Places, accept as Found
    if storefront_found:
        return 'Found'
    # If we have a valid outdoor Street View panorama for the chosen spot,
    # consider the pharmacy to exist at that location.
    if pano_found:
        return 'Found'
    # If nothing found
    if not found_any_location:
        return 'Not Found'

    # No input address provided: if we have any location, consider Found
    if input_address_coords is None:
        return 'Found'

    # If we have both, compare distance
    if scraped_address_coords is not None:
        dist = _try_distance(input_address_coords, scraped_address_coords)
        if dist is None:
            return 'Found'
        # Be more lenient if input is city-level only
        limit = 10.0 if city_like_input else threshold_km
        return 'Found' if dist <= limit else 'Fraud Pharmacy'

    # If we have at least a location from name search, consider Found
    return 'Found'


def _try_distance(a: Tuple[float, float], b: Tuple[float, float]) -> Optional[float]:
    try:
        from .geocode import distance_km
        return distance_km(a, b)
    except Exception:
        return None
