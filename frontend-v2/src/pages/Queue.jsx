import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { BadgeCheck, CheckCircle2, Download, Loader2, MapPin, RotateCcw, ShieldCheck } from "lucide-react";
import { reports as api, downloadBlob } from "../lib/api";
import { fromApi, pdfName, riskColor, statusStyle } from "../lib/present";

/**
 * The municipal official's queue.
 *
 * Sorted by risk, not date: an official asks "what is waiting, and what is
 * worst". It never shows a draft (the server excludes them) and carries no
 * reporter contact details — the complaint is about a road.
 */
const TABS = [
  { key: "Submitted", label: "Awaiting action" },
  { key: "Acknowledged", label: "In progress" },
  { key: "Resolved", label: "Resolved" },
];

export default function Queue() {
  const [tab, setTab] = useState("Submitted");
  const [rows, setRows] = useState([]);
  const [busy, setBusy] = useState(true);
  const [acting, setActing] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setBusy(true);
    setError("");
    try {
      // mine=false turns "my reports" into "the queue"; the server honours it
      // only for an official account.
      const page = await api.list({ mine: false, status: tab, limit: 200 });
      setRows(page.items.map(fromApi).sort((a, b) => b.riskIndex - a.riskIndex));
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

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

  const move = (id, status) => act(id, async () => { await api.setStatus(id, status); await load(); });
  const pdf = (r) => act(r.id, async () => downloadBlob(await api.pdf(r.id), pdfName(r.reference)));

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-white lg:text-3xl">Grievance Queue</h1>
          <p className="mt-2 text-base text-ink/65">Complaints filed by citizens, worst first</p>
        </div>
        <span className="inline-flex w-fit items-center gap-2 rounded-xl border border-signal/25 bg-signal/10 px-4 py-2 text-sm text-signal">
          <ShieldCheck className="h-4 w-4" /> Official access
        </span>
      </div>

      <div className="flex items-start gap-2.5 rounded-xl border border-line bg-panel2 p-4 text-sm text-ink/60">
        <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-signal" />
        <p>
          Drafts never appear here — an unsent working copy is not a complaint. Acknowledging and resolving is
          limited to this role; the server refuses those actions to a citizen account, not just a hidden button.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
              tab === t.key ? "bg-signal text-white" : "border border-line text-ink/60 hover:text-ink"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {busy ? (
        <div className="grid place-items-center gap-2 rounded-2xl border border-line bg-panel p-12 text-sm text-muted">
          <Loader2 className="h-5 w-5 animate-spin" /> Loading the queue...
        </div>
      ) : rows.length === 0 ? (
        <div className="grid place-items-center gap-2 rounded-2xl border border-line bg-panel p-12 text-center">
          <CheckCircle2 className="h-6 w-6 text-green-400" />
          <p className="text-muted">
            Nothing {tab === "Submitted" ? "awaiting action" : `marked ${tab.toLowerCase()}`}.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {rows.map((r, i) => (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: Math.min(i * 0.04, 0.3) }}
              className="rounded-2xl border border-line bg-panel p-4"
            >
              <div className="flex flex-wrap items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-signal">{r.reference}</span>
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${statusStyle[r.status]}`}>{r.status}</span>
                    <span
                      className="rounded-full px-2.5 py-0.5 text-xs font-medium"
                      style={{ backgroundColor: `${riskColor[r.riskLevel]}20`, color: riskColor[r.riskLevel] }}
                    >
                      {r.riskLevel} · {r.riskIndex.toFixed(1)}
                    </span>
                  </div>
                  <p className="mt-1.5 font-medium text-white">{r.area}</p>
                  <p className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-ink/55">
                    <MapPin className="h-3 w-3" />
                    <a
                      className="underline decoration-dotted underline-offset-2 hover:text-ink"
                      href={`https://www.google.com/maps/search/?api=1&query=${r.lat},${r.lng}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {r.lat.toFixed(5)}, {r.lng.toFixed(5)}
                    </a>
                    <span>· {r.condition} · {r.defects} defects · {r.damageType}</span>
                    <span>· {r.tier}{r.responseWindow ? ` — ${r.responseWindow}` : ""}</span>
                    <span>· filed {r.date}</span>
                  </p>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button
                    disabled={acting === r.id || !r.hasImage}
                    onClick={() => pdf(r)}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-xs text-ink hover:border-signal hover:text-signal disabled:opacity-40"
                  >
                    {acting === r.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5" />}
                    PDF
                  </button>
                  {r.status === "Submitted" && (
                    <button
                      disabled={acting === r.id}
                      onClick={() => move(r.id, "Acknowledged")}
                      className="rounded-lg bg-signal px-3 py-1.5 text-xs font-semibold text-white hover:bg-signalDim disabled:opacity-40"
                    >
                      Acknowledge
                    </button>
                  )}
                  {r.status !== "Resolved" && (
                    <button
                      disabled={acting === r.id}
                      onClick={() => move(r.id, "Resolved")}
                      className="rounded-lg border border-line px-3 py-1.5 text-xs text-ink hover:border-green-500 hover:text-green-400 disabled:opacity-40"
                    >
                      Mark resolved
                    </button>
                  )}
                  {r.status === "Resolved" && (
                    <button
                      disabled={acting === r.id}
                      title="Reopen if the repair did not hold"
                      onClick={() => move(r.id, "Acknowledged")}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-line px-3 py-1.5 text-xs text-ink hover:border-amber-400 hover:text-amber-300 disabled:opacity-40"
                    >
                      <RotateCcw className="h-3.5 w-3.5" /> Reopen
                    </button>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      <p className="text-xs leading-relaxed text-ink/45">
        Scores and risk tiers come from a project-defined model, not from IRC, MoRTH or any GHMC standard. They are a
        triage aid — the decision to send an engineer stays a human one.
      </p>
    </div>
  );
}
