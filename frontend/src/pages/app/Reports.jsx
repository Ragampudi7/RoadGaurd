import { useState } from "react";
import { Send, Trash2, RotateCcw, Database } from "lucide-react";
import { useReports } from "../../context/ReportsContext";
import { STATUS_COLOUR, CONDITION_COLOUR, RISK_COLOUR } from "../../lib/mockData";

const STATUSES = ["All", "Draft", "Submitted", "Acknowledged", "Resolved"];

export default function Reports() {
  const { reports, submit, setStatus, remove, resetDemo } = useReports();
  const [filter, setFilter] = useState("All");
  const rows = filter === "All" ? reports : reports.filter((r) => r.status === filter);

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        <button className="btn btn-ghost ml-auto" onClick={resetDemo}>
          <RotateCcw size={15} /> Reset demo data
        </button>
      </div>

      <div className="glass-soft flex items-start gap-2.5 p-3.5 text-[13px] text-[color:var(--color-muted)]">
        <Database size={15} className="mt-0.5 shrink-0" />
        <p>
          Reports live in <span className="font-mono">localStorage</span> on this
          browser only — they will not appear on another device, and clearing site
          data loses them. Shared, durable storage arrives with the database.
        </p>
      </div>

      {/* filters in one row above the content */}
      <div className="flex flex-wrap gap-1.5">
        {STATUSES.map((s) => (
          <button key={s} onClick={() => setFilter(s)}
            className={`rounded-lg px-3 py-1.5 text-[13px] font-medium transition cursor-pointer border
              ${filter === s
                ? "border-[color:var(--color-brand)]/35 bg-[color:var(--color-brand)]/15 text-[color:var(--color-brand)]"
                : "border-transparent text-[color:var(--color-muted)] hover:bg-white/8"}`}>
            {s}
            <span className="ml-1.5 opacity-60">
              {s === "All" ? reports.length : reports.filter((r) => r.status === s).length}
            </span>
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <div className="glass p-10 text-center text-[color:var(--color-muted)]">
          No reports with that status.
        </div>
      ) : (
        <div className="grid gap-3">
          {rows.map((r) => (
            <div key={r.id} className="glass glass-hover p-4">
              <div className="flex flex-wrap items-center gap-3">
                <div className="rounded-lg border-2 px-3 py-1.5 text-center"
                     style={{ borderColor: CONDITION_COLOUR[r.condition] ?? "var(--color-minor)" }}>
                  <div className="text-lg font-semibold leading-none"
                       style={{ color: CONDITION_COLOUR[r.condition] }}>
                    {r.score?.toFixed(1)}
                  </div>
                  <div className="mt-0.5 text-[9.5px] uppercase tracking-wide text-[color:var(--color-muted)]">score</div>
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-[color:var(--color-muted)]">{r.id}</span>
                    <span className="chip text-white" style={{ background: STATUS_COLOUR[r.status] }}>{r.status}</span>
                  </div>
                  <div className="mt-1 truncate font-medium">{r.title}</div>
                  <div className="mt-0.5 text-xs text-[color:var(--color-muted)]">
                    {r.condition} · {r.defects} defects ·{" "}
                    <span style={{ color: RISK_COLOUR[r.risk_level] }}>{r.risk_level} risk {r.risk_index?.toFixed(1)}</span>
                    {" · "}{r.tier} · {new Date(r.created_at).toLocaleDateString()}
                  </div>
                </div>

                <div className="flex gap-2">
                  {r.status === "Draft" && (
                    <button className="btn btn-primary !px-3 !py-1.5 !text-xs" onClick={() => submit(r.id)}>
                      <Send size={13} /> Submit
                    </button>
                  )}
                  {r.status === "Submitted" && (
                    <button className="btn btn-ghost !px-3 !py-1.5 !text-xs" onClick={() => setStatus(r.id, "Acknowledged")}>
                      Acknowledge
                    </button>
                  )}
                  {r.status === "Acknowledged" && (
                    <button className="btn btn-ghost !px-3 !py-1.5 !text-xs" onClick={() => setStatus(r.id, "Resolved")}>
                      Mark resolved
                    </button>
                  )}
                  <button aria-label={`Delete ${r.id}`} onClick={() => remove(r.id)}
                          className="rounded-lg p-2 text-[color:var(--color-muted)] hover:bg-white/8 hover:text-[color:var(--color-danger)] transition cursor-pointer">
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs leading-relaxed text-[color:var(--color-muted)]">
        Status changes are unrestricted here — anyone using this browser can mark
        a complaint resolved. That is fine for a demo and wrong for a real
        grievance workflow, which needs accounts and roles on the server.
      </p>
    </div>
  );
}
