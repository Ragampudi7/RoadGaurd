"""Tests for input validation and the image/PDF services."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from app.config import get_settings
from app.services import image_service
from app.utils.errors import (
    ImageDimensionError,
    InvalidCoordinateError,
    InvalidImageError,
    UnsupportedImageTypeError,
)
from app.utils.validation import (
    decode_image,
    safe_filename,
    validate_coordinates,
    validate_declared_type,
)
from tests.conftest import SAMPLE_DETECTIONS, make_jpeg


# --- coordinates -----------------------------------------------------------


def test_valid_coordinates_pass_through():
    assert validate_coordinates(17.4948, 78.3996) == (17.4948, 78.3996)
    assert validate_coordinates(-90, -180) == (-90.0, -180.0)
    assert validate_coordinates(90, 180) == (90.0, 180.0)


@pytest.mark.parametrize("lat,lon", [(91, 0), (-90.1, 0), (0, 181), (0, -180.5)])
def test_out_of_range_coordinates_are_rejected(lat, lon):
    with pytest.raises(InvalidCoordinateError):
        validate_coordinates(lat, lon)


def test_nan_coordinates_are_rejected():
    with pytest.raises(InvalidCoordinateError):
        validate_coordinates(float("nan"), 0.0)


def test_non_numeric_coordinates_are_rejected():
    with pytest.raises(InvalidCoordinateError):
        validate_coordinates("north", 0.0)


# --- declared type ---------------------------------------------------------


def test_pdf_upload_is_rejected_by_content_type():
    with pytest.raises(UnsupportedImageTypeError):
        validate_declared_type("report.pdf", "application/pdf")


def test_bad_extension_is_rejected():
    with pytest.raises(UnsupportedImageTypeError):
        validate_declared_type("payload.exe", "image/jpeg")


def test_normal_image_is_accepted():
    validate_declared_type("road.jpg", "image/jpeg")


def test_filenames_are_stripped_of_path_traversal():
    assert safe_filename("../../etc/passwd.jpg") == "passwd.jpg"
    assert safe_filename("C:\\Users\\me\\road.png") == "road.png"
    assert safe_filename(None) == "uploaded_image"


# --- decoding --------------------------------------------------------------


def test_decode_valid_jpeg():
    image = decode_image(make_jpeg(640, 480), get_settings())
    assert image.size == (640, 480)
    assert image.mode == "RGB"


def test_decode_rejects_non_image_bytes():
    with pytest.raises(InvalidImageError):
        decode_image(b"this is definitely not an image", get_settings())


def test_decode_rejects_a_renamed_text_file():
    # The classic attack: upload.txt renamed to upload.jpg. The declared type
    # check passes, the real decode does not.
    with pytest.raises(InvalidImageError):
        decode_image(b"%PDF-1.7 fake", get_settings())


def test_decode_rejects_tiny_images():
    with pytest.raises(ImageDimensionError):
        decode_image(make_jpeg(16, 16), get_settings())


# --- annotation ------------------------------------------------------------


def test_annotation_returns_a_new_image_of_the_same_size():
    original = Image.new("RGB", (800, 600), (100, 100, 100))
    annotated = image_service.annotate_image(original, SAMPLE_DETECTIONS)
    assert annotated.size == original.size
    assert annotated is not original
    # Something must actually have been drawn.
    assert annotated.tobytes() != original.tobytes()


def test_annotation_survives_a_box_touching_the_top_edge():
    original = Image.new("RGB", (400, 300), (100, 100, 100))
    detections = [{"class_id": 0, "class_name": "pothole", "confidence": 0.5,
                   "x1": 0, "y1": 0, "x2": 50, "y2": 50}]
    assert image_service.annotate_image(original, detections).size == (400, 300)


def test_downscale_never_upscales():
    small = Image.new("RGB", (200, 150))
    assert image_service.downscale(small, 1280).size == (200, 150)


def test_downscale_keeps_aspect_ratio():
    large = Image.new("RGB", (4000, 2000))
    assert image_service.downscale(large, 1280).size == (1280, 640)


def test_build_annotated_jpeg_produces_valid_jpeg_bytes():
    original = Image.new("RGB", (2000, 1500), (80, 80, 80))
    data, size = image_service.build_annotated_jpeg(
        original, SAMPLE_DETECTIONS, max_side=1280, quality=82
    )
    assert data[:2] == b"\xff\xd8"          # JPEG SOI marker
    assert size == (1280, 960)
    assert Image.open(io.BytesIO(data)).size == (1280, 960)
