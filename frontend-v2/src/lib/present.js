/**
 * The one place backend vocabulary is translated for the screens.
 *
 * The backend speaks in risk levels (Low | Moderate | High | Critical), road
 * conditions (Good | Fair | Poor | Dangerous), priority tiers and four
 * statuses. The screens show those words as-is rather than renaming them, so
 * what a user sees here matches the PDF the backend generates.
 */
import { formatCoordinates, getNearestHyderabadArea } from "../data/hyderabadGeo";

export const RISK_LEVELS = ["Critical", "High", "Moderate", "Low"];

export const riskColor = {
  Critical: "#ef4444",
  High: "#f97316",
  Moderate: "#eab308",
  Low: "#22c55e",
};

export const conditionColor = {
  Good: "#22c55e",
  Fair: "#eab308",
  Poor: "#f97316",
  Dangerous: "#ef4444",
};

export const STATUSES = ["Draft", "Submitted", "Acknowledged", "Resolved"];

export const statusStyle = {
  Draft: "bg-amber-500/15 text-amber-300",
  Submitted: "bg-blue-500/15 text-blue-300",
  Acknowledged: "bg-violet-500/15 text-violet-300",
  Resolved: "bg-green-500/15 text-green-300",
};

/** "alligator_crack" -> "Alligator crack" */
export function prettyClass(name) {
  if (!name) return "";
  const s = String(name).replace(/[_-]+/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** The class with the most detections, or null when nothing was found. */
export function topClass(counts) {
  const entries = Object.entries(counts || {});
  if (!entries.length) return null;
  return entries.sort((a, b) => b[1] - a[1])[0][0];
}

export function damageLabel(counts, dominant) {
  const name = dominant || topClass(counts);
  return name ? prettyClass(name) : "No defects detected";
}

/** Server ReportOut -> the flat row the list, map and dashboard read. */
export function fromApi(r) {
  const point = { lat: r.latitude, lng: r.longitude };
  return {
    id: r.id,
    reference: r.reference,
    status: r.status,
    title: r.title,
    lat: r.latitude,
    lng: r.longitude,
    locationSource: r.location_source,
    area: getNearestHyderabadArea(point),
    location: `${getNearestHyderabadArea(point)} | ${formatCoordinates(point)}`,
    score: r.road_health_score,
    condition: r.road_condition,
    riskIndex: r.risk_index,
    riskLevel: r.risk_level,
    tier: r.priority_tier,
    responseWindow: r.response_window,
    defects: r.total_defects,
    defectCounts: r.defect_counts || {},
    damageType: damageLabel(r.defect_counts),
    hasImage: r.has_image,
    modelVersion: r.model_version,
    createdAt: r.created_at,
    date: (r.created_at || "").slice(0, 10),
  };
}

/** Filename the backend's PDF is saved under. */
export const pdfName = (reference) => `RoadGuard_${reference || "report"}.pdf`;
