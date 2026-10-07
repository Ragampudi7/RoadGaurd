import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { reports as api, fileToBase64 } from "../lib/api";
import { fromApi } from "../lib/present";
import { useAuth } from "./AuthContext";

/**
 * Report store, backed by the server. Reports belong to the signed-in account
 * and follow it to any device; nothing is kept in the browser.
 *
 * Headline numbers come from GET /reports/stats, which Postgres computes over
 * every row. The list is one page, so counting it would under-report.
 */
const ReportsContext = createContext(null);

export function ReportsProvider({ children }) {
  const { user, loading: authLoading } = useAuth();
  const [reports, setReports] = useState([]);
  const [stats, setStats] = useState(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (!user) { setReports([]); setStats(null); setReady(true); return; }
    try {
      const [page, summary] = await Promise.all([api.list({ limit: 200 }), api.stats()]);
      setReports(page.items.map(fromApi));
      setStats({ ...summary, worst: summary.worst ? fromApi(summary.worst) : null });
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setReady(true);
    }
  }, [user]);

  useEffect(() => {
    if (!authLoading) refresh();
  }, [authLoading, refresh]);

  // After a mutation the aggregate is stale; ask the database again. A failure
  // here must not undo a mutation that already succeeded.
  const syncStats = async () => {
    try {
      const summary = await api.stats();
      setStats({ ...summary, worst: summary.worst ? fromApi(summary.worst) : null });
    } catch { /* the numbers can lag; the report itself did not fail */ }
  };

  /**
   * File an AnalyzeResponse as a report. `file` is the photograph it came
   * from - without it the report has no evidence and its PDF cannot be rebuilt.
   */
  const saveAnalysis = async (analysis, { submit = false, file, title } = {}) => {
    let image_base64 = null;
    if (file) {
      try { image_base64 = await fileToBase64(file); } catch { image_base64 = null; }
    }
    const { latitude, longitude } = analysis.location;
    const created = await api.create({
      title: title ?? `Road defect at ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`,
      latitude,
      longitude,
      road_health_score: analysis.road_health_score,
      road_condition: analysis.road_condition,
      defect_percentage: analysis.defect_percentage,
      total_defects: analysis.total_defects,
      defect_counts: analysis.defect_counts ?? {},
      risk_index: analysis.risk.risk_index,
      risk_level: analysis.risk.risk_level,
      priority_tier: analysis.risk.priority_tier,
      response_window: analysis.risk.response_window,
      risk_components: analysis.risk.components ?? [],
      // The whole risk object, so a rebuilt PDF shows what was filed rather
      // than what a since-edited config would compute.
      risk_detail: analysis.risk,
      detections: analysis.detections ?? [],
      model_name: analysis.model_info?.name,
      // The weights fingerprint, e.g. yolo11n-935e809b.
      model_version: analysis.model_info?.version,
      inference_image_size: analysis.model_info?.inference_image_size,
      image_sha256: analysis.image?.sha256,
      image_width: analysis.image?.width,
      image_height: analysis.image?.height,
      image_base64,
      image_mime: file?.type || null,
      complaint_description: analysis.complaint_description,
      addressed_to: analysis.addressed_to,
      analysed_at: analysis.analysed_at,
      submit,
    });
    const row = fromApi(created);
    setReports((r) => [row, ...r]);
    syncStats();
    return row;
  };

  const setStatus = async (id, status) => {
    const updated = await api.setStatus(id, status);
    const row = fromApi(updated);
    setReports((r) => r.map((x) => (x.id === id ? row : x)));
    syncStats();
    return row;
  };

  const submitReport = (id) => setStatus(id, "Submitted");
  const withdrawReport = (id) => setStatus(id, "Draft");

  const deleteReport = async (id) => {
    await api.remove(id);
    setReports((r) => r.filter((x) => x.id !== id));
    syncStats();
  };

  const drafts = reports.filter((r) => r.status === "Draft");

  return (
    <ReportsContext.Provider
      value={{
        reports, drafts, stats, ready, error, refresh,
        saveAnalysis, setStatus, submitReport, withdrawReport, deleteReport,
      }}
    >
      {children}
    </ReportsContext.Provider>
  );
}

export function useReports() {
  const ctx = useContext(ReportsContext);
  if (!ctx) throw new Error("useReports must be used within ReportsProvider");
  return ctx;
}
