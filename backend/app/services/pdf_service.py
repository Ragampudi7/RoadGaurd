"""
PDF report generation with ReportLab.

A structured, three-part grievance document:

    Page 1  Assessment summary   - health gauge, headline tiles, the road-risk
                                   panel, capture telemetry, municipal routing
                                   and the official grievance statement
    Page 2  Inventory & analytics- per-defect table with severity and suggested
                                   remediation, plus three charts
    Page 3  Visual evidence      - annotated photograph, defect close-ups and
                                   the methodology panel

Everything is built in a ``BytesIO`` buffer - no temporary files, nothing
written to disk, nothing to clean up. Every chart is drawn with ReportLab's own
vector primitives, so they stay sharp at any zoom and add no dependency.

(ReportLab rather than an HTML-to-PDF engine such as WeasyPrint: those need
Cairo/Pango system libraries that Render's plain Python runtime does not ship,
which would force a Docker deployment. ReportLab is pure Python.)
"""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Polygon, Rect, String, Wedge
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image as RLImage,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from app.config import DEFECT_SEVERITY_BANDS, RISK_BANDS, ROAD_CONDITION_BANDS
from app.utils.errors import ReportGenerationError
from app.utils.logging_config import get_logger

logger = get_logger(__name__)

# --- palette ---------------------------------------------------------------
INK = colors.HexColor("#16202B")
MUTED = colors.HexColor("#64748B")
FAINT = colors.HexColor("#94A3B8")
LINE = colors.HexColor("#E3E7ED")
PANEL = colors.HexColor("#F7F9FB")
TRACK = colors.HexColor("#EDF1F5")
BRAND = colors.HexColor("#0F2C4C")
ACCENT = colors.HexColor("#1D4ED8")
ALERT = colors.HexColor("#B01B1B")
WHITE = colors.white

# Pale companions to every band colour used in the meters.
TINTS: Dict[str, str] = {
    "#8B0000": "#F7DCDC",
    "#B01B1B": "#FAE3E3",
    "#C2560F": "#FBE8DA",
    "#B8860B": "#F8EFD3",
    "#1B7F3B": "#DDF1E3",
    "#5A6470": "#E7EAEE",
}

PAGE_MARGIN = 15 * mm
RADIUS = [5, 5, 5, 5]


def _tint(hex_colour: str) -> colors.Color:
    return colors.HexColor(TINTS.get(hex_colour.upper(), "#EEF2F6"))


def _bands(raw: Sequence[Sequence[Any]]) -> List[Tuple[float, str, str]]:
    """Normalise any config band tuple to (lower bound, label, colour)."""
    return [(float(row[0]), str(row[1]), str(row[2])) for row in raw]


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()["Normal"]

    def make(name: str, **kwargs: Any) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base, **kwargs)

    return {
        "title": make("title", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=INK),
        "tagline": make("tagline", fontName="Helvetica", fontSize=7.8, leading=11, textColor=MUTED),
        "ref": make("ref", fontName="Courier-Bold", fontSize=8, leading=11,
                    textColor=MUTED, alignment=TA_RIGHT),
        "section": make("section", fontName="Helvetica-Bold", fontSize=9.5, leading=12, textColor=INK),
        "eyebrow": make("eyebrow", fontName="Helvetica-Bold", fontSize=7.4, leading=10, textColor=MUTED),
        "eyebrow_c": make("eyebrow_c", fontName="Helvetica-Bold", fontSize=7.4, leading=10,
                          textColor=MUTED, alignment=TA_CENTER),
        "kpi": make("kpi", fontName="Helvetica-Bold", fontSize=17.5, leading=21, textColor=INK),
        "kpisub": make("kpisub", fontName="Helvetica", fontSize=7, leading=9.5, textColor=FAINT),
        "big": make("big", fontName="Helvetica-Bold", fontSize=26, leading=29,
                    textColor=INK, alignment=TA_CENTER),
        "body": make("body", fontName="Helvetica", fontSize=9, leading=13.5,
                     textColor=INK, alignment=TA_JUSTIFY),
        "key": make("key", fontName="Helvetica", fontSize=8.2, leading=11.5, textColor=MUTED),
        "val": make("val", fontName="Helvetica-Bold", fontSize=8.2, leading=11.5, textColor=INK),
        "mono": make("mono", fontName="Courier", fontSize=7, leading=10, textColor=MUTED),
        "cell": make("cell", fontName="Helvetica", fontSize=8, leading=10.5, textColor=INK),
        "cellb": make("cellb", fontName="Helvetica-Bold", fontSize=8, leading=10.5, textColor=INK),
        "th": make("th", fontName="Helvetica-Bold", fontSize=7, leading=9.5, textColor=MUTED),
        "note": make("note", fontName="Helvetica", fontSize=7.2, leading=10.2,
                     textColor=MUTED, alignment=TA_JUSTIFY),
        "cap": make("cap", fontName="Helvetica", fontSize=7.2, leading=9.5, textColor=MUTED),
        "cap_c": make("cap_c", fontName="Helvetica", fontSize=6.9, leading=9,
                      textColor=MUTED, alignment=TA_CENTER),
        "chip": make("chip", fontName="Helvetica-Bold", fontSize=8, leading=10.5,
                     textColor=WHITE, alignment=TA_CENTER),
        "warn": make("warn", fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=WHITE),
    }


