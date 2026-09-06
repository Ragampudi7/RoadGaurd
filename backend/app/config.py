"""
Central configuration for the Automated Road Health Assessment backend.

Every tunable value lives in this one file so that changing a threshold, a
limit or a deployment detail never means hunting through the codebase.

Values come from environment variables (or a local ``.env`` file during
development) and are validated by Pydantic at startup, so a typo in an
environment variable fails loudly instead of silently misbehaving.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Tuple

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> backend/
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Road-health classification bands
# ---------------------------------------------------------------------------
# IMPORTANT - READ THIS BEFORE QUOTING THESE NUMBERS ANYWHERE:
#
# These bands are PROJECT-DEFINED.  They were chosen by this project team as a
# reasonable, easy-to-explain starting point.  They are NOT taken from IRC,
# MoRTH, GHMC or any other official road-condition standard, and no claim of
# official status should be made about them in a report or a viva.
#
# Format: (inclusive lower bound of the score band, label, hex colour for PDF)
# Bands must be listed from the highest lower-bound to the lowest.
ROAD_CONDITION_BANDS: Tuple[Tuple[float, str, str], ...] = (
    (90.0, "Good", "#1B7F3B"),        # 90.00 - 100.00
    (70.0, "Fair", "#B8860B"),        # 70.00 -  89.99
    (40.0, "Poor", "#C2560F"),        # 40.00 -  69.99
    (0.0, "Dangerous", "#B01B1B"),    #  0.00 -  39.99
)

# ---------------------------------------------------------------------------
# Road-risk model  (project-defined - see README section "Estimating road risk")
# ---------------------------------------------------------------------------
# The health score answers "how much of the frame is damaged?".  Risk answers
# "how urgently should someone go and fix it?", which is a different question:
# one large pothole is more dangerous than the same area spread over hairline
# cracks, and a low-confidence detection should not drive an emergency.
#
# NOTHING below is an official standard.  Every number is a project convention,
# chosen to be explainable, and every one of them lives here so it can be
# defended, tuned or replaced in a single place.

# Severity of ONE defect, from the share of the photograph its box covers.
# (An image cannot show depth, so this is an extent proxy, never a depth claim.)
DEFECT_SEVERITY_BANDS: Tuple[Tuple[float, str, str], ...] = (
    (8.0, "Critical", "#8B0000"),   # box covers >= 8% of the frame
    (3.0, "High", "#B01B1B"),
    (1.0, "Medium", "#C2560F"),
    (0.0, "Minor", "#5A6470"),
)
SEVERITY_ORDER: Tuple[str, ...] = ("Minor", "Medium", "High", "Critical")

# A detection the model is unsure about is demoted one severity band, so a big
# low-confidence blob cannot manufacture a "Critical" finding.
LOW_CONFIDENCE_DOWNGRADE_BELOW: float = 0.40

# How hazardous each defect class is to a road user, relative to a pothole.
# Keys are matched as substrings of the model's class name, so "d40_pothole"
# and "pothole" both score 1.0. Add your own classes here after training.
DEFECT_CLASS_WEIGHTS: Dict[str, float] = {
    "pothole": 1.00,
    "rut": 0.85,
    "depression": 0.85,
    "ravel": 0.70,
    "manhole": 0.70,
    "alligator": 0.65,
    "crack": 0.55,
    "patch": 0.45,
}
DEFAULT_CLASS_WEIGHT: float = 0.75

# Risk Index bands -> label, colour, grievance tier, response window.
RISK_BANDS: Tuple[Tuple[float, str, str, str, str], ...] = (
    (75.0, "Critical", "#8B0000", "Priority-1", "Immediate action - within 48 hours"),
    (50.0, "High", "#B01B1B", "Priority-2", "Remediate within 7 days"),
    (25.0, "Moderate", "#C2560F", "Priority-3", "Remediate within 30 days"),
    (0.0, "Low", "#1B7F3B", "Routine", "Include in the routine maintenance cycle"),
)

# Suggested remediation per (class family, severity). These are common municipal
# maintenance practices offered as a starting point for the engineering wing -
# they are NOT an engineering directive, and the report says so.
RECOMMENDED_ACTIONS: Dict[str, Dict[str, str]] = {
    "pothole": {
        "Critical": "Barricade, excavate and full-depth patch with hot-mix asphalt",
        "High": "Hot-mix / cold-mix asphalt fill with mechanical compaction",
        "Medium": "Edge trimming, tack coat and patch sealing",
        "Minor": "Localised surface levelling during the next maintenance round",
    },
    "crack": {
        "Critical": "Mill and resurface the affected stretch",
        "High": "Bituminous slurry seal over the cracked area",
        "Medium": "Crack routing and hot sealant application",
        "Minor": "Crack sealing during routine maintenance",
    },
    "default": {
        "Critical": "Site inspection by the engineering wing, then full-depth repair",
        "High": "Surface repair and sealing of the affected area",
        "Medium": "Patch repair during the next maintenance round",
        "Minor": "Monitor and include in routine maintenance",
    },
}


# Image formats we are willing to decode.  Anything else is rejected before a
# single byte is handed to Pillow or YOLO.
ALLOWED_IMAGE_CONTENT_TYPES: Tuple[str, ...] = (
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
)
ALLOWED_IMAGE_EXTENSIONS: Tuple[str, ...] = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".bmp",
)
# Pillow's own format names, checked after decoding (defence in depth: a
# client can lie about Content-Type, it cannot lie about the actual bytes).
ALLOWED_PILLOW_FORMATS: Tuple[str, ...] = ("JPEG", "PNG", "WEBP", "BMP", "MPO")


class Settings(BaseSettings):
    """All runtime configuration, loaded from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        # Frees up the ``model_*`` prefix for our own field names.
        protected_namespaces=("settings_",),
    )

    # -- Application ------------------------------------------------------
    app_name: str = "Automated Road Health Assessment & Grievance Tool"
    app_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # -- YOLO model -------------------------------------------------------
    model_path: str = "weights/best.pt"
    # If best.pt is missing, may we fall back to a generic pretrained model?
    # This keeps the API usable while the real model is still being trained.
    # The fallback detects COCO objects (person, car, ...), NOT road defects,
    # so every response and PDF produced in this mode is clearly marked.
    allow_pretrained_fallback: bool = True
    fallback_model_name: str = "yolo11n.pt"
    confidence_threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    max_detections: int = Field(default=100, ge=1, le=1000)
    # Longest side YOLO runs on. Our weights/best.pt was TRAINED at 416,
    # so serving at 416 matches train and inference. Measured 45.7 ms per
    # image on CPU at this size. Change it only if you retrain to match.
    inference_image_size: int = Field(default=416, ge=320, le=1280)

    # -- Upload limits ----------------------------------------------------
    max_image_size_mb: float = Field(default=10.0, gt=0.0, le=50.0)
    min_image_dimension: int = Field(default=64, ge=1)
    # Guards against decompression-bomb images.
    max_image_dimension: int = Field(default=8000, ge=256)
    # The annotated image embedded in the PDF is downscaled to this longest
    # side, which keeps the PDF small enough to base64 into a JSON response.
    max_annotated_dimension: int = Field(default=1280, ge=320, le=4096)
    annotated_jpeg_quality: int = Field(default=82, ge=40, le=95)

    # -- Road-risk model --------------------------------------------------
    # Each component is scored 0-100 by dividing the measured value by its
    # "full scale" - the value at which that component is considered maxed out.
    risk_extent_full_scale: float = Field(default=25.0, gt=0.0)      # % of frame damaged
    risk_severity_full_scale: float = Field(default=10.0, gt=0.0)    # % of frame in ONE box
    risk_density_full_scale: int = Field(default=8, ge=1)            # number of defects
    # Weights must be meaningful relative to each other; they are normalised.
    risk_weight_extent: float = Field(default=0.50, ge=0.0)
    risk_weight_severity: float = Field(default=0.30, ge=0.0)
    risk_weight_density: float = Field(default=0.20, ge=0.0)

    # -- Report extras ----------------------------------------------------
    include_defect_crops: bool = True
    max_defect_crops: int = Field(default=6, ge=0, le=12)
    crop_thumbnail_side: int = Field(default=360, ge=120, le=800)

    # -- Scoring ----------------------------------------------------------
    # "sum"   -> add every bounding-box area (the project specification).
    # "union" -> count each overlapping pixel once (see scoring_service).
    area_method: str = "sum"

    # -- CORS -------------------------------------------------------------
    frontend_url: str = "http://localhost:3000"
    # Comma-separated list of any additional origins (Vercel previews, etc.)
    extra_cors_origins: str = ""

    # -- Report wording ---------------------------------------------------
    municipal_authority: str = "Greater Hyderabad Municipal Corporation (GHMC)"
    engineering_wing: str = "Roads & Maintenance Division"
    complaint_region: str = "Hyderabad, Telangana, India"
    report_timezone_offset_minutes: int = 330  # IST (UTC+05:30)

    # -- Performance ------------------------------------------------------
    # A free Render instance has ~0.1 CPU and 512 MB RAM. Serialising
    # inference protects it from being OOM-killed by concurrent uploads.
    max_concurrent_inferences: int = Field(default=1, ge=1, le=8)

    @field_validator("area_method")
    @classmethod
    def _validate_area_method(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"sum", "union"}:
            raise ValueError("AREA_METHOD must be either 'sum' or 'union'")
        return value

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        value = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if value not in allowed:
            raise ValueError("LOG_LEVEL must be one of " + ", ".join(sorted(allowed)))
        return value

    # -- Database (optional) ----------------------------------------------
    # Unset means persistence is disabled and /analyze still works. Managed
    # providers hand out postgres:// or postgresql:// URLs with ?sslmode=require;
    # both are normalised for asyncpg in app/db/base.py.
    database_url: str | None = None

    # -- Auth ---------------------------------------------------------------
    # MUST be set in production. The default below is a development convenience
    # only: a known secret means anyone can mint a valid token, so the app
    # refuses to start with it when ENVIRONMENT=production.
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_expires_hours: int = Field(default=72, ge=1, le=720)

    # -- Derived helpers --------------------------------------------------
    @property
    def model_file(self) -> Path:
        """Absolute path to the trained weights file."""
        path = Path(self.model_path).expanduser()
        if not path.is_absolute():
            path = BASE_DIR / path
        return path

    @property
    def max_image_size_bytes(self) -> int:
        return int(self.max_image_size_mb * 1024 * 1024)

    @property
    def cors_origins(self) -> List[str]:
        """Origins allowed to call this API from a browser."""
        raw = [self.frontend_url] + self.extra_cors_origins.split(",")
        origins = [item.strip().rstrip("/") for item in raw if item and item.strip()]
        if "*" in origins:
            return ["*"]
        # Local development conveniences, harmless in production.
        for default in ("http://localhost:3000", "http://localhost:5173",
                        "http://127.0.0.1:3000", "http://127.0.0.1:5173"):
            if default not in origins:
                origins.append(default)
        # De-duplicate while preserving order.
        return list(dict.fromkeys(origins))

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings object (parsed once per process)."""
    return Settings()


settings = get_settings()
