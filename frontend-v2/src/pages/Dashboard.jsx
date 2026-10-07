import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { AlertTriangle, Gauge, ShieldCheck, Sparkles, Target, Upload } from "lucide-react";
import { useReports } from "../context/ReportsContext";
import { prettyClass, riskColor, RISK_LEVELS } from "../lib/present";

const CLASS_COLORS = ["#2563eb", "#7c3aed", "#0ea5e9", "#14b8a6", "#f59e0b"];

function StatGauge({ label, value, suffix = "", helper, color, icon: Icon, progress, delay = 0 }) {
  const angle = Math.max(0, Math.min(progress, 100)) * 3.6;

  return (
    <motion.div
      initial={{ opacity: 0, y: 22, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay, duration: 0.55, ease: "easeOut" }}
      className="group relative overflow-hidden rounded-2xl border border-line bg-panel p-4 shadow-card sm:p-5"
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(37,99,235,0.18),transparent_42%)] opacity-80" />
      <div className="absolute -right-12 -top-16 h-36 w-36 rounded-full bg-white/5 blur-2xl transition-opacity group-hover:opacity-80" />

      <div className="relative mx-auto flex aspect-square w-full max-w-[190px] items-center justify-center 2xl:max-w-[220px]">
        <div
          className="absolute inset-0 rounded-full p-[12px] shadow-[0_0_34px_rgba(37,99,235,0.18)]"
          style={{
            background: `conic-gradient(${color} ${angle}deg, rgba(255,255,255,0.08) ${angle}deg 360deg)`,
          }}
        >
          <div className="h-full w-full rounded-full bg-base/90 shadow-inner" />
        </div>

        <div className="absolute inset-[20px] rounded-full border border-white/10 bg-panel2/70" />
        <div className="relative max-w-[120px] text-center">
          <div
            className="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-xl border border-white/10"
            style={{ backgroundColor: `${color}22`, color }}
          >
            <Icon className="h-5 w-5" />
          </div>
          <p className="text-[11px] font-semibold leading-tight text-ink/60 sm:text-xs">{label}</p>
          <p className="mt-1 whitespace-nowrap font-display text-3xl font-bold leading-none text-white sm:text-4xl">
            {value}
            <span className="text-base text-ink/50 sm:text-xl">{suffix}</span>
          </p>
          <p className="mt-1 text-[11px] leading-tight text-ink/45 sm:text-xs">{helper}</p>
        </div>
      </div>
    </motion.div>
  );
}