# ---------------------------------------------------------------------------
# Layout primitives
# ---------------------------------------------------------------------------


def _plain(rows: List[List[Any]], widths: List[float], **pad: float) -> Table:
    """A table with every default padding stripped - used purely for layout."""
    table = Table(rows, colWidths=widths)
    table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN", (0, 0), (-1, -1), pad.get("valign", "TOP")),
    ]))
    return table


def _stack(items: List[Any], width: float) -> Table:
    return _plain([[item] for item in items], [width])


def _card(items: List[Any], width: float, *, padding: float = 9,
          background=WHITE, border=LINE) -> Table:
    table = Table([[item] for item in items], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.7, border),
        ("ROUNDEDCORNERS", RADIUS),
        ("LEFTPADDING", (0, 0), (-1, -1), padding),
        ("RIGHTPADDING", (0, 0), (-1, -1), padding),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("TOPPADDING", (0, 0), (-1, 0), padding),
        ("BOTTOMPADDING", (0, -1), (-1, -1), padding),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _chip(text: str, hex_colour: str, style: ParagraphStyle, width: float,
          *, solid: bool = True) -> Table:
    fill = colors.HexColor(hex_colour) if solid else _tint(hex_colour)
    text_style = style if solid else ParagraphStyle(
        "chip_soft", parent=style, textColor=colors.HexColor(hex_colour))
    table = Table([[Paragraph(escape(text), text_style)]], colWidths=[width])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), fill),
        ("ROUNDEDCORNERS", [7, 7, 7, 7]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return table


def _heading(title: str, style: Dict[str, ParagraphStyle], width: float,
             right: str = "", accent=BRAND) -> Table:
    cells = [Paragraph(escape(title.upper()), style["section"])]
    widths = [width]
    if right:
        cells.append(Paragraph(escape(right), style["cap"]))
        widths = [width * 0.60, width * 0.40]
    table = Table([cells], colWidths=widths)
    table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (0, 0), 9),
        ("LEFTPADDING", (-1, 0), (-1, 0), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LINEBEFORE", (0, 0), (0, 0), 2.4, accent),
        ("LINEBELOW", (0, 0), (-1, -1), 0.7, LINE),
    ]))
    return table


def _kv(rows: Sequence[Tuple[str, Any]], style: Dict[str, ParagraphStyle],
        width: float) -> Table:
    data = []
    for key, value in rows:
        cell = value if isinstance(value, Paragraph) else Paragraph(escape(str(value)), style["val"])
        data.append([Paragraph(escape(key), style["key"]), cell])
    table = Table(data, colWidths=[width * 0.35, width * 0.65], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
    ]))
    return table


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------


def _gauge(score: float, hex_colour: str, size: float) -> Drawing:
    """270-degree donut gauge with the score in the middle."""
    drawing = Drawing(size, size)
    cx = cy = size / 2.0
    outer, start, sweep = size * 0.45, 225.0, 270.0
    inner = outer * 0.72
    fraction = max(0.0, min(1.0, score / 100.0))

    drawing.add(Wedge(cx, cy, outer, start - sweep, start, fillColor=TRACK, strokeColor=None))
    if fraction > 0.002:
        drawing.add(Wedge(cx, cy, outer, start - sweep * fraction, start,
                          fillColor=colors.HexColor(hex_colour), strokeColor=None))
    drawing.add(Circle(cx, cy, inner, fillColor=WHITE, strokeColor=None))
    # Scale the centre text with the dial so it always clears the ring.
    score_size = max(11.0, size * 0.20)
    drawing.add(String(cx, cy + score_size * 0.06, "%.2f" % score,
                       fontName="Helvetica-Bold", fontSize=score_size,
                       fillColor=INK, textAnchor="middle"))
    drawing.add(String(cx, cy - score_size * 0.78, "OUT OF 100", fontName="Helvetica",
                       fontSize=max(5.4, size * 0.075), fillColor=FAINT, textAnchor="middle"))
    return drawing


