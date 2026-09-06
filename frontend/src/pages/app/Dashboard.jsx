import { Link } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, LabelList,
} from "recharts";
import { FileText, TriangleAlert, Gauge, CheckCircle2, ArrowRight } from "lucide-react";
import { useReports } from "../../context/ReportsContext";
import { useAuth } from "../../context/AuthContext";
import { distributions, CONDITION_COLOUR, STATUS_COLOUR } from "../../lib/mockData";
import DemoBadge from "../../components/DemoBadge";

/* Chart colours.
   The condition bars keep the semantic Good/Fair/Poor/Dangerous palette (it
   matches the gauge, the badges and the PDF). Those four are an ordered
   severity ramp, and adjacent steps sit ~10 dE apart - under the 15 floor for a
   categorical palette - so colour alone would not be readable. It does not have
   to be: every bar carries its band name on the axis and its count at the end,
   so colour reinforces an encoding that is already there in text.
   The two-line pair below is a genuine categorical pair and was validated:
   dE 32 normal vision, 27 under CVD. */
const SERIES_SCORE = "#4a9eff";
const SERIES_RISK = "#f2a03d";
const AXIS = "rgb(154 163 178 / .75)";
const GRID = "rgb(255 255 255 / .07)";

function TooltipCard({ active, payload, label, suffix = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass px-3 py-2 text-xs">
      <div className="font-semibold">{label}</div>
      {payload.map((p) => (
        <div key={p.name} className="mt-0.5 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ background: p.color ?? p.fill }} />
          <span className="text-[color:var(--color-muted)]">{p.name}</span>
          <span className="ml-auto font-mono">{p.value}{suffix}</span>
        </div>
      ))}
    </div>
  );
}

export default function Dashboard() {
  const { reports } = useReports();
  const { user } = useAuth();
  const { byCondition, timeline } = distributions(reports);

  const total = reports.length;
  const open = reports.filter((r) => r.status === "Submitted" || r.status === "Acknowledged").length;
  const resolved = reports.filter((r) => r.status === "Resolved").length;
  const avgScore = total ? (reports.reduce((s, r) => s + r.score, 0) / total).toFixed(1) : "—";
  const worst = reports.reduce((w, r) => (!w || r.risk_index > w.risk_index ? r : w), null);
  const anyDemo = reports.some((r) => r.is_demo !== false);

  const TILES = [
    { icon: FileText, v: total, l: "Reports filed" },
    { icon: Gauge, v: avgScore, l: "Average health score" },
    { icon: TriangleAlert, v: open, l: "Open grievances" },
    { icon: CheckCircle2, v: resolved, l: "Resolved" },
  ];

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Welcome back, <span className="capitalize">{user?.name}</span>
          </h1>
          <p className="text-sm text-[color:var(--color-muted)]">
            {total ? `${total} reports in this browser.` : "No reports yet."}
          </p>
        </div>
        {anyDemo && <DemoBadge />}
        <Link to="/app/upload" className="btn btn-primary ml-auto">
          New report <ArrowRight size={15} />
        </Link>
      </div>

      {/* hero numbers - a stat tile beats a chart for a single value */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {TILES.map((t) => (
          <div key={t.l} className="glass p-4">
            <t.icon size={17} className="text-[color:var(--color-brand)]" />
            <div className="mt-2.5 text-2xl font-semibold tracking-tight">{t.v}</div>
            <div className="text-[11.5px] uppercase tracking-wider text-[color:var(--color-muted)]">{t.l}</div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* band name on the axis + count at the bar end, so colour is reinforcement */}
        <div className="glass p-5">
          <h2 className="font-semibold">Reports by road condition</h2>
          <p className="mb-3 text-xs text-[color:var(--color-muted)]">
            How many reports fell in each condition band.
          </p>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={byCondition} layout="vertical" margin={{ left: 4, right: 30, top: 4, bottom: 4 }}>
              <CartesianGrid horizontal={false} stroke={GRID} />
              <XAxis type="number" allowDecimals={false} stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="name" width={78} stroke={AXIS} fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip content={<TooltipCard />} cursor={{ fill: "rgb(255 255 255 / .04)" }} />
              <Bar dataKey="value" name="Reports" radius={[0, 4, 4, 0]} barSize={18}>
                <LabelList dataKey="value" position="right" fill="rgb(154 163 178 / .95)" fontSize={11} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* two series, one 0-100 axis, legend always present */}
        <div className="glass p-5">
          <h2 className="font-semibold">Health score and risk over time</h2>
          <p className="mb-3 text-xs text-[color:var(--color-muted)]">
            Both are 0–100 on one scale, and they move in opposite directions by
            design — a healthier road scores higher and risks less.
          </p>
          <ResponsiveContainer width="100%" height={210}>
            <LineChart data={timeline} margin={{ left: -14, right: 8, top: 4, bottom: 4 }}>
              <CartesianGrid stroke={GRID} />
              <XAxis dataKey="date" stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} />
              <YAxis domain={[0, 100]} stroke={AXIS} fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip content={<TooltipCard />} cursor={{ stroke: "rgb(255 255 255 / .18)" }} />
              <Legend wrapperStyle={{ fontSize: 12, paddingTop: 6 }} iconType="plainline" />
              <Line type="monotone" dataKey="score" name="Health score" stroke={SERIES_SCORE}
                    strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
              <Line type="monotone" dataKey="risk" name="Risk index" stroke={SERIES_RISK}
                    strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {worst && (
        <div className="glass p-5">
          <h2 className="font-semibold">Needs attention first</h2>
          <div className="mt-3 flex flex-wrap items-center gap-4">
            <div className="rounded-xl border-2 px-4 py-2.5 text-center"
                 style={{ borderColor: CONDITION_COLOUR[worst.condition] }}>
              <div className="text-2xl font-semibold" style={{ color: CONDITION_COLOUR[worst.condition] }}>
                {worst.risk_index.toFixed(1)}
              </div>
              <div className="text-[10.5px] text-[color:var(--color-muted)]">Risk index</div>
            </div>
            <div className="min-w-0">
              <div className="font-medium">{worst.title}</div>
              <div className="text-xs text-[color:var(--color-muted)]">
                {worst.tier} · {worst.defects} defects · {worst.condition}
              </div>
            </div>
            <span className="chip ml-auto text-white" style={{ background: STATUS_COLOUR[worst.status] }}>
              {worst.status}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
