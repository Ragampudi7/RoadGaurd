"""
Read the GPS position a camera embedded in a photograph (EXIF GPS IFD).

Phones write the location into the photo when the camera's location setting is
on - this is how "geo-tag" and GPS-stamp camera apps work too. It is the
location of the *photograph*, which for a gallery upload is the pothole, not
wherever the citizen happens to be when they upload it.

Many photos carry none: WhatsApp and most messengers strip it, screenshots
never had it, and some browsers remove it on upload. Callers must treat
``None`` as normal, not as an error.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Optional

from PIL import Image

_GPS_IFD = 0x8825
_EXIF_IFD = 0x8769
# GPS IFD tags
_LAT_REF, _LAT, _LON_REF, _LON = 1, 2, 3, 4
# EXIF IFD tag
_DATETIME_ORIGINAL = 0x9003


@dataclass(frozen=True)
class PhotoGPS:
    latitude: float
    longitude: float
    taken_at: Optional[str] = None   # "YYYY:MM:DD HH:MM:SS" as the camera wrote it


def _to_degrees(value) -> Optional[float]:
    """EXIF stores degrees, minutes, seconds as three rationals."""
    try:
        d, m, s = (float(part) for part in value)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    return d + m / 60.0 + s / 3600.0


def read_photo_gps(data: bytes) -> Optional[PhotoGPS]:
    """Return the embedded GPS position, or None if the photo has none."""
    try:
        with Image.open(io.BytesIO(data)) as img:
            exif = img.getexif()
            gps = exif.get_ifd(_GPS_IFD)
            if not gps:
                return None
            lat = _to_degrees(gps.get(_LAT))
            lon = _to_degrees(gps.get(_LON))
            if lat is None or lon is None:
                return None
            if str(gps.get(_LAT_REF, "N")).upper().startswith("S"):
                lat = -lat
            if str(gps.get(_LON_REF, "E")).upper().startswith("W"):
                lon = -lon
            taken = exif.get_ifd(_EXIF_IFD).get(_DATETIME_ORIGINAL)
    except Exception:
        # Unreadable metadata is the same as no metadata.
        return None

    # 0,0 is what some cameras write when they had no fix.
    if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0):
        return None
    return PhotoGPS(latitude=round(lat, 6), longitude=round(lon, 6),
                    taken_at=str(taken) if taken else None)


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres (haversine)."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# How the complaint's coordinates were obtained, and how the report words it.
LOCATION_SOURCES = {
    "photo": "Photo's embedded GPS (checked against the image file)",
    "device": "Device GPS when the photo was taken in the app",
    "map": "Pinned on the map by the citizen",
}


def source_label(source: Optional[str]) -> str:
    return LOCATION_SOURCES.get(source or "", "Not recorded")


# A phone's own GPS fix wanders by a few metres, and the frontend rounds; a
# "photo" location further than this from the photo's metadata did not come
# from the photo.
PHOTO_MATCH_TOLERANCE_M = 100.0
# For hand-pinned or device locations, a photo whose embedded GPS is this far
# away is worth flagging on the report - but not refusing, because a citizen
# may legitimately photograph a road and pin it correctly from elsewhere.
PHOTO_DISAGREES_WARN_M = 1_000.0


def check_location_source(source: Optional[str], latitude: float, longitude: float,
                          image_bytes: bytes) -> dict:
    """
    Validate the declared location source against the photo itself.

    Returns {"source", "source_label", "photo_taken_at", "warning"}. Raises
    LocationSourceError when the client claims the coordinates came from the
    photo and the photo says otherwise - the one case where trusting the
    client would put a false statement on a document sent to GHMC.
    """
    from app.utils.errors import LocationSourceError  # local: avoid import cycle

    source = (source or "").strip().lower() or None
    if source is not None and source not in LOCATION_SOURCES:
        raise LocationSourceError(
            "location_source must be one of: %s." % ", ".join(LOCATION_SOURCES))

    gps = read_photo_gps(image_bytes)
    warning = None

    if source == "photo":
        if gps is None:
            raise LocationSourceError(
                "This photo has no location saved in it, so its location cannot be "
                "used. Pin the spot on the map instead.")
        gap = distance_m(latitude, longitude, gps.latitude, gps.longitude)
        if gap > PHOTO_MATCH_TOLERANCE_M:
            raise LocationSourceError(
                "The coordinates sent are %.0f m from the location saved in the photo. "
                "Use the photo's location or pin the spot on the map." % gap,
                details={"distance_m": round(gap)})
    elif gps is not None:
        gap = distance_m(latitude, longitude, gps.latitude, gps.longitude)
        if gap > PHOTO_DISAGREES_WARN_M:
            warning = ("The photo's own saved location is %.1f km from the location "
                       "given for this complaint." % (gap / 1000.0))

    return {
        "source": source,
        "source_label": source_label(source),
        "photo_taken_at": gps.taken_at if gps else None,
        "warning": warning,
    }
