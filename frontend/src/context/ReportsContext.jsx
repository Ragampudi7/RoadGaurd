import { createContext, useContext, useEffect, useState } from "react";
import { demoReports } from "../lib/mockData";

/**
 * Report store. Persisted to localStorage until the database exists.
 *
 * localStorage is per-browser and per-device: reports filed on a phone will not
 * appear on a laptop, and clearing site data loses everything. That is the main
 * reason the Aiven step matters, and the Reports screen says so.
 */
const KEY = "roadguard_user_reports";
const ReportsCtx = createContext(null);

export function ReportsProvider({ children }) {
  const [reports, setReports] = useState([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      setReports(raw ? JSON.parse(raw) : demoReports);
    } catch {
      setReports(demoReports);
    }
    setReady(true);
  }, []);

  useEffect(() => {
    if (!ready) return;
    try { localStorage.setItem(KEY, JSON.stringify(reports)); } catch { /* ignore */ }
  }, [reports, ready]);

  const saveDraft = (report) => {
    const row = {
      id: "RG-" + Math.floor(1000 + Math.random() * 9000),
      status: "Draft",
      created_at: new Date().toISOString(),
      ...report,
    };
    setReports((r) => [row, ...r]);
    return row;
  };

  const submit = (id) =>
    setReports((r) => r.map((x) => (x.id === id ? { ...x, status: "Submitted" } : x)));

  const setStatus = (id, status) =>
    setReports((r) => r.map((x) => (x.id === id ? { ...x, status } : x)));

  const remove = (id) => setReports((r) => r.filter((x) => x.id !== id));

  const resetDemo = () => setReports(demoReports);

  return (
    <ReportsCtx.Provider value={{ reports, ready, saveDraft, submit, setStatus, remove, resetDemo }}>
      {children}
    </ReportsCtx.Provider>
  );
}

export const useReports = () => useContext(ReportsCtx);
