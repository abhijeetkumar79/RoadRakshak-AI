"""
Geo utility helpers — distance calculations and geocoding wrapper.
"""
import math
from functools import lru_cache


def haversine_m(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in meters."""
    r = 6371000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@lru_cache(maxsize=256)
def geocode_place(query: str):
    """
    Geocode a place name to (lat, lon, display_name) using Nominatim (OpenStreetMap).
    Returns None if not found or if geopy/network is unavailable.
    Cached so repeated searches in the same session don't hit the API again.
    """
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="roadrakshak_ai_app")
        location = geolocator.geocode(query, timeout=10)
        if location:
            return (location.latitude, location.longitude, location.address)
    except Exception:
        return None
    return None


def reverse_geocode(lat: float, lon: float):
    """Reverse geocode lat/lon into a human-readable address string."""
    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="roadrakshak_ai_app")
        location = geolocator.reverse((lat, lon), timeout=10)
        if location:
            return location.address
    except Exception:
        return None
    return None
