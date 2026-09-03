"""
Pydantic models describing everything this API returns.

Keeping the response shape in one typed place means FastAPI can generate
accurate OpenAPI docs at /docs, and a frontend developer can read the
contract without reading the implementation.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


class BoundingBox(BaseModel):
    """Pixel coordinates in the ORIGINAL uploaded image, top-left origin."""

    x1: int = Field(..., description="Left edge, pixels")
    y1: int = Field(..., description="Top edge, pixels")
    x2: int = Field(..., description="Right edge, pixels")
    y2: int = Field(..., description="Bottom edge, pixels")

    @property
    def width(self) -> int:
        return max(0, self.x2 - self.x1)

    @property
    def height(self) -> int:
        return max(0, self.y2 - self.y1)

    @property
    def area(self) -> int:
        return self.width * self.height

    def as_list(self) -> List[int]:
        return [self.x1, self.y1, self.x2, self.y2]


class Detection(BaseModel):
    """One defect found by the model."""

    id: int = Field(..., description="1-based index, matches the PDF and the label drawn on the image")
    class_id: int = Field(..., description="Numeric class index reported by the model")
    class_name: str = Field(..., description="Class name from the model's own label map")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model confidence, 0.0 - 1.0")
    bbox: List[int] = Field(..., description="[x1, y1, x2, y2] in original-image pixels")
    area: int = Field(..., description="Bounding-box area in pixels")
    area_percentage: float = Field(..., description="This box's area as a percentage of the whole image")
    severity: str = Field(default="Minor", description="Minor | Medium | High | Critical - project-defined, derived from how much of the frame the box covers")
    severity_rank: int = Field(default=0, description="0 = Minor ... 3 = Critical, for sorting")
    severity_colour: str = Field(default="#5A6470", description="Hex colour used for this severity in the report")
    recommended_action: str = Field(default="", description="Suggested remediation - a starting point for the engineering wing, not an engineering directive")


class Location(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    maps_url: str = Field(..., description="Ready-to-open Google Maps link for the coordinates")


class ImageInfo(BaseModel):
    filename: str
    width: int
    height: int
    area_pixels: int
    sha256: str = Field(default="", description="SHA-256 of the uploaded bytes - an evidence-integrity digest anyone can recompute from the same file")


class AreaBreakdown(BaseModel):
    """
    Both ways of measuring defect area, so the number in the report can be
    justified and the alternative is always visible.

    ``summed``  - every bounding box added up (the project specification).
                  Overlapping boxes are counted twice, so this can exceed the
                  true damaged area, and in extreme cases exceed 100%.
    ``union``   - each damaged pixel counted once, overlaps removed.
    """

    method: str = Field(..., description="Which figure the score was computed from: 'sum' or 'union'")
    summed_area_pixels: int
    union_area_pixels: int
    summed_percentage: float
    union_percentage: float
    overlap_detected: bool = Field(..., description="True when boxes overlap, i.e. the two figures differ")


class RiskComponent(BaseModel):
    """One ingredient of the Road Risk Index, normalised to 0-100."""

    name: str
    value: float = Field(..., description="The measured quantity (percent, or a count)")
    unit: str
    value_display: str = Field(default="", description="Ready-to-print form of the measurement, e.g. '14.54% of the frame damaged'")
    full_scale: float = Field(..., description="Value at which this component scores 100")
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float = Field(..., description="Share of the final index, already normalised")


class RiskAssessment(BaseModel):
    """
    How urgently this stretch of road needs attention.

    Distinct from the health score: the score measures how much of the frame is
    damaged, risk weighs that by how hazardous the defect types are, how bad the
    single worst defect is, how many there are, and how sure the model was.
    Every constant behind it is project-defined and listed in app/config.py.
    """

    risk_index: float = Field(..., ge=0.0, le=100.0, description="0 = no concern, 100 = maximum modelled risk")
    risk_level: str = Field(..., description="Low | Moderate | High | Critical")
    risk_colour: str
    priority_tier: str = Field(..., description="Suggested grievance tier, e.g. 'Priority-2'")
    response_window: str = Field(..., description="Suggested response time for that tier")
    components: List[RiskComponent] = Field(default_factory=list)
    hazard_factor: float = Field(..., description="Area-weighted mean hazard weight of the detected classes (0-1)")
    confidence_factor: float = Field(..., description="Mean detection confidence, floored (0.5-1.0)")
    max_severity: str = Field(..., description="Severity of the single worst defect")
    dominant_defect: Optional[str] = Field(default=None, description="Class contributing the most damaged area")
    summary: str = Field(..., description="One-line, plain-language reading of the index")


class ModelInfo(BaseModel):
    """Where the detections actually came from - important for honesty."""

    status: str = Field(
        ...,
        description="'trained' = your own road-defect weights; 'pretrained_fallback' = generic COCO model; 'unavailable' = no model loaded",
    )
    name: str
    task: str = "detect"
    classes: List[str] = Field(default_factory=list)
    device: str = "cpu"
    confidence_threshold: float
    iou_threshold: float
    is_road_defect_model: bool = Field(
        ..., description="False means the results are NOT road-defect detections and the report is not submittable"
    )


class MediaPayload(BaseModel):
    """
    A binary file returned inside JSON.

    ``data`` is standard base64 (no data-URI prefix).  In the browser:

        const blob = await (await fetch(`data:${p.mime_type};base64,${p.data}`)).blob();
        const url  = URL.createObjectURL(blob);
    """

    filename: str
    mime_type: str
    encoding: str = "base64"
    size_bytes: int
    data: str


# ---------------------------------------------------------------------------
# Endpoint responses
# ---------------------------------------------------------------------------


class RootResponse(BaseModel):
    status: str = "ok"
    message: str
    version: str
    docs_url: str = "/docs"


class HealthResponse(BaseModel):
    status: str = Field(..., description="'ok' when the API can serve analysis requests, 'degraded' otherwise")
    version: str
    uptime_seconds: float
    model_loaded: bool
    model: ModelInfo


class AnalyzeResponse(BaseModel):
    success: bool = True
    request_id: str
    analysed_at: str = Field(..., description="ISO-8601 timestamp of the assessment")

    road_health_score: float = Field(..., ge=0.0, le=100.0, description="100 - defect_percentage, floored at 0")
    road_condition: str = Field(..., description="Good | Fair | Poor | Dangerous")
    defect_percentage: float = Field(..., ge=0.0, description="Share of the image covered by defect boxes")

    total_defects: int
    defect_counts: Dict[str, int] = Field(default_factory=dict, description="Per-class counts, e.g. {'pothole': 3}")
    detections: List[Detection] = Field(default_factory=list)

    risk: RiskAssessment

    location: Location
    image: ImageInfo
    area_breakdown: AreaBreakdown
    model_info: ModelInfo

    complaint_description: str
    addressed_to: str

    processing_time_ms: int
    warnings: List[str] = Field(default_factory=list)

    annotated_image: Optional[MediaPayload] = Field(
        default=None, description="JPEG with bounding boxes drawn, base64-encoded"
    )
    defect_crops: List[MediaPayload] = Field(
        default_factory=list,
        description="Close-up JPEG crop of each detection, in the same order as `detections`",
    )
    report: Optional[MediaPayload] = Field(
        default=None, description="The complaint-ready PDF, base64-encoded"
    )


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, object]] = None


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