def _meter(value: float, bands: List[Tuple[float, str, str]], width: float) -> Drawing:
    """A banded 0-100 scale with a marker at the assessed value."""
    drawing = Drawing(width, 41)
    bar_y, bar_h = 14.0, 12.5
    ordered = sorted(bands, key=lambda band: band[0])
    edges = [band[0] for band in ordered] + [100.0]

    active = ordered[0][1]
    for lower, label, _colour in ordered:
        if value >= lower:
            active = label

    for index, (lower, label, colour) in enumerate(ordered):
        x = width * (lower / 100.0)
        w = width * ((edges[index + 1] - lower) / 100.0)
        live = label == active
        drawing.add(Rect(x, bar_y, w, bar_h, rx=2.5, ry=2.5,
                         fillColor=colors.HexColor(colour) if live else _tint(colour),
                         strokeColor=WHITE, strokeWidth=1.4))
        drawing.add(String(x + w / 2.0, bar_y - 9, label.upper(),
                           fontName="Helvetica-Bold" if live else "Helvetica",
                           fontSize=6.2, fillColor=INK if live else FAINT,
                           textAnchor="middle"))

    marker = max(3.0, min(width - 3.0, width * (value / 100.0)))
    drawing.add(Polygon([marker - 4.4, bar_y + bar_h + 6.5, marker + 4.4, bar_y + bar_h + 6.5,
                         marker, bar_y + bar_h + 1.0], fillColor=INK, strokeColor=None))
    anchor = "middle"
    if marker < 30:
        anchor = "start"
    elif marker > width - 30:
        anchor = "end"
    drawing.add(String(marker, bar_y + bar_h + 10.5, "%.1f / 100" % value,
                       fontName="Helvetica-Bold", fontSize=7.6, fillColor=INK,
                       textAnchor=anchor))
    return drawing


def _component_rows(components: Sequence[Any], width: float) -> Drawing:
    """One labelled bar per risk component, with its measurement and weight."""
    row_h = 21.0
    drawing = Drawing(width, row_h * max(1, len(components)))
    label_w = width * 0.24
    score_w = 40.0
    detail_w = width * 0.36
    track_w = max(30.0, width - label_w - score_w - detail_w - 10)

    for index, component in enumerate(components):
        y = drawing.height - (index + 1) * row_h + 11
        drawing.add(String(0, y, component.name, fontName="Helvetica",
                           fontSize=7.8, fillColor=INK))
        drawing.add(Rect(label_w, y - 2.4, track_w, 8, rx=4, ry=4,
                         fillColor=TRACK, strokeColor=None))
        filled = track_w * max(0.0, min(1.0, component.score / 100.0))
        if filled > 1:
            drawing.add(Rect(label_w, y - 2.4, max(4.0, filled), 8, rx=4, ry=4,
                             fillColor=BRAND, strokeColor=None))
        drawing.add(String(label_w + track_w + score_w - 4, y, "%.0f" % component.score,
                           fontName="Helvetica-Bold", fontSize=7.8, fillColor=INK,
                           textAnchor="end"))
        drawing.add(String(label_w + track_w + score_w, y, "/100",
                           fontName="Helvetica", fontSize=6.6, fillColor=FAINT))
        drawing.add(String(width, y + 3, component.value_display,
                           fontName="Helvetica", fontSize=6.8, fillColor=MUTED,
                           textAnchor="end"))
        drawing.add(String(width, y - 6, "weight %d%%" % round(component.weight * 100),
                           fontName="Helvetica", fontSize=6.4, fillColor=FAINT,
                           textAnchor="end"))
    return drawing


def _severity_chart(detections: Sequence[Any], width: float) -> Drawing:
    """Defect count per severity band."""
    bands = _bands(DEFECT_SEVERITY_BANDS)
    counts = {label: 0 for _b, label, _c in bands}
    for det in detections:
        counts[det.severity] = counts.get(det.severity, 0) + 1
    peak = max(list(counts.values()) + [1])

    row_h = 19.0
    drawing = Drawing(width, row_h * len(bands))
    label_w, value_w = 48.0, 14.0
    track_w = max(24.0, width - label_w - value_w - 6)

    for index, (_bound, label, colour) in enumerate(bands):
        count = counts.get(label, 0)
        y = drawing.height - (index + 1) * row_h + 6
        drawing.add(String(0, y, label, fontName="Helvetica", fontSize=7.6, fillColor=INK))
        drawing.add(Rect(label_w, y - 2.4, track_w, 8, rx=4, ry=4, fillColor=TRACK,
                         strokeColor=None))
        if count:
            drawing.add(Rect(label_w, y - 2.4, max(5.0, track_w * count / float(peak)), 8,
                             rx=4, ry=4, fillColor=colors.HexColor(colour), strokeColor=None))
        drawing.add(String(width, y, str(count), fontName="Helvetica-Bold", fontSize=7.6,
                           fillColor=INK if count else FAINT, textAnchor="end"))
    return drawing


