"""
Typed application errors.

Every expected failure in this backend raises an :class:`AppError` subclass.
``app/main.py`` registers a single exception handler that turns those into a
clean JSON body with the right HTTP status code.

Why a custom hierarchy instead of raising ``HTTPException`` everywhere?
Because the service layer should not have to know it is being called over
HTTP.  Services raise domain errors; the API layer decides how to present
them.  It also guarantees one thing that matters for security: a Python
traceback is never serialised into a response.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class AppError(Exception):
    """Base class for every error this application deliberately raises."""

    status_code: int = 500
    error_code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "success": False,
            "error": {"code": self.error_code, "message": self.message},
        }
        if self.details:
            body["error"]["details"] = self.details
        return body


# --- Client mistakes (4xx) -------------------------------------------------


class MissingImageError(AppError):
    status_code = 400
    error_code = "image_missing"
    message = "No image file was uploaded. Send a file in the 'image' form field."


class EmptyImageError(AppError):
    status_code = 400
    error_code = "image_empty"
    message = "The uploaded file is empty."


class UnsupportedImageTypeError(AppError):
    status_code = 415
    error_code = "image_type_unsupported"
    message = "Unsupported image format. Use JPG, PNG, WEBP or BMP."


class InvalidImageError(AppError):
    status_code = 422
    error_code = "image_invalid"
    message = "The uploaded file is not a readable image."


class ImageTooLargeError(AppError):
    status_code = 413
    error_code = "image_too_large"
    message = "The uploaded image is larger than the allowed limit."


class ImageDimensionError(AppError):
    status_code = 422
    error_code = "image_dimensions_invalid"
    message = "The uploaded image resolution is outside the accepted range."


class InvalidCoordinateError(AppError):
    status_code = 422
    error_code = "coordinates_invalid"
    message = "The supplied GPS coordinates are invalid."


# --- Server-side failures (5xx) -------------------------------------------


class ModelUnavailableError(AppError):
    status_code = 503
    error_code = "model_unavailable"
    message = (
        "The road-defect detection model is not available on this server. "
        "Please try again later."
    )


class InferenceError(AppError):
    status_code = 500
    error_code = "inference_failed"
    message = "The detection model failed while analysing the image."


class ImageProcessingError(AppError):
    status_code = 500
    error_code = "image_processing_failed"
    message = "The image could not be processed."


class ReportGenerationError(AppError):
    status_code = 500
    error_code = "report_generation_failed"
    message = "The PDF report could not be generated."


class ServerBusyError(AppError):
    status_code = 503
    error_code = "server_busy"
    message = "The server is busy processing other images. Please retry shortly."
