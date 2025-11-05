from __future__ import annotations

from typing import Optional, Tuple, Dict, Any
import requests
from django.conf import settings


def find_nearest_streetview(lat: float, lng: float) -> Optional[Dict[str, Any]]:
    """Find nearest outdoor Street View pano using Google Street View Metadata API.

    Returns a dict with keys: 'status', 'pano_id' (optional), 'location' {'lat','lng'}
    or None if no panorama was found.
    """
    api_key = getattr(settings, 'MAPS_API_KEY', '')
    if not api_key:
        return None

    url = "https://maps.googleapis.com/maps/api/streetview/metadata"
    # Incrementally expand search radius (meters)
    for radius in (30, 50, 100, 250, 500):
        try:
            resp = requests.get(
                url,
                params={
                    'location': f"{lat},{lng}",
                    'key': api_key,
                    'source': 'outdoor',
                    'radius': radius,
                },
                timeout=10,
            )
        except Exception:
            continue
        if resp.status_code >= 400:
            continue
        data = resp.json()
        status = data.get('status')
        if status == 'OK':
            pano_id = data.get('pano_id')
            loc = data.get('location') or {}
            sv_lat = loc.get('lat', lat)
            sv_lng = loc.get('lng', lng)
            return {
                'status': status,
                'pano_id': pano_id,
                'location': {'lat': sv_lat, 'lng': sv_lng},
                'radius': radius,
            }
    return None



