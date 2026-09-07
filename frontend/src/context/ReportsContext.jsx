import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { reports as api, USE_MOCK } from "../lib/api";
import { demoReports } from "../lib/mockData";
import { useAuth } from "./AuthContext";

/**
 * Report store.
 *
 *   USE_MOCK=true   localStorage. Per-browser and per-device: reports filed on
 *                   a phone never appear on a laptop, and clearing site data
 *                   loses them. The Reports screen says so.
 *   USE_MOCK=false  the server. Reports belong to the signed-in account and
 *                   follow it to any device.
 *
 * The rest of the app reads a single flat shape either way, so screens do not
 * branch on which mode is active — only the copy does.
 */
const KEY = "roadguard_user_reports";
const ReportsCtx = createContext(null);

/** Server row -> the flat shape the screens already expect. */
function fromApi(r) {
  return {
    id: r.id,
    reference: r.reference,
    status: r.status,
    title: r.title ?? `Report at ${r.latitude?.toFixed?.(4)}, ${r.longitude?.toFixed?.(4)}`,
    score: r.road_health_score,
    condition: r.road_condition,
    risk_index: r.risk_index,
    risk_level: r.risk_level,
    tier: r.priority_tier,
    defects: r.total_defects,
    lat: r.latitude,
    lon: r.longitude,
    created_at: r.created_at,
    model_version: r.model_version,
    is_demo: false,
  };
}

export function ReportsProvider({ children }) {
  const { user, ready: authReady } = useAuth();
  const [reports, setReports] = useState([]);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (USE_MOCK) return;
    if (!user) { setReports([]); setReady(true); return; }
    try {
      const page = await api.list({ limit: 200 });
      setReports(page.items.map(fromApi));
      setError(null);
    } catch (e) {
      setError(e);
    } finally {
      setReady(true);
    }
  }, [user]);

  useEffect(() => {
    if (USE_MOCK) {
      try {
        const raw = localStorage.getItem(KEY);
        setReports(raw ? JSON.parse(raw) : demoReports);
      } catch { setReports(demoReports); }
      setReady(true);
      return;
    }
    if (authReady) refresh();
  }, [authReady, refresh]);

  // Mirror to localStorage only in mock mode; on the server path the database
  // is the record and a stale browser copy would just be a second truth.
  useEffect(() => {
    if (!USE_MOCK || !ready) return;
    try { localStorage.setItem(KEY, JSON.stringify(reports)); } catch { /* ignore */ }
  }, [reports, ready]);

  /** File -> bare base64 (no data: prefix), which is what the API accepts. */
  const fileToBase64 = (f) =>
    new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(String(r.result).split(",", 2)[1]);
      r.onerror = () => reject(r.error);
      r.readAsDataURL(f);
    });

  /** `analysis` is an AnalyzeResponse (real or mock); `file` the photograph it came from. */
  const saveDraft = async (analysis, { submit = false, title, file } = {}) => {
    if (USE_MOCK) {
      const row = {
        id: "RG-" + Math.floor(1000 + Math.random() * 9000),
        status: submit ? "Submitted" : "Draft",
        created_at: new Date().toISOString(),
        title: title ?? `Report at ${analysis.location.latitude.toFixed(4)}, ${analysis.location.longitude.toFixed(4)}`,
        score: analysis.road_health_score,
        condition: analysis.road_condition,
        risk_index: analysis.risk.risk_index,
        risk_level: analysis.risk.risk_level,
        tier: analysis.risk.priority_tier,
        defects: analysis.total_defects,
        lat: analysis.location.latitude,
        lon: analysis.location.longitude,
        is_demo: true,
      };
      setReports((r) => [row, ...r]);
      return row;
    }

    // Sending the photograph is best-effort: a FileReader failure should cost
    // the picture, not the whole report.
    let image_base64 = null;
    if (file) {
      try { image_base64 = await fileToBase64(file); }
      catch { image_base64 = null; }
    }

    const created = await api.create({
      title: title ?? `Report at ${analysis.location.latitude.toFixed(4)}, ${analysis.location.longitude.toFixed(4)}`,
      latitude: analysis.location.latitude,
      longitude: analysis.location.longitude,
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
      detections: analysis.detections ?? [],
      model_name: analysis.model_info?.name,
      // The weights fingerprint, not model_info.status ("trained"), which says
      // nothing about WHICH trained weights produced these numbers.
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
    return row;
  };

  const setStatus = async (id, status) => {
    if (USE_MOCK) {
      setReports((r) => r.map((x) => (x.id === id ? { ...x, status } : x)));
      return;
    }
    const updated = await api.setStatus(id, status);
    setReports((r) => r.map((x) => (x.id === id ? fromApi(updated) : x)));
  };

  const submit = (id) => setStatus(id, "Submitted");

  const remove = async (id) => {
    if (!USE_MOCK) await api.remove(id);
    setReports((r) => r.filter((x) => x.id !== id));
  };

  const resetDemo = () => { if (USE_MOCK) setReports(demoReports); };

  return (
    <ReportsCtx.Provider
      value={{ reports, ready, error, refresh, saveDraft, submit, setStatus, remove,
               resetDemo, isMock: USE_MOCK }}>
      {children}
    </ReportsCtx.Provider>
  );
}

export const useReports = () => useContext(ReportsCtx);
