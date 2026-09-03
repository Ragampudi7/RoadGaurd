"""
Input validation helpers.

These run *before* anything expensive happens.  The order matters:

1.  Is a file present at all?
2.  Does its declared type / extension look like an image?
3.  Is it small enough to read into memory?  (Checked while reading, so a
    50 MB upload is abandoned early instead of being buffered in full.)
4.  Does Pillow actually decode it, and is the real format allowed?
5.  Are the pixel dimensions sane?

Only after all five does the image reach YOLO.
"""

from __future__ import annotations

import io
from pathlib import PurePosixPath
from typing import Optional, Tuple

from PIL import Image, UnidentifiedImageError

from app.config import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_PILLOW_FORMATS,
    Settings,
)
from app.utils.errors import (
    EmptyImageError,
    ImageDimensionError,
    ImageTooLargeError,
    InvalidCoordinateError,
    InvalidImageError,
    MissingImageError,
    UnsupportedImageTypeError,
)

# Pillow refuses images above ~89 megapixels by default; we lower that further
# through max_image_dimension, but keep Pillow's own guard switched on.
Image.MAX_IMAGE_PIXELS = 80_000_000

_CHUNK_SIZE = 64 * 1024


def validate_coordinates(latitude: float, longitude: float) -> Tuple[float, float]:
    """Validate WGS-84 coordinates and return them as floats."""
    try:
        lat = float(latitude)
        lon = float(longitude)
    except (TypeError, ValueError) as exc:
        raise InvalidCoordinateError(
            "Latitude and longitude must be numeric values."
        ) from exc

    # NaN never compares equal to itself - this catches it.
    if lat != lat or lon != lon:
        raise InvalidCoordinateError("Latitude and longitude must be real numbers.")

    if not -90.0 <= lat <= 90.0:
        raise InvalidCoordinateError(
            "Latitude must be between -90 and 90 degrees.",
            details={"latitude": lat},
        )
    if not -180.0 <= lon <= 180.0:
        raise InvalidCoordinateError(
            "Longitude must be between -180 and 180 degrees.",
            details={"longitude": lon},
        )
    return lat, lon


def validate_declared_type(filename: Optional[str], content_type: Optional[str]) -> None:
    """Cheap first pass on the client-declared filename and MIME type."""
    if not filename and not content_type:
        raise MissingImageError()

    if content_type:
        declared = content_type.split(";")[0].strip().lower()
        if declared not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise UnsupportedImageTypeError(
                "Unsupported content type '%s'. Allowed: %s."
                % (declared, ", ".join(ALLOWED_IMAGE_CONTENT_TYPES))
            )

    if filename:
        # PurePosixPath + basename strips any directory component a client may
        # have sent ("../../etc/passwd.jpg" becomes "passwd.jpg").  We never
        # write uploads to disk, but the name reaches the PDF, so sanitise it.
        suffix = PurePosixPath(filename.replace("\\", "/")).suffix.lower()
        if suffix and suffix not in ALLOWED_IMAGE_EXTENSIONS:
            raise UnsupportedImageTypeError(
                "Unsupported file extension '%s'. Allowed: %s."
                % (suffix, ", ".join(ALLOWED_IMAGE_EXTENSIONS))
            )


def safe_filename(filename: Optional[str]) -> str:
    """Return a display-safe basename, never a path."""
    if not filename:
        return "uploaded_image"
    name = PurePosixPath(filename.replace("\\", "/")).name
    cleaned = "".join(ch for ch in name if ch.isalnum() or ch in "._- ()")
    return cleaned.strip() or "uploaded_image"


async def read_upload(upload, settings: Settings) -> bytes:
    """
    Stream an ``UploadFile`` into memory, aborting as soon as the size limit
    is exceeded so a malicious client cannot exhaust RAM.
    """
    limit = settings.max_image_size_bytes
    buffer = io.BytesIO()
    total = 0

    while True:
        chunk = await upload.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ImageTooLargeError(
                "Image exceeds the %.1f MB limit." % settings.max_image_size_mb,
                details={"max_image_size_mb": settings.max_image_size_mb},
            )
        buffer.write(chunk)

    if total == 0:
        raise EmptyImageError()
    return buffer.getvalue()


def decode_image(data: bytes, settings: Settings) -> Image.Image:
    """
    Decode raw bytes into an RGB Pillow image, verifying the *actual* format.

    ``Image.verify()`` consumes the file object, so the standard pattern is to
    verify on one handle and then reopen for real decoding.
    """
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
            detected_format = (probe.format or "").upper()
    except UnidentifiedImageError as exc:
        raise InvalidImageError(
            "The uploaded file could not be recognised as an image."
        ) from exc
    except Exception as exc:  # corrupt/truncated payloads land here
        raise InvalidImageError("The uploaded image appears to be corrupted.") from exc

    if detected_format not in ALLOWED_PILLOW_FORMATS:
        raise UnsupportedImageTypeError(
            "Image format '%s' is not supported." % (detected_format or "unknown")
        )

    try:
        image = Image.open(io.BytesIO(data))
        image = image.convert("RGB")
    except Exception as exc:
        raise InvalidImageError("The uploaded image could not be decoded.") from exc

    width, height = image.size
    if width < settings.min_image_dimension or height < settings.min_image_dimension:
        raise ImageDimensionError(
            "Image is too small (%dx%d). Minimum side is %d pixels."
            % (width, height, settings.min_image_dimension)
        )
    if width > settings.max_image_dimension or height > settings.max_image_dimension:
        raise ImageDimensionError(
            "Image is too large (%dx%d). Maximum side is %d pixels."
            % (width, height, settings.max_image_dimension)
        )
    return image
