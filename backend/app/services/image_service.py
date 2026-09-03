"""
Image service - decoding, annotation and encoding, all in memory.

Nothing here ever touches the filesystem.  Uploads arrive as bytes, are held
as Pillow images, and leave as JPEG bytes in a BytesIO buffer.

Why Pillow rather than OpenCV for the drawing?
* No BGR/RGB channel-order bugs, which are the classic source of "why are my
  boxes blue" mistakes.
* Real TrueType text with proper sizing, instead of OpenCV's Hershey fonts.
* ``opencv-python-headless`` is still installed (Ultralytics needs it), but by
  not importing it here we keep one less way for a deployment to fail on a
  slim Linux image that is missing libGL.
"""

from __future__ import annotations

import base64
import io
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

from app.utils.errors import ImageProcessingError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# Distinct, colour-blind-friendly box colours, picked per class id so the same
# defect class always gets the same colour within a report.
_PALETTE: Tuple[Tuple[int, int, int], ...] = (
    (255, 56, 56),    # red
    (255, 157, 0),    # orange
    (26, 147, 255),   # blue
    (0, 190, 130),    # green
    (190, 90, 255),   # violet
    (255, 214, 0),    # yellow
    (0, 214, 214),    # cyan
    (255, 105, 180),  # pink
)

# Font files that exist on most Linux images (Render), macOS and Windows.
_FONT_CANDIDATES: Tuple[str, ...] = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "C:\\Windows\\Fonts\\arialbd.ttf",
)


def _load_font(size: int):
    """Best available font at the requested size, degrading gracefully."""
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    try:
        # Pillow >= 10.1 can scale its built-in bitmap font.
        return ImageFont.load_default(size=size)
    except TypeError:  # pragma: no cover - older Pillow
        return ImageFont.load_default()


def colour_for_class(class_id: int) -> Tuple[int, int, int]:
    return _PALETTE[class_id % len(_PALETTE)]


def downscale(image: Image.Image, max_side: int) -> Image.Image:
    """Shrink so the longest side is ``max_side``. Never upscales."""
    width, height = image.size
    longest = max(width, height)
    if longest <= max_side:
        return image
    ratio = max_side / float(longest)
    new_size = (max(1, int(width * ratio)), max(1, int(height * ratio)))
    return image.resize(new_size, Image.LANCZOS)


def annotate_image(
    image: Image.Image,
    detections: Sequence[Dict[str, Any]],
    *,
    draw_index: bool = True,
    banner: Optional[str] = None,
) -> Image.Image:
    """
    Draw one labelled rectangle per detection and return a NEW image.

    Labels read like ``1. Pothole 87%``.  The number matches the detection id
    used in the API response and in the PDF's defect table, so a reader can
    tie a row in the table back to a box in the picture.
    """
    try:
        annotated = image.convert("RGB").copy()
        draw = ImageDraw.Draw(annotated)
        width, height = annotated.size

        # Scale line width and text with the image so a 4000px photo and a
        # 640px photo both look right.
        scale = max(width, height) / 1000.0
        line_width = max(2, int(round(3 * scale)))
        font_size = max(13, int(round(18 * scale)))
        font = _load_font(font_size)
        pad = max(3, int(round(4 * scale)))

        for index, det in enumerate(detections, start=1):
            x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
            colour = colour_for_class(int(det.get("class_id", 0)))

            draw.rectangle([x1, y1, x2, y2], outline=colour, width=line_width)

            label = "%s %d%%" % (
                str(det.get("class_name", "defect")).replace("_", " ").title(),
                int(round(float(det.get("confidence", 0.0)) * 100)),
            )
            if draw_index:
                label = "%d. %s" % (index, label)

            left, top, right, bottom = draw.textbbox((0, 0), label, font=font)
            text_w, text_h = right - left, bottom - top

            # Prefer the label above the box; drop it inside if there is no room.
            box_top = y1 - text_h - 2 * pad
            if box_top < 0:
                box_top = y1 + line_width
            box_left = min(x1, max(0, width - text_w - 2 * pad))

            draw.rectangle(
                [box_left, box_top, box_left + text_w + 2 * pad, box_top + text_h + 2 * pad],
                fill=colour,
            )
            draw.text(
                (box_left + pad - left, box_top + pad - top),
                label,
                fill=(255, 255, 255),
                font=font,
            )

        if banner:
            _draw_banner(draw, annotated.size, banner, scale)

        return annotated
    except Exception as exc:
        logger.exception("Annotation failed: %s", exc)
        raise ImageProcessingError("The annotated image could not be created.") from exc


