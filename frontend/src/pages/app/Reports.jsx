import { useState } from "react";
import { Send, Trash2, RotateCcw, Database } from "lucide-react";
import { useReports } from "../../context/ReportsContext";
import { STATUS_COLOUR, CONDITION_COLOUR, RISK_COLOUR } from "../../lib/mockData";

const STATUSES = ["All", "Draft", "Submitted", "Acknowledged", "Resolved"];

export default function Reports() {
  const { reports, submit, setStatus, remove, resetDemo, isMock, error, refresh } = useReports();
  const [filter, setFilter] = useState("All");
  const [actErr, setActErr] = useState(null);
  const rows = filter === "All" ? reports : reports.filter((r) => r.status === filter);

  // Every mutation can now fail on the server (403 on a transition a citizen
  // may not make, 404 on someone else's row), so show why instead of silence.
  async function act(fn) {
    setActErr(null);
    try { await fn(); } catch (e) { setActErr(e); }
  }

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
        {isMock && (
          <button className="btn btn-ghost ml-auto" onClick={resetDemo}>
            <RotateCcw size={15} /> Reset demo data
          </button>
        )}
      </div>

      <div className="glass-soft flex items-start gap-2.5 p-3.5 text-[13px] text-[color:var(--color-muted)]">
        <Database size={15} className="mt-0.5 shrink-0" />
        {isMock ? (
          <p>
            Reports live in <span className="font-mono">localStorage</span> on this
            browser only — they will not appear on another device, and clearing site
            data loses them.
          </p>
        ) : (
          <p>
            Reports are stored in PostgreSQL and belong to your account, so they
            follow you to any device you sign in on.
          </p>
        )}
      </div>

      {actErr && (
        <div className="glass-soft border-[color:var(--color-danger)]/40 p-3.5 text-[13px] text-[color:var(--color-danger)]" role="alert">
          {actErr.message}
        </div>
      )}

      {error && (
        <div className="glass-soft border-[color:var(--color-danger)]/40 p-3.5 text-[13px] text-[color:var(--color-danger)]" role="alert">
          Could not load reports — {error.message}{" "}
          <button className="underline cursor-pointer" onClick={refresh}>Retry</button>
        </div>
      )}

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
                    {/* Server rows carry a human reference (RHA-20260906-A1B2C3); the id is a
                        UUID nobody can quote down a phone line. Mock rows only have the id. */}
                    <span className="font-mono text-xs text-[color:var(--color-muted)]">{r.reference ?? r.id}</span>
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
                    <button className="btn btn-primary !px-3 !py-1.5 !text-xs" onClick={() => act(() => submit(r.id))}>
                      <Send size={13} /> Submit
                    </button>
                  )}
                  {r.status === "Submitted" && isMock && (
                    <button className="btn btn-ghost !px-3 !py-1.5 !text-xs" onClick={() => act(() => setStatus(r.id, "Acknowledged"))}>
                      Acknowledge
                    </button>
                  )}
                  {r.status === "Acknowledged" && isMock && (
                    <button className="btn btn-ghost !px-3 !py-1.5 !text-xs" onClick={() => act(() => setStatus(r.id, "Resolved"))}>
                      Mark resolved
                    </button>
                  )}
                  {r.status === "Submitted" && !isMock && (
                    <button className="btn btn-ghost !px-3 !py-1.5 !text-xs"
                            title="Withdraw back to draft" onClick={() => act(() => setStatus(r.id, "Draft"))}>
                      Withdraw
                    </button>
                  )}
                  {!isMock && (r.status === "Acknowledged" || r.status === "Resolved") && (
                    <span className="self-center text-[11px] text-[color:var(--color-muted)]">
                      set by the authority
                    </span>
                  )}
                  <button aria-label={`Delete ${r.id}`} onClick={() => act(() => remove(r.id))}
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
        {isMock
          ? "Status changes are unrestricted here — anyone using this browser can mark a complaint resolved. That is fine for a demo and wrong for a real grievance workflow."
          : "You can submit and withdraw your own reports. Acknowledging and resolving belongs to the municipal body — the server will refuse those transitions from a citizen account."}
      </p>
    </div>
  );
}