def _area_chart(detections: Sequence[Any], width: float, *, limit: int = 6) -> Drawing:
    """Share of the frame taken by each individual defect."""
    items = sorted(detections, key=lambda det: det.area_percentage, reverse=True)[:limit]
    row_h = 19.0
    drawing = Drawing(width, row_h * max(1, len(items)))

    if not items:
        drawing.add(String(0, drawing.height - 13, "No defects detected.",
                           fontName="Helvetica", fontSize=7.6, fillColor=FAINT))
        return drawing

    peak = max([det.area_percentage for det in items] + [0.01])
    label_w, value_w = 78.0, 32.0
    track_w = max(24.0, width - label_w - value_w - 6)

    for index, det in enumerate(items):
        y = drawing.height - (index + 1) * row_h + 6
        name = str(det.class_name).replace("_", " ").title()
        if len(name) > 13:
            name = name[:12] + "."
        drawing.add(String(0, y, "#%d %s" % (det.id, name), fontName="Helvetica",
                           fontSize=7.4, fillColor=INK))
        drawing.add(Rect(label_w, y - 2.4, track_w, 8, rx=4, ry=4, fillColor=TRACK,
                         strokeColor=None))
        drawing.add(Rect(label_w, y - 2.4, max(5.0, track_w * det.area_percentage / peak), 8,
                         rx=4, ry=4, fillColor=colors.HexColor(det.severity_colour),
                         strokeColor=None))
        drawing.add(String(width, y, "%.2f%%" % det.area_percentage,
                           fontName="Helvetica-Bold", fontSize=7.4, fillColor=INK,
                           textAnchor="end"))
    return drawing


def _confidence_cell(confidence: float, hex_colour: str, width: float) -> Drawing:
    drawing = Drawing(width, 11)
    bar_w = width - 26
    drawing.add(Rect(0, 2, bar_w, 6.5, rx=3.2, ry=3.2, fillColor=TRACK, strokeColor=None))
    drawing.add(Rect(0, 2, max(3.5, bar_w * max(0.0, min(1.0, confidence))), 6.5,
                     rx=3.2, ry=3.2, fillColor=colors.HexColor(hex_colour), strokeColor=None))
    drawing.add(String(width, 2.5, "%d%%" % round(confidence * 100),
                       fontName="Helvetica-Bold", fontSize=7.4, fillColor=INK,
                       textAnchor="end"))
    return drawing


# ---------------------------------------------------------------------------
# Document template
# ---------------------------------------------------------------------------


class _ReportDoc(BaseDocTemplate):
    """Page frame plus the footer, which carries the reference number and nothing else."""

    def __init__(self, buffer: io.BytesIO, *, reference: str, **kwargs: Any) -> None:
        super().__init__(
            buffer, pagesize=A4,
            leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
            topMargin=PAGE_MARGIN, bottomMargin=PAGE_MARGIN + 5 * mm,
            title="Road Health & Citizen Grievance Report",
            author="Automated Road Health Assessment & Grievance Tool",
            subject="Road condition assessment, risk estimation and complaint",
            **kwargs,
        )
        self.reference = reference
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height,
                      id="body", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id="report", frames=[frame], onPage=self._footer)])

    def _footer(self, canvas, doc) -> None:
        canvas.saveState()
        y = self.bottomMargin - 4.5 * mm
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.6)
        canvas.line(self.leftMargin, y + 3.6 * mm, self.leftMargin + self.width, y + 3.6 * mm)
        canvas.setFont("Courier", 7)
        canvas.setFillColor(FAINT)
        canvas.drawString(self.leftMargin, y, "Ref: %s" % self.reference)
        canvas.restoreState()


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------