function DamagePatternCard({ reports }) {
  // Sum per-class detections across the reports on file.
  const counts = {};
  reports.forEach((r) => {
    Object.entries(r.defectCounts || {}).forEach(([k, v]) => { counts[k] = (counts[k] || 0) + v; });
  });
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const damageDistribution = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([k, v], i) => ({
      label: prettyClass(k),
      count: v,
      value: total ? Math.round((v / total) * 100) : 0,
      color: CLASS_COLORS[i % CLASS_COLORS.length],
    }));

  return (
    <motion.div
      initial={{ opacity: 0, x: 18 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.15, duration: 0.55 }}
      className="rounded-2xl border border-line bg-panel p-5 shadow-card"
    >
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h2 className="font-display text-lg font-semibold text-white">Damage Pattern</h2>
          <p className="text-sm text-ink/50">{total} defects detected across your reports</p>
        </div>
        <Sparkles className="h-5 w-5 text-signal" />
      </div>

      <div className="space-y-5">
        {total === 0 && <p className="text-sm text-ink/50">No defects on file yet.</p>}
        {damageDistribution.map((item, index) => {
          return (
            <div key={item.label}>
              <div className="mb-2 flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span
                    className="h-2.5 w-2.5 rounded-full shadow-[0_0_14px_currentColor]"
                    style={{ backgroundColor: item.color, color: item.color }}
                  />
                  <span className="font-medium text-ink/75">{item.label}</span>
                </div>
                <span className="font-display font-semibold text-white">{item.value}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-panel2">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${item.value}%` }}
                  transition={{ delay: 0.35 + index * 0.12, duration: 0.9, ease: "easeOut" }}
                  className="h-full rounded-full"
                  style={{
                    background: `linear-gradient(90deg, ${item.color}, ${item.color}99)`,
                    boxShadow: `0 0 18px ${item.color}66`,
                  }}
                />
              </div>
              <p className="mt-1 text-xs text-ink/40">{item.count} detection{item.count === 1 ? "" : "s"}</p>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}

function RiskDonutCard({ byRisk = {}, total = 0 }) {
  const severityDistribution = RISK_LEVELS.map((label) => ({
    label,
    color: riskColor[label],
    count: byRisk[label] || 0,
    value: total ? Math.round(((byRisk[label] || 0) / total) * 100) : 0,
  }));
  let cursor = 0;
  const segments = severityDistribution.map((item) => {
    const start = cursor;
    cursor += item.value;
    return `${item.color} ${start * 3.6}deg ${cursor * 3.6}deg`;
  });

  return (
    <motion.div
      initial={{ opacity: 0, x: 18 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.25, duration: 0.55 }}
      className="rounded-2xl border border-line bg-panel p-5 shadow-card"
    >
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h2 className="font-display text-lg font-semibold text-white">Road Risk Levels</h2>
          <p className="text-sm text-ink/50">Risk level of {total} filed report{total === 1 ? "" : "s"}</p>
        </div>
        <Target className="h-5 w-5 text-hazard" />
      </div>

      <div className="flex flex-col items-center gap-5 sm:flex-row lg:flex-col xl:flex-row">
        <div className="relative flex h-44 w-44 shrink-0 items-center justify-center">
          <motion.div
            initial={{ rotate: -70, scale: 0.9, opacity: 0 }}
            animate={{ rotate: 0, scale: 1, opacity: 1 }}
            transition={{ delay: 0.35, duration: 0.8, ease: "easeOut" }}
            className="absolute inset-0 rounded-full shadow-[0_0_34px_rgba(37,99,235,0.2)]"
            style={{ background: total ? `conic-gradient(${segments.join(", ")})` : "rgba(255,255,255,0.08)" }}
          />
          <div className="absolute inset-8 rounded-full border border-white/10 bg-base" />
          <div className="relative text-center">
            <p className="font-display text-3xl font-bold text-white">{total}</p>
            <p className="text-xs text-ink/45">reports</p>
          </div>
        </div>

        <div className="grid flex-1 grid-cols-2 gap-3">
          {severityDistribution.map((item) => (
            <div key={item.label} className="rounded-xl border border-line bg-panel2/70 p-3">
              <div className="mb-2 flex items-center gap-2">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                <span className="text-xs font-medium text-ink/60">{item.label}</span>
              </div>
              <p className="font-display text-xl font-bold text-white">{item.count}</p>
              <p className="text-xs text-ink/40">{item.value}%</p>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

export default function Dashboard() {
  const { stats, reports, ready, error } = useReports();
  // Server aggregate over every row (the list is paginated). Drafts are
  // included for a citizen's own dashboard, which matches /reports/stats.
  const byRisk = stats?.by_risk_level || {};
  const total = stats?.total || 0;
  const criticalCount = byRisk.Critical || 0;
  const highPriority = (byRisk.Critical || 0) + (byRisk.High || 0);
  const avgScore = stats?.average_score != null ? Math.round(stats.average_score) : "—";

  return (
    <div className="relative space-y-6 overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_24%_18%,rgba(37,99,235,0.18),transparent_30%),radial-gradient(circle_at_70%_8%,rgba(239,68,68,0.12),transparent_24%)]" />

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
        className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between"
      >
        <div>
          <h1 className="font-display text-2xl font-bold text-white lg:text-3xl">Road Safety Overview</h1>
          <p className="mt-2 max-w-2xl text-base text-ink/65">
            Severity trends, damage patterns, and road condition insights
          </p>
        </div>
        <div className="inline-flex w-fit items-center gap-2 rounded-xl border border-signal/25 bg-signal/10 px-4 py-2 text-sm text-signal">
          <span className="h-2 w-2 animate-pulseDot rounded-full bg-signal" />
          {ready ? `${total} report${total === 1 ? "" : "s"} on file` : "Loading..."}
        </div>
      </motion.div>

      {error && (
        <div role="alert" className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error.message}
        </div>
      )}

      {ready && !error && total === 0 && (
        <div className="flex flex-col items-start gap-3 rounded-2xl border border-line bg-panel p-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-ink/70">No reports yet. Photograph a damaged road to file your first complaint.</p>
          <Link to="/app/upload" className="inline-flex items-center gap-2 rounded-xl bg-signal px-4 py-2.5 text-sm font-semibold text-white hover:bg-signalDim">
            <Upload className="h-4 w-4" /> Create Complaint
          </Link>
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.9fr)]">
        <div className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2 2xl:grid-cols-3">
            <div className="lg:col-span-1">
              <StatGauge
                label="Critical Signals"
                value={criticalCount}
                helper="Require attention"
                color={riskColor.Critical}
                icon={AlertTriangle}
                progress={Math.min(100, criticalCount * 22)}
              />
            </div>
            <div className="lg:col-span-1 lg:-mt-2">
              <StatGauge
                label="Avg Road Score"
                value={avgScore}
                suffix="/100"
                helper="Condition index"
                color="#22c55e"
                icon={Gauge}
                progress={typeof avgScore === "number" ? avgScore : 0}
                delay={0.1}
              />
            </div>
            <div className="lg:col-span-1">
              <StatGauge
                label="Priority Roads"
                value={highPriority}
                helper="High or critical"
                color={riskColor.Moderate}
                icon={ShieldCheck}
                progress={Math.min(100, highPriority * 15)}
                delay={0.2}
              />
            </div>
          </div>
        </div>

        <div className="grid gap-6">
          <DamagePatternCard reports={reports} />
          <RiskDonutCard byRisk={byRisk} total={total} />
        </div>
      </div>
    </div>
  );
}
