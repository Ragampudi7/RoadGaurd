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


# ---------------------------------------------------------------------------
# Accounts, sessions and persistence
# ---------------------------------------------------------------------------


class UnauthenticatedError(AppError):
    status_code = 401
    error_code = "unauthenticated"
    message = "Sign in to continue."


class InvalidTokenError(AppError):
    status_code = 401
    error_code = "invalid_token"
    message = "Your session has expired. Sign in again."


class InvalidCredentialsError(AppError):
    status_code = 401
    error_code = "invalid_credentials"
    # Deliberately identical whether the email is unknown or the password is
    # wrong: two different messages turn the login form into an oracle for
    # discovering which addresses have accounts.
    message = "Email or password is incorrect."


class EmailTakenError(AppError):
    status_code = 409
    error_code = "email_taken"
    message = "An account with that email already exists."


class AccountDisabledError(AppError):
    status_code = 403
    error_code = "account_disabled"
    message = "This account is disabled."


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"
    message = "You do not have permission to do that."


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"
    message = "That record does not exist."


class DatabaseUnavailableError(AppError):
    status_code = 503
    error_code = "database_unavailable"
    message = (
        "Persistence is not configured on this server. Analysis still works, "
        "but reports cannot be saved."
    )