def _masthead(ctx: Dict[str, Any], style: Dict[str, ParagraphStyle], width: float) -> List[Any]:
    risk = ctx["risk"]
    left = _stack([
        Paragraph("ROAD HEALTH &amp; CITIZEN GRIEVANCE REPORT", style["title"]),
        Spacer(1, 3),
        Paragraph("Automated computer-vision assessment of road surface condition, defect "
                  "extent and remediation urgency, prepared for municipal grievance "
                  "submission.", style["tagline"]),
    ], width * 0.58)

    chip_w = width * 0.38
    right = _stack([
        _chip("CONDITION: %s" % ctx["road_condition"].upper(), ctx["condition_colour"],
              style["chip"], chip_w, solid=False),
        Spacer(1, 4),
        _chip("RISK: %s \u00b7 %s" % (risk.risk_level.upper(), risk.priority_tier),
              risk.risk_colour, style["chip"], chip_w),
        Spacer(1, 4),
        Paragraph("REF: %s" % escape(ctx["reference"]), style["ref"]),
    ], chip_w)

    head = Table([[left, right]], colWidths=[width * 0.60, width * 0.40])
    head.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), 1.1, colors.HexColor("#C7D0DA")),
    ]))

    flow: List[Any] = [head, Spacer(1, 4 * mm)]

    if not ctx["is_road_defect_model"]:
        warn = Table([[Paragraph(
            "DEMONSTRATION OUTPUT - NOT A VALID COMPLAINT. Produced with the generic "
            "pretrained model '%s' because no trained road-defect model was installed. "
            "The objects listed are not road defects. Do not submit this document."
            % escape(ctx["model_name"]), style["warn"])]], colWidths=[width])
        warn.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), ALERT),
            ("ROUNDEDCORNERS", RADIUS),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ]))
        flow += [warn, Spacer(1, 4 * mm)]
    return flow


def _tile(label: str, value: str, sub: str, style: Dict[str, ParagraphStyle],
          width: float) -> Table:
    return _card([
        Paragraph(escape(label.upper()), style["eyebrow"]),
        Spacer(1, 2),
        Paragraph(escape(value), style["kpi"]),
        Paragraph(escape(sub), style["kpisub"]),
    ], width, padding=8, background=PANEL)


