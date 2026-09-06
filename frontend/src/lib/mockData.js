/**
 * Demo data.
 *
 * IMPORTANT: mockDetectionResult is shaped to match the real `POST /analyze`
 * response field for field (see backend/app/models/schemas.py). That is
 * deliberate — swapping to the live API means changing one call in
 * DetectionContext, not rewriting every screen that reads a result.
 *
 * Everything produced from this file is fabricated. The UI marks it as demo
 * data wherever it is shown, because this app can generate a grievance report
 * addressed to a municipal body and invented numbers must never look official.
 */

export const SEVERITY_COLOUR = {
  Critical: "var(--color-critical)",
  High: "var(--color-high)",
  Medium: "var(--color-medium)",
  Minor: "var(--color-minor)",
};

export const CONDITION_COLOUR = {
  Good: "var(--color-good)",
  Fair: "var(--color-fair)",
  Poor: "var(--color-poor)",
  Dangerous: "var(--color-danger)",
};

export const RISK_COLOUR = {
  Low: "var(--color-good)",
  Moderate: "var(--color-poor)",
  High: "var(--color-high)",
  Critical: "var(--color-critical)",
};

export const STATUS_COLOUR = {
  Draft: "var(--color-minor)",
  Submitted: "var(--color-brand)",
  Acknowledged: "var(--color-fair)",
  Resolved: "var(--color-good)",
};

/** Matches AnalyzeResponse from the backend. */
export const mockDetectionResult = {
  success: true,
  request_id: "RHA-DEMO-0001",
  analysed_at: "2026-09-06T10:15:00Z",
  road_health_score: 80.84,
  road_condition: "Fair",
  defect_percentage: 19.16,
  total_defects: 5,
  defect_counts: { pothole: 5 },
  detections: [
    { id: 1, class_id: 0, class_name: "pothole", confidence: 0.84, bbox: [150, 380, 500, 560],
      area: 63000, area_percentage: 11.93, severity: "Critical", severity_rank: 3,
      recommended_action: "Barricade, excavate and full-depth patch with hot-mix asphalt" },
    { id: 2, class_id: 0, class_name: "pothole", confidence: 0.80, bbox: [430, 270, 570, 320],
      area: 7000, area_percentage: 2.12, severity: "Medium", severity_rank: 1,
      recommended_action: "Edge trimming, tack coat and patch sealing" },
    { id: 3, class_id: 0, class_name: "pothole", confidence: 0.79, bbox: [180, 170, 400, 240],
      area: 15400, area_percentage: 3.04, severity: "High", severity_rank: 2,
      recommended_action: "Hot-mix / cold-mix asphalt fill with mechanical compaction" },
    { id: 4, class_id: 0, class_name: "pothole", confidence: 0.77, bbox: [190, 330, 330, 370],
      area: 5600, area_percentage: 1.48, severity: "Medium", severity_rank: 1,
      recommended_action: "Edge trimming, tack coat and patch sealing" },
    { id: 5, class_id: 0, class_name: "pothole", confidence: 0.60, bbox: [270, 90, 350, 120],
      area: 2400, area_percentage: 0.59, severity: "Minor", severity_rank: 0,
      recommended_action: "Localised surface levelling during the next maintenance round" },
  ],
  risk: {
    risk_index: 61.4,
    risk_level: "High",
    priority_tier: "Priority-2",
    response_window: "Remediate within 7 days",
    hazard_factor: 1.0,
    confidence_factor: 0.76,
    max_severity: "Critical",
    dominant_defect: "pothole",
    components: [
      { name: "Extent", value: 48, weight: 0.5, detail: "19.16% of the frame damaged" },
      { name: "Worst defect", value: 100, weight: 0.3, detail: "11.93% of the frame in one box" },
      { name: "Density", value: 63, weight: 0.2, detail: "5 defects detected" },
    ],
    summary:
      "Modelled risk is high (61.4 / 100). The worst single defect is rated critical, 5 defects cover about 19.16% of the photographed surface, and the suggested grievance tier is Priority-2 — remediate within 7 days.",
  },
  location: { latitude: 17.4948, longitude: 78.3996, maps_url: "https://maps.google.com/?q=17.4948,78.3996" },
  image: { filename: "demo-road.jpg", width: 640, height: 640, area_pixels: 409600,
           sha256: "demo0000000000000000000000000000000000000000000000000000000000" },
  model_info: { status: "demo", name: "mock", task: "detect", classes: ["pothole", "crack"],
                device: "none", confidence_threshold: 0.25, iou_threshold: 0.45,
                is_road_defect_model: false },
  complaint_description:
    "Road surface defects were detected in a photograph captured at latitude 17.494800, longitude 78.399600. Automated analysis identified 5 potholes, covering approximately 19.16% of the photographed road surface.",
  addressed_to: "Greater Hyderabad Municipal Corporation (GHMC)",
  processing_time_ms: 311,
  warnings: [],
  annotated_image: null,
  defect_crops: [],
  report: null,
  is_demo: true,
};

