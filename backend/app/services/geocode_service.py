"""
Coordinates -> a human-readable place name, via OpenStreetMap's Nominatim.

Why on the server and not in the browser: Nominatim's free service allows at
most one request per second, requires an identifying User-Agent, and asks
clients to cache results. A browser that looked up every row of the Reports
list, the map and the official's queue would break all three. So the server
looks a point up once, caches it, and the address is stored with the report;
lists and the PDF read the stored value.

A failed lookup is never an error. The complaint is located by its
coordinates; the address is a convenience for the people reading it. On any
failure this returns None and the caller shows coordinates instead - never a
guessed area name.

Usage policy: https://operations.osmfoundation.org/policies/nominatim/
"""
from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import OrderedDict
from typing import Optional

from app.config import Settings, get_settings
from app.utils.logging_config import get_logger

log = get_logger(__name__)

# Most specific first. Nominatim uses different keys for the same idea in
# different places (a colony may be a "neighbourhood", "suburb" or "quarter").
_STREET_KEYS = ("road", "pedestrian", "footway", "residential", "path")
_NEIGHBOURHOOD_KEYS = ("neighbourhood", "quarter", "hamlet")
_AREA_KEYS = ("suburb", "village", "city_district")
_CITY_KEYS = ("city", "town", "municipality", "county", "state_district")

_CACHE_SIZE = 2048
_cache: "OrderedDict[tuple, Optional[dict]]" = OrderedDict()
_cache_lock = threading.Lock()
_rate_lock = threading.Lock()
_last_request = 0.0


def _first(address: dict, keys) -> Optional[str]:
    for key in keys:
        value = (address.get(key) or "").strip()
        if value:
            return value
    return None


def format_label(address: dict) -> Optional[str]:
    """
    "Snehapuri Colony Main Road, Nagole, Hyderabad" from Nominatim's parts:
    street, colony, area, city. A part already contained in an earlier one is
    dropped ("Snehapuri Colony" adds nothing after "Snehapuri Colony Main
    Road"), as are repeats (a suburb is often also the city district).
    """
    parts: list = []
    for keys in (_STREET_KEYS, _NEIGHBOURHOOD_KEYS, _AREA_KEYS, _CITY_KEYS):
        value = _first(address, keys)
        if value and not any(value.lower() in p.lower() for p in parts):
            parts.append(value)
    return ", ".join(parts) or None


def _cache_key(latitude: float, longitude: float) -> tuple:
    # 4 decimal places is about 11 m: the same pothole re-pinned by a
    # finger's width is the same address, and one lookup.
    return (round(latitude, 4), round(longitude, 4))


def _throttle(min_interval: float) -> None:
    """Hold this thread until at least `min_interval` s since the last request."""
    global _last_request
    with _rate_lock:
        wait = _last_request + min_interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()


def _fetch(latitude: float, longitude: float, settings: Settings) -> Optional[dict]:
    query = urllib.parse.urlencode({
        "format": "jsonv2",
        "lat": "%.6f" % latitude,
        "lon": "%.6f" % longitude,
        "zoom": 18,              # street level
        "addressdetails": 1,
        "accept-language": "en",
    })
    url = "%s/reverse?%s" % (settings.geocoder_url.rstrip("/"), query)
    request = urllib.request.Request(url, headers={
        "User-Agent": settings.geocoder_user_agent,
        "Accept": "application/json",
    })
    _throttle(settings.geocoder_min_interval_seconds)
    with urllib.request.urlopen(request, timeout=settings.geocoder_timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, dict) or "error" in payload:
        return None   # e.g. a point in the sea: {"error": "Unable to geocode"}
    address = payload.get("address") or {}
    label = format_label(address)
    if not label:
        return None
    return {
        "label": label,
        "full": (payload.get("display_name") or label).strip(),
        "postcode": address.get("postcode"),
        "source": "OpenStreetMap",
    }


def reverse(latitude: float, longitude: float,
            settings: Optional[Settings] = None) -> Optional[dict]:
    """
    {"label", "full", "postcode", "source"} for the point, or None.
    Blocking (network + up to one second of throttling): call it from a
    worker thread, never directly on the event loop.
    """
    settings = settings or get_settings()
    if not settings.geocoding_enabled:
        return None

    key = _cache_key(latitude, longitude)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]

    try:
        result = _fetch(latitude, longitude, settings)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        # Do not cache a failure: the next attempt may well succeed.
        log.warning("Reverse geocoding failed for %.4f,%.4f: %s", latitude, longitude, exc)
        return None

    with _cache_lock:
        _cache[key] = result
        _cache.move_to_end(key)
        while len(_cache) > _CACHE_SIZE:
            _cache.popitem(last=False)
    return result


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()