def _summary_row(ctx: Dict[str, Any], style: Dict[str, ParagraphStyle], width: float) -> Table:
    risk = ctx["risk"]
    gauge_w = width * 0.28
    tiles_area = width - gauge_w - 8
    tile_w = (tiles_area - 16) / 3.0

    gauge_card = _card([
        Paragraph("ROAD HEALTH INDEX", style["eyebrow_c"]),
        _gauge(ctx["road_health_score"], ctx["condition_colour"], gauge_w - 58),
        _chip(ctx["road_condition"].upper(), ctx["condition_colour"], style["chip"],
              gauge_w - 40, solid=False),
    ], gauge_w, padding=7)

    counts = ctx["defect_counts"]
    breakdown = ", ".join(
        "%d %s%s" % (count, name.replace("_", " "), "s" if count != 1 else "")
        for name, count in list(counts.items())[:3]
    ) or "none detected"

    worst = None
    for det in ctx["detections"]:
        if worst is None or det.severity_rank > worst.severity_rank:
            worst = det

    tiles = _plain([[
        _tile("Defects detected", str(ctx["total_defects"]), breakdown, style, tile_w),
        _tile("Defect area ratio", "%.2f%%" % ctx["defect_percentage"],
              "of the photographed surface", style, tile_w),
        _tile("Highest severity", risk.max_severity,
              ("%s - tag #%d" % (worst.class_name.replace("_", " ").title(), worst.id))
              if worst else "no defects found", style, tile_w),
    ]], [tile_w + 8, tile_w + 8, tile_w])

    row = Table([[gauge_card, tiles]], colWidths=[gauge_w + 8, tiles_area])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 8),
        ("RIGHTPADDING", (1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row


def _risk_panel(ctx: Dict[str, Any], style: Dict[str, ParagraphStyle], width: float) -> Table:
    risk = ctx["risk"]
    score_w = width * 0.26
    detail_w = width - score_w - 8

    score_card = _card([
        Paragraph("ROAD RISK INDEX", style["eyebrow"]),
        Spacer(1, 3),
        Paragraph("%.1f" % risk.risk_index, style["big"]),
        Spacer(1, 3),
        _chip("%s RISK" % risk.risk_level.upper(), risk.risk_colour, style["chip"],
              score_w - 36),
        Spacer(1, 6),
        Paragraph("<b>%s</b>" % escape(risk.priority_tier), style["cellb"]),
        Paragraph(escape(risk.response_window), style["kpisub"]),
    ], score_w, padding=9, background=_tint(risk.risk_colour),
        border=colors.HexColor(risk.risk_colour))

    inner = detail_w - 18
    detail_card = _card([
        Paragraph("REMEDIATION URGENCY", style["eyebrow"]),
        Spacer(1, 2),
        _meter(risk.risk_index, _bands(RISK_BANDS), inner),
        Spacer(1, 5),
        _component_rows(risk.components, inner),
        Spacer(1, 2),
        Paragraph(
            "Weighted mean of the components above, scaled by a hazard factor of <b>%.2f</b> "
            "(how dangerous the detected classes are, area-weighted) and a confidence factor "
            "of <b>%.2f</b> (mean confidence, floored at 0.50)."
            % (risk.hazard_factor, risk.confidence_factor), style["cap"]),
    ], detail_w, padding=9)

    row = Table([[score_card, detail_card]], colWidths=[score_w + 8, detail_w])
    row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, 0), 8),
        ("RIGHTPADDING", (1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return row


def _statement(ctx: Dict[str, Any], style: Dict[str, ParagraphStyle], width: float) -> Table:
    inner = width - 22
    statement_style = ParagraphStyle("stmt", parent=style["body"], fontSize=8.5, leading=12.4)
    block = _stack([
        Paragraph("Official Citizen Grievance Statement", style["cellb"]),
        Spacer(1, 3),
        Paragraph(escape(ctx["complaint_description"]), statement_style),
        Spacer(1, 5),
        Paragraph("<b>Addressed to:</b> %s" % escape(ctx["addressed_to"]), style["cell"]),
    ], inner)
    card = Table([[block]], colWidths=[width])
    card.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBEFORE", (0, 0), (0, -1), 2.6, BRAND),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return card


def _inventory(ctx: Dict[str, Any], style: Dict[str, ParagraphStyle], width: float) -> Table:
    header = [Paragraph(text, style["th"]) for text in
              ("TAG", "CLASSIFICATION", "DETECTION CONFIDENCE", "SEVERITY",
               "FRAME AREA", "RECOMMENDED REMEDIATION")]
    widths = [33, 86, 86, 54, 46, width - 305]
    rows: List[List[Any]] = [header]

    for det in ctx["detections"]:
        severity_style = ParagraphStyle("sev", parent=style["cellb"],
                                        textColor=colors.HexColor(det.severity_colour))
        rows.append([
            Paragraph("#%d" % det.id, style["cellb"]),
            _chip(str(det.class_name).replace("_", " ").title(), det.severity_colour,
                  ParagraphStyle("cls", parent=style["cell"], alignment=TA_CENTER),
                  widths[1] - 16, solid=False),
            _confidence_cell(det.confidence, det.severity_colour, widths[2] - 14),
            Paragraph(escape(det.severity), severity_style),
            Paragraph("%.2f%%" % det.area_percentage, style["cell"]),
            Paragraph(escape(det.recommended_action), style["cell"]),
        ])

    table = Table(rows, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, colors.HexColor("#C7D0DA")),
        ("LINEBELOW", (0, 1), (-1, -2), 0.4, LINE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("ROUNDEDCORNERS", RADIUS),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _crop_grid(ctx: Dict[str, Any], style: Dict[str, ParagraphStyle],
               width: float) -> Optional[Table]:
    crops = ctx.get("defect_crops") or []
    detections = list(ctx["detections"])
    if not crops:
        return None

    # Four across reads well up to four crops; beyond that a three-across grid
    # avoids a lonely single card on the second row.
    columns = 4 if len(crops) <= 4 else 3
    cell_w = (width - (columns - 1) * 8) / columns
    image_w = cell_w - 16

    cards: List[Any] = []
    for index, (jpeg, size) in enumerate(crops):
        det = detections[index] if index < len(detections) else None
        ratio = (size[1] / float(size[0])) if size and size[0] else 0.75
        cards.append(_card([
            RLImage(io.BytesIO(jpeg), width=image_w, height=image_w * ratio),
            Spacer(1, 4),
            Paragraph("<b>Tag #%d \u00b7 %s</b>"
                      % (det.id, escape(str(det.class_name).replace("_", " ").title()))
                      if det else " ", style["cap_c"]),
            Paragraph("%s \u00b7 %d%% confidence" % (escape(det.severity),
                                                     round(det.confidence * 100))
                      if det else " ", style["cap_c"]),
        ], cell_w, padding=8))

    rows: List[List[Any]] = []
    for start in range(0, len(cards), columns):
        row = cards[start:start + columns]
        row += [""] * (columns - len(row))
        rows.append(row)

    grid = Table(rows, colWidths=[cell_w + 8] * (columns - 1) + [cell_w])
    grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-2, -1), 8),
        ("RIGHTPADDING", (-1, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return grid


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def build_report(ctx: Dict[str, Any]) -> bytes:
    """Render the complaint PDF and return its raw bytes."""
    try:
        style = _styles()
        buffer = io.BytesIO()
        doc = _ReportDoc(buffer, reference=ctx["reference"])
        width = doc.width
        risk = ctx["risk"]
        moment: datetime = ctx["generated_at"]
        story: List[Any] = []

        # ---------------- Page 1 -----------------------------------------
        story += _masthead(ctx, style, width)
        story.append(_summary_row(ctx, style, width))
        story.append(Spacer(1, 4 * mm))

        story.append(_heading("Road Risk Assessment", style, width,
                              right="Project-defined model - see methodology",
                              accent=colors.HexColor(risk.risk_colour)))
        story.append(Spacer(1, 2.5 * mm))
        story.append(_risk_panel(ctx, style, width))
        story.append(Spacer(1, 4 * mm))

        half = width * 0.5 - 4
        telemetry = _card([
            Paragraph("GEOSPATIAL &amp; CAPTURE TELEMETRY", style["eyebrow"]),
            Spacer(1, 4),
            _kv([
                ("Date & time", moment.strftime("%d %b %Y, %I:%M %p")),
                ("Coordinates", "%.6f\u00b0 %s, %.6f\u00b0 %s"
                 % (abs(ctx["latitude"]), "N" if ctx["latitude"] >= 0 else "S",
                    abs(ctx["longitude"]), "E" if ctx["longitude"] >= 0 else "W")),
                ("Region", ctx["region"]),
                ("Source image", "%s (%d x %d px)" % (ctx["image_filename"],
                                                      ctx["source_size"][0],
                                                      ctx["source_size"][1])),
                ("Evidence SHA-256", Paragraph(escape(ctx["sha256"][:24]) + "...", style["mono"])),
                ("Map link", Paragraph(
                    '<link href="%s" color="#1D4ED8">Open this location in Google Maps</link>'
                    % escape(ctx["maps_url"]), style["cap"])),
            ], style, half - 18),
        ], half, padding=9)

        routing = _card([
            Paragraph("MUNICIPAL JURISDICTION &amp; ROUTING", style["eyebrow"]),
            Spacer(1, 4),
            _kv([
                ("Recipient body", ctx["addressed_to"]),
                ("Grievance tier", "%s - %s" % (risk.priority_tier, risk.response_window)),
                ("Dominant defect", (risk.dominant_defect or "None").replace("_", " ").title()),
                ("Priority action", ctx["detections"][0].recommended_action
                 if ctx["detections"] else "No action requested"),
                ("Submission status", "Prepared by the citizen - not yet filed with the authority"),
            ], style, half - 18),
        ], half, padding=9)

        pair = _plain([[telemetry, routing]], [half + 8, half])
        pair.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 8),
            ("RIGHTPADDING", (1, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(pair)
        story.append(Spacer(1, 4 * mm))
        story.append(_statement(ctx, style, width))

        # ---------------- Page 2 -----------------------------------------
        story.append(PageBreak())
        story.append(_heading("Defect Inventory & Recommended Remediation", style, width,
                              right="Suggestions for the engineering wing, not directives"))
        story.append(Spacer(1, 2.5 * mm))
        if ctx["detections"]:
            story.append(_inventory(ctx, style, width))
        else:
            story.append(_card([Paragraph(
                "No road defects were detected in the submitted photograph at the "
                "configured confidence threshold. No remediation is requested.",
                style["body"])], width, padding=10))
        story.append(Spacer(1, 5 * mm))

        story.append(_heading("Risk Analytics", style, width,
                              right="How the index was arrived at"))
        story.append(Spacer(1, 2.5 * mm))
        chart_w = width * 0.5 - 4
        charts = _plain([[
            _card([Paragraph("DEFECT COUNT BY SEVERITY BAND", style["eyebrow"]),
                   Spacer(1, 5),
                   _severity_chart(ctx["detections"], chart_w - 18)], chart_w, padding=9),
            _card([Paragraph("FRAME SHARE PER DEFECT", style["eyebrow"]),
                   Spacer(1, 5),
                   _area_chart(ctx["detections"], chart_w - 18)], chart_w, padding=9),
        ]], [chart_w + 8, chart_w])
        charts.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (0, 0), 8),
            ("RIGHTPADDING", (1, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        story.append(charts)
        story.append(Spacer(1, 4 * mm))

        story.append(_card([
            Paragraph("ROAD HEALTH SCORE AGAINST THE PROJECT'S CONDITION BANDS", style["eyebrow"]),
            Spacer(1, 3),
            _meter(ctx["road_health_score"], _bands(ROAD_CONDITION_BANDS), width - 18),
            Spacer(1, 3),
            Paragraph("Health score = 100 - defect percentage = 100 - %.2f = %.2f. "
                      "Higher is better here, so this scale runs in the opposite direction to "
                      "the risk scale on page 1."
                      % (ctx["defect_percentage"], ctx["road_health_score"]), style["cap"]),
        ], width, padding=9))

        # ---------------- End of page 2: methodology ----------------------
        story.append(Spacer(1, 4 * mm))
        classes = ", ".join(ctx.get("model_classes") or []) or "not reported"
        story.append(KeepTogether([
            _heading("Methodology & Limitations", style, width),
            Spacer(1, 2.5 * mm),
            _card([
                Paragraph(
                    "<b>Detection.</b> %s object-detection model (%s), single-pass CPU "
                    "inference at %d px, confidence threshold %.2f, NMS IoU %.2f. "
                    "Classes: %s."
                    % (escape(ctx["model_status"].replace("_", " ")).capitalize(),
                       escape(ctx["model_name"]), ctx["inference_image_size"],
                       ctx["confidence_threshold"], ctx["iou_threshold"], escape(classes)),
                    style["note"]),
                Spacer(1, 3),
                Paragraph(
                    "<b>Health score.</b> Defect area was measured by the '%s' method - summed "
                    "bounding-box area %.2f%%, overlap-corrected union area %.2f%% - as a share "
                    "of the %d x %d px frame. Road Health Score = 100 - defect percentage "
                    "= %.2f."
                    % (escape(ctx["area_method"]), ctx["summed_percentage"],
                       ctx["union_percentage"], ctx["source_size"][0], ctx["source_size"][1],
                       ctx["road_health_score"]), style["note"]),
                Spacer(1, 3),
                Paragraph(
                    "<b>Risk index.</b> (%s) x hazard %.2f x confidence %.2f = %.2f, "
                    "placing this location in the %s band (%s, %s). Severity of a single defect "
                    "is banded by the share of the frame its box covers, and demoted one band "
                    "when the model's confidence is below 0.40."
                    % (escape(" + ".join("%.2f x %s" % (c.weight, c.name.lower())
                                         for c in risk.components)),
                       risk.hazard_factor, risk.confidence_factor, risk.risk_index,
                       escape(risk.risk_level), escape(risk.priority_tier),
                       escape(risk.response_window)), style["note"]),
                Spacer(1, 3),
                Paragraph(
                    "<b>Limitations.</b> Every threshold, weight and band used above - the "
                    "Good/Fair/Poor/Dangerous score bands, the severity bands, the class hazard "
                    "weights and the risk bands - is defined by this project team for the "
                    "purpose of this tool. None of them is taken from IRC, MoRTH, GHMC or any "
                    "other official standard, and the recommended remediation is a starting "
                    "point for the engineering wing rather than an engineering directive. A "
                    "photograph carries no depth and no scale, so 'severity' reflects how much "
                    "of the frame a defect occupies, not how deep it is, and the same defect "
                    "photographed from a different distance will score differently. This "
                    "document is an automated visual estimate from a single photograph and does "
                    "not replace physical inspection by a qualified engineer.", style["note"]),
            ], width, padding=9),
        ]))

        # ---------------- Page 3: visual evidence annex -------------------
        if ctx.get("annotated_jpeg"):
            story.append(PageBreak())
            story.append(_heading("Visual Evidence", style, width,
                                  right="Annotated photographic record"))
            story.append(Spacer(1, 2.5 * mm))

            img_w, img_h = ctx["image_size"]
            display_w = width - 18
            display_h = display_w * (img_h / float(img_w or 1))
            max_h = doc.height * 0.50
            if display_h > max_h:
                display_h = max_h
                display_w = display_h * (img_w / float(img_h or 1))

            story.append(_card([
                RLImage(io.BytesIO(ctx["annotated_jpeg"]), width=display_w, height=display_h),
                Spacer(1, 4),
                Paragraph("<b>Figure 1.</b> Detected defects with class and confidence. Each "
                          "label number matches a tag in the inventory on page 2. "
                          "%d x %d px." % (img_w, img_h), style["cap"]),
            ], width, padding=9))
            story.append(Spacer(1, 4.5 * mm))

            grid = _crop_grid(ctx, style, width)
            if grid is not None:
                story.append(_heading("Isolated Defect Close-Ups", style, width,
                                      right="One crop per detection"))
                story.append(Spacer(1, 2.5 * mm))
                # No trailing spacer: the grid can end flush with the frame,
                # and a spacer there would spill an otherwise empty page.
                story.append(grid)

        doc.build(story)
        return buffer.getvalue()
    except Exception as exc:
        logger.exception("PDF generation failed: %s", exc)
        raise ReportGenerationError() from exc