/** Seed reports so History, Map and Analytics have something to render. */
export const demoReports = [
  { id: "RG-1042", title: "Sunken patch near Kondapur junction", status: "Submitted",
    score: 42.1, condition: "Poor", risk_index: 74.2, risk_level: "High", tier: "Priority-2",
    defects: 8, lat: 17.4615, lon: 78.3648, created_at: "2026-09-01T08:20:00Z" },
  { id: "RG-1041", title: "Crack network on Gachibowli flyover approach", status: "Acknowledged",
    score: 66.3, condition: "Poor", risk_index: 51.0, risk_level: "High", tier: "Priority-2",
    defects: 5, lat: 17.4401, lon: 78.3489, created_at: "2026-08-29T17:05:00Z" },
  { id: "RG-1038", title: "Water-filled pothole, Madhapur service road", status: "Resolved",
    score: 38.7, condition: "Dangerous", risk_index: 88.4, risk_level: "Critical", tier: "Priority-1",
    defects: 11, lat: 17.4483, lon: 78.3915, created_at: "2026-08-22T06:40:00Z" },
  { id: "RG-1035", title: "Edge ravelling near Hitec City MMTS", status: "Submitted",
    score: 74.9, condition: "Fair", risk_index: 33.8, risk_level: "Moderate", tier: "Priority-3",
    defects: 3, lat: 17.4930, lon: 78.3915, created_at: "2026-08-18T12:15:00Z" },
  { id: "RG-1030", title: "Minor surface wear, Jubilee Hills Road No. 36", status: "Resolved",
    score: 91.2, condition: "Good", risk_index: 12.4, risk_level: "Low", tier: "Routine",
    defects: 1, lat: 17.4239, lon: 78.4110, created_at: "2026-08-11T09:00:00Z" },
];

/** Aggregates for the dashboard. Derived from whatever reports exist. */
export function distributions(reports) {
  const byCondition = ["Good", "Fair", "Poor", "Dangerous"].map((k) => ({
    name: k,
    value: reports.filter((r) => r.condition === k).length,
    fill: CONDITION_COLOUR[k],
  }));
  const byRisk = ["Low", "Moderate", "High", "Critical"].map((k) => ({
    name: k,
    value: reports.filter((r) => r.risk_level === k).length,
    fill: RISK_COLOUR[k],
  }));
  const byStatus = ["Draft", "Submitted", "Acknowledged", "Resolved"].map((k) => ({
    name: k,
    value: reports.filter((r) => r.status === k).length,
    fill: STATUS_COLOUR[k],
  }));
  const timeline = [...reports]
    .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    .map((r) => ({
      date: new Date(r.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
      score: r.score,
      risk: r.risk_index,
    }));
  return { byCondition, byRisk, byStatus, timeline };
}
