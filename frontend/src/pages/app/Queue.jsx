import { useCallback, useEffect, useState } from "react";
import {
  BadgeCheck, CheckCircle2, FileDown, Loader2, MapPin, RotateCcw, ShieldCheck,
} from "lucide-react";
import { reports as api, downloadBlob } from "../../lib/api";
import { STATUS_COLOUR, RISK_COLOUR } from "../../lib/mockData";

/**
 * The municipal official's queue.
 *
 * Deliberately not a version of the citizen's Reports screen with extra
 * buttons: it answers a different question. A citizen asks "what happened to
 * mine"; an official asks "what is waiting, and what is worst". So it is
 * sorted by risk rather than by date, it never shows a draft, and it carries
 * no contact details — the complaint is about a road, and giving every
 * official the reporter's email would be collecting personal data the job
 * does not need.
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
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      // mine=false is what turns this from "my reports" into "the queue"; the
      // server only honours it for an official account.
      const page = await api.list({ mine: false, status: tab, limit: 200 });
      setRows([...page.items].sort((a, b) => b.risk_index - a.risk_index));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  async function act(id, status) {
    setError(null);
    setActing(id);
    try {
      await api.setStatus(id, status);
      await load();
    } catch (e) {
      setError(e);
    } finally {
      setActing(null);
    }
  }

  async function pdf(r) {
    setError(null);
    setActing(r.id);
    try {
      downloadBlob(await api.pdf(r.id), `road_health_report_${r.reference}.pdf`);
    } catch (e) {
      setError(e);
    } finally {
      setActing(null);
    }
  }

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Grievance queue</h1>
          <p className="text-sm text-[color:var(--color-muted)]">
            Complaints filed by citizens, worst first.
          </p>
        </div>
        {/* The header already shows who is signed in; this says what they are
            allowed to do here, which is the part that is not obvious. */}
        <span className="chip ml-auto flex items-center gap-1.5 bg-[color:var(--color-brand)]/15 text-[color:var(--color-brand)]">
          <ShieldCheck size={13} /> Official access
        </span>
      </div>

      <div className="glass-soft flex items-start gap-2.5 p-3.5 text-[13px] text-[color:var(--color-muted)]">
        <BadgeCheck size={15} className="mt-0.5 shrink-0" />
        <p>
          Drafts never appear here — a citizen’s unsent working copy is not a
          complaint. Acknowledging and resolving is limited to this role; a
          citizen account is refused those transitions by the server, not just
          by a hidden button.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => setTab(t.key)}
                  className={`chip cursor-pointer transition ${
                    tab === t.key
                      ? "bg-[color:var(--color-brand)] text-white"
                      : "bg-white/6 text-[color:var(--color-muted)] hover:bg-white/10"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="glass-soft border-[color:var(--color-danger)]/40 p-3.5 text-[13px] text-[color:var(--color-danger)]" role="alert">
          {error.message}
        </div>
      )}

      {busy ? (
        <div className="glass grid place-items-center gap-2 p-12 text-sm text-[color:var(--color-muted)]">
          <Loader2 size={20} className="animate-spin" /> Loading the queue…
        </div>
      ) : rows.length === 0 ? (
        <div className="glass grid place-items-center gap-2 p-12 text-center">
          <CheckCircle2 size={24} className="text-[color:var(--color-good)]" />
          <p className="text-[color:var(--color-muted)]">
            Nothing {tab === "Submitted" ? "awaiting action" : `marked ${tab.toLowerCase()}`}.
          </p>
        </div>
      ) : (
        <div className="grid gap-3">
          {rows.map((r) => (
            <div key={r.id} className="glass glass-hover p-4">
              <div className="flex flex-wrap items-start gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs text-[color:var(--color-muted)]">{r.reference}</span>
                    <span className="chip text-white" style={{ background: STATUS_COLOUR[r.status] }}>
                      {r.status}
                    </span>
                    <span className="chip text-white" style={{ background: RISK_COLOUR[r.risk_level] }}>
                      {r.risk_level} · {r.risk_index.toFixed(1)}
                    </span>
                  </div>
                  <div className="mt-1 truncate font-medium">{r.title}</div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 text-xs text-[color:var(--color-muted)]">
                    <MapPin size={12} />
                    <a className="underline decoration-dotted underline-offset-2"
                       href={`https://www.google.com/maps/search/?api=1&query=${r.latitude},${r.longitude}`}
                       target="_blank" rel="noreferrer">
                      {r.latitude.toFixed(5)}, {r.longitude.toFixed(5)}
                    </a>
                    <span>· {r.road_condition} · {r.total_defects} defects</span>
                    <span>· {r.priority_tier}{r.response_window ? ` — ${r.response_window}` : ""}</span>
                    <span>· filed {new Date(r.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                <div className="flex flex-wrap gap-2">
                  <button className="btn btn-ghost !px-3 !py-1.5 !text-xs"
                          disabled={acting === r.id} onClick={() => pdf(r)}>
                    {acting === r.id ? <Loader2 size={13} className="animate-spin" /> : <FileDown size={13} />}
                    PDF
                  </button>
                  {r.status === "Submitted" && (
                    <button className="btn btn-primary !px-3 !py-1.5 !text-xs"
                            disabled={acting === r.id} onClick={() => act(r.id, "Acknowledged")}>
                      Acknowledge
                    </button>
                  )}
                  {r.status !== "Resolved" && (
                    <button className="btn btn-ghost !px-3 !py-1.5 !text-xs"
                            disabled={acting === r.id} onClick={() => act(r.id, "Resolved")}>
                      Mark resolved
                    </button>
                  )}
                  {r.status === "Resolved" && (
                    <button className="btn btn-ghost !px-3 !py-1.5 !text-xs"
                            title="Reopen if the repair did not hold"
                            disabled={acting === r.id} onClick={() => act(r.id, "Acknowledged")}>
                      <RotateCcw size={13} /> Reopen
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <p className="text-xs leading-relaxed text-[color:var(--color-muted)]">
        Scores and risk tiers here come from a project-defined model, not from
        IRC, MoRTH or any GHMC standard. They are a triage aid — the decision to
        send an engineer stays a human one.
      </p>
    </div>
  );
}