def _draw_banner(draw: ImageDraw.ImageDraw, size: Tuple[int, int], text: str, scale: float) -> None:
    """A red strip across the top - used to mark demonstration-mode output."""
    width, _height = size
    font = _load_font(max(14, int(round(20 * scale))))
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    strip_height = (bottom - top) + int(round(16 * scale))
    draw.rectangle([0, 0, width, strip_height], fill=(176, 27, 27))
    draw.text(
        ((width - (right - left)) / 2 - left, (strip_height - (bottom - top)) / 2 - top),
        text,
        fill=(255, 255, 255),
        font=font,
    )


def to_jpeg_bytes(image: Image.Image, quality: int = 82) -> bytes:
    """Encode a Pillow image to JPEG bytes without ever writing to disk."""
    try:
        buffer = io.BytesIO()
        image.convert("RGB").save(
            buffer, format="JPEG", quality=quality, optimize=True, progressive=True
        )
        return buffer.getvalue()
    except Exception as exc:
        logger.exception("JPEG encoding failed: %s", exc)
        raise ImageProcessingError("The processed image could not be encoded.") from exc


def to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def build_defect_crops(
    image: Image.Image,
    detections: Sequence[Dict[str, Any]],
    *,
    max_side: int,
    quality: int,
    limit: int,
    padding: float = 0.22,
) -> List[Tuple[bytes, Tuple[int, int]]]:
    """
    A close-up JPEG of each detection, in detection order.

    Every crop is taken from a freshly annotated copy so the box and its label
    travel with the crop, and is padded outwards so the defect is shown in a
    little of its surrounding road rather than floating with no context.
    """
    if not detections or limit <= 0:
        return []

    try:
        annotated = annotate_image(image, detections)
        width, height = annotated.size
        crops: List[Tuple[bytes, Tuple[int, int]]] = []

        # The label above each box is drawn at a size proportional to the whole
        # image, so on a small box it is far wider than the box itself. Widen
        # the crop to cover it, or close-ups of small defects lose their label.
        scale = max(width, height) / 1000.0
        label_font = max(13.0, round(18 * scale))

        for index, det in enumerate(list(detections)[:limit], start=1):
            x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]
            pad = int(round(max(x2 - x1, y2 - y1) * padding)) + 6
            label_chars = len("%d. %s 100%%" % (index, str(det.get("class_name", "defect"))))
            label_width = int(round(label_chars * label_font * 0.58))
            # Extra headroom at the top: the label sits above the box.
            left = max(0, x1 - pad)
            top = max(0, y1 - pad - int(round(label_font * 1.6)))
            right = min(width, max(x2 + pad, x1 + label_width))
            bottom = min(height, y2 + pad)
            if right <= left or bottom <= top:
                continue

            crop = annotated.crop((left, top, right, bottom))
            # Letterbox every crop to one 4:3 canvas so the contact sheet in the
            # PDF is a tidy grid instead of a row of mismatched heights.
            target = (max_side, int(round(max_side * 0.75)))
            crop = ImageOps.pad(crop, target, method=Image.LANCZOS, color=(233, 236, 240))
            crops.append((to_jpeg_bytes(crop, quality=quality), crop.size))

        return crops
    except ImageProcessingError:
        raise
    except Exception as exc:
        logger.exception("Defect crop extraction failed: %s", exc)
        raise ImageProcessingError("The defect close-ups could not be created.") from exc


def build_annotated_jpeg(
    image: Image.Image,
    detections: Sequence[Dict[str, Any]],
    *,
    max_side: int,
    quality: int,
    banner: Optional[str] = None,
) -> Tuple[bytes, Tuple[int, int]]:
    """
    Annotate at full resolution, then downscale once for delivery.

    Annotating first keeps the box coordinates trivially correct (they are in
    original-image space); downscaling afterwards keeps the JPEG that goes
    into the PDF and into the JSON response small.
    """
    annotated = annotate_image(image, detections, banner=banner)
    delivered = downscale(annotated, max_side)
    return to_jpeg_bytes(delivered, quality=quality), delivered.size
