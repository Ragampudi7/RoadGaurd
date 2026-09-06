"""
Application entry point.

Run locally:      uvicorn app.main:app --reload
Run in production: uvicorn app.main:app --host 0.0.0.0 --port $PORT

The YOLO model is loaded exactly once, during startup, and reused for every
request. Nothing is loaded per-request.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.config import get_settings
from app.services.detection_service import get_detector
from app.api.auth import router as auth_router
from app.api.reports import router as reports_router
from app.db.base import create_all, database_enabled, dispose_engine, init_engine
from app.utils.errors import AppError
from app.utils.logging_config import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

DESCRIPTION = """
Backend for the **Automated Road Health Assessment & Grievance Tool**.

A citizen uploads a road photograph together with the GPS coordinates captured
by the browser. The service detects road defects with a YOLO model, measures how
much of the frame they cover, converts that into a Road Health Score, and returns
both the structured findings and a complaint-ready PDF report.

* `GET /` - status
* `GET /health` - health probe, reports which model is loaded
* `POST /analyze` - the full pipeline
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the model once at startup; release it at shutdown."""
    logger.info("Starting %s v%s (%s)", settings.app_name, settings.app_version, settings.environment)
    logger.info("Weights path: %s", settings.model_file)
    logger.info("Confidence: %.2f | IoU: %.2f | Area method: %s",
                settings.confidence_threshold, settings.iou_threshold, settings.area_method)
    logger.info("CORS origins: %s", ", ".join(settings.cors_origins))

    # Persistence is optional. If DATABASE_URL is unset the API still serves
    # /analyze exactly as before; only the report endpoints answer 503.
    if database_enabled(settings):
        if settings.environment == "production":
            if settings.jwt_secret == "dev-only-insecure-secret-change-me":
                raise RuntimeError(
                    "JWT_SECRET is still the development default. Anyone could mint "
                    "a valid session token. Set JWT_SECRET before deploying."
                )
            # HS256 keys shorter than the hash output weaken the signature;
            # RFC 7518 3.2 puts the floor at 32 bytes.
            if len(settings.jwt_secret.encode()) < 32:
                raise RuntimeError(
                    "JWT_SECRET must be at least 32 bytes. Generate one with: "
                    "python3 -c \"import secrets; print(secrets.token_urlsafe(48))\""
                )
        init_engine(settings)
        await create_all()
        logger.info("Persistence enabled")
    else:
        logger.info("DATABASE_URL not set - reports will not be persisted")

    detector = get_detector()
    detector.load()
    if not detector.is_ready:
        logger.warning(
            "No detection model loaded - /analyze will answer 503 until weights are available. %s",
            detector.load_error or "",
        )
    yield
    detector.unload()
    await dispose_engine()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.app_name,
    description=DESCRIPTION,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# The frontend is deployed separately (Vercel, Netlify, ...), so the browser
# needs explicit permission to call this origin. Configure via FRONTEND_URL and
# EXTRA_CORS_ORIGINS - never hardcode a deployment URL in the source.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=3600,
)

# The /analyze response carries a base64 PDF; gzip cuts several hundred KB off
# the wire on a slow mobile connection for almost no CPU cost.
app.add_middleware(GZipMiddleware, minimum_size=2048)

app.include_router(router)
app.include_router(auth_router)
app.include_router(reports_router)


# ---------------------------------------------------------------------------
# Error handling - a Python traceback must never reach the client.
# ---------------------------------------------------------------------------


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    log = logger.warning if exc.status_code < 500 else logger.error
    log("%s %s -> %s: %s", request.method, request.url.path, exc.error_code, exc.message)
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Turn FastAPI's field-level errors into one readable message."""
    friendly = {
        "image": "An image file is required in the 'image' form field.",
        "latitude": "A numeric 'latitude' form field is required (-90 to 90).",
        "longitude": "A numeric 'longitude' form field is required (-180 to 180).",
    }
    messages = []
    for error in exc.errors():
        location = [str(part) for part in error.get("loc", []) if part not in ("body", "query")]
        field = location[-1] if location else "request"
        messages.append(friendly.get(field, "%s: %s" % (field, error.get("msg", "invalid value"))))

    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "request_invalid",
                "message": " ".join(dict.fromkeys(messages)) or "The request could not be validated.",
            },
        },
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": "http_error_%d" % exc.status_code,
                "message": str(exc.detail) if exc.detail else "Request failed.",
            },
        },
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Full detail goes to the server log; the client gets a generic message.
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "internal_error",
                "message": "An unexpected server error occurred. Please try again.",
            },
        },
    )
