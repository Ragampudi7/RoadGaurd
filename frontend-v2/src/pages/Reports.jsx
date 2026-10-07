import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Search, ChevronLeft, ChevronRight, Filter, Download, Send, Trash2, Undo2, Loader2, RefreshCw } from "lucide-react";
import { useReports } from "../context/ReportsContext";
import { reports as api, downloadBlob } from "../lib/api";
import { pdfName, riskColor, RISK_LEVELS, STATUSES, statusStyle } from "../lib/present";

const PAGE_SIZE = 8;
const severityOptions = ["All", ...RISK_LEVELS];
const typeOptions = ["All", ...STATUSES];

export default function Reports() {
  const { reports: allReports, ready, error: loadError, refresh, submitReport, withdrawReport, deleteReport } = useReports();
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [page, setPage] = useState(1);
  const [acting, setActing] = useState(null);
  const [error, setError] = useState("");

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return allReports.filter((r) => {
      const matchSearch =
        (r.reference || "").toLowerCase().includes(q) ||
        (r.location || "").toLowerCase().includes(q);
      const matchSeverity = severity === "All" || r.riskLevel === severity;
      const matchType = typeFilter === "All" || r.status === typeFilter;
      return matchSearch && matchSeverity && matchType;
    });
  }, [allReports, search, severity, typeFilter]);

  const act = async (id, fn) => {
    setActing(id);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setActing(null);
    }
  };

  // The backend rebuilds the PDF from the stored report and photograph.
  const downloadPdf = (r) => act(r.id, async () => downloadBlob(await api.pdf(r.id), pdfName(r.reference)));

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE) || 1;
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-white lg:text-3xl">Reports</h1>
        <p className="mt-2 text-base text-ink/65">View drafts, submitted reports, and download PDFs</p>
      </div>

      {(error || loadError) && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          <span>{error || loadError.message}</span>
          {loadError && (
            <button onClick={refresh} className="inline-flex items-center gap-1 text-red-200 hover:underline">
              <RefreshCw className="h-3.5 w-3.5" /> Retry
            </button>
          )}
        </div>
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            type="text"
            placeholder="Search by reference or area..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full rounded-xl border border-line bg-panel2 py-2.5 pl-10 pr-4 text-sm text-ink outline-none focus:border-signal"
          />
        </div>
        <div className="flex gap-3">
          <div className="relative">
            <Filter className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted" />
            <select
              value={severity}
              onChange={(e) => {
                setSeverity(e.target.value);
                setPage(1);
              }}
              className="appearance-none rounded-xl border border-line bg-panel2 py-2.5 pl-9 pr-8 text-sm text-ink outline-none focus:border-signal"
            >
              {severityOptions.map((o) => (
                <option key={o} value={o}>
                  {o === "All" ? "All Risk Levels" : o}
                </option>
              ))}
            </select>
          </div>
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-xl border border-line bg-panel2 px-4 py-2.5 text-sm text-ink outline-none focus:border-signal"
          >
            {typeOptions.map((o) => (
              <option key={o} value={o}>
                {o === "All" ? "All Statuses" : o}
              </option>
            ))}
          </select>
        </div>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="overflow-hidden rounded-xl border border-line bg-panel"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line bg-panel2/50 text-left text-ink/50">
                <th className="px-5 py-3.5 font-medium">Reference</th>
                <th className="px-5 py-3.5 font-medium">Location</th>
                <th className="px-5 py-3.5 font-medium">Risk</th>
                <th className="px-5 py-3.5 font-medium">Score</th>
                <th className="px-5 py-3.5 font-medium">Date</th>
                <th className="px-5 py-3.5 font-medium">Status</th>
                <th className="px-5 py-3.5 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {!ready ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-muted">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </td>
                </tr>
              ) : paginated.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-muted">
                    {allReports.length === 0
                      ? "No reports yet — create a complaint from Upload."
                      : "No reports found matching your filters"}
                  </td>
                </tr>
              ) : (
                paginated.map((r) => (
                  <tr key={r.id} className="border-b border-line/50 transition-colors hover:bg-panel2/30">
                    <td className="px-5 py-4 font-mono text-xs text-signal">{r.reference}</td>
                    <td className="px-5 py-4 text-ink/85">
                      <div>{r.area}</div>
                      <div className="text-xs text-ink/45">{r.damageType} · {r.defects} defect{r.defects === 1 ? "" : "s"}</div>
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium"
                        style={{
                          backgroundColor: `${riskColor[r.riskLevel] || "#64748b"}20`,
                          color: riskColor[r.riskLevel] || "#64748b",
                        }}
                      >
                        {r.riskLevel}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-ink/80">{r.score?.toFixed(1)}</td>
                    <td className="px-5 py-4 text-muted">{r.date}</td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyle[r.status] || ""}`}>
                        {r.status}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        {acting === r.id ? (
                          <Loader2 className="h-4 w-4 animate-spin text-muted" />
                        ) : (
                          <>
                            <button
                              onClick={() => downloadPdf(r)}
                              disabled={!r.hasImage}
                              title={r.hasImage ? "Download PDF" : "No photograph stored — the PDF cannot be rebuilt"}
                              className="rounded-lg border border-line p-1.5 text-muted hover:border-signal hover:text-signal disabled:opacity-30"
                            >
                              <Download className="h-3.5 w-3.5" />
                            </button>
                            {r.status === "Draft" && (
                              <>
                                <button
                                  onClick={() => act(r.id, () => submitReport(r.id))}
                                  title="Submit report"
                                  className="rounded-lg border border-line p-1.5 text-muted hover:border-green-500 hover:text-green-400"
                                >
                                  <Send className="h-3.5 w-3.5" />
                                </button>
                                <button
                                  onClick={() => act(r.id, () => deleteReport(r.id))}
                                  title="Delete draft"
                                  className="rounded-lg border border-line p-1.5 text-muted hover:border-red-400 hover:text-red-400"
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                </button>
                              </>
                            )}
                            {r.status === "Submitted" && (
                              <button
                                onClick={() => act(r.id, () => withdrawReport(r.id))}
                                title="Withdraw back to draft"
                                className="rounded-lg border border-line p-1.5 text-muted hover:border-amber-400 hover:text-amber-300"
                              >
                                <Undo2 className="h-3.5 w-3.5" />
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {filtered.length > PAGE_SIZE && (
          <div className="flex items-center justify-between border-t border-line px-5 py-3">
            <p className="text-xs text-muted">
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, filtered.length)} of{" "}
              {filtered.length}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="rounded-lg border border-line p-1.5 text-muted hover:text-ink disabled:opacity-30"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="flex items-center px-3 text-sm text-muted">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="rounded-lg border border-line p-1.5 text-muted hover:text-ink disabled:opacity-30"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
