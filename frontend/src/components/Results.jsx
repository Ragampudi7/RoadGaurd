import { CONDITION_COLOUR, RISK_COLOUR, SEVERITY_COLOUR } from "../lib/mockData";

/* ---------------------------------------------------------------- gauge --
   Same 270-degree arc as the PDF report's Road Health Index, so the screen and
   the printed grievance read as one document. Score runs 0-100, higher better —
   the opposite direction to the risk meter, which is worth noticing. */
export function ScoreGauge({ score, condition, size = 180 }) {
  const stroke = 14;
  const r = (size - stroke) / 2;
  const c = size / 2;
  const SWEEP = 270, START = 135;

  const polar = (deg) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [c + r * Math.cos(rad), c + r * Math.sin(rad)];
  };
  const arc = (a, b) => {
    const [x1, y1] = polar(a), [x2, y2] = polar(b);
    return `M ${x1} ${y1} A ${r} ${r} 0 ${b - a > 180 ? 1 : 0} 1 ${x2} ${y2}`;
  };

  const pct = Math.max(0, Math.min(100, Number(score ?? 0))) / 100;
  const colour = CONDITION_COLOUR[condition] ?? "var(--color-muted)";

  return (
    <div className="relative grid place-items-center">
      <svg width={size} height={size} role="img"
           aria-label={`Road health score ${score} of 100, condition ${condition}`}>
        <path d={arc(START, START + SWEEP)} fill="none" stroke="rgb(255 255 255 / .1)"
              strokeWidth={stroke} strokeLinecap="round" />
        {pct > 0 && (
          <path d={arc(START, START + SWEEP * pct)} fill="none" stroke={colour}
                strokeWidth={stroke} strokeLinecap="round" />
        )}
      </svg>
      <div className="absolute top-[41%] -translate-y-1/2 text-center">
        <div className="text-[32px] font-semibold leading-none" style={{ color: colour }}>
          {Number(score ?? 0).toFixed(2)}
        </div>
        <div className="mt-1 text-[11px] text-[color:var(--color-muted)]">out of 100</div>
      </div>
      <span className="chip absolute bottom-1 text-white" style={{ background: colour }}>
        {condition}
      </span>
    </div>
  );
}

/* ----------------------------------------------------------------- risk --
   The weighted components are shown, not just the index. Without them the
   number has to be taken on faith; with them it can be checked. */
export function RiskPanel({ risk }) {
  if (!risk) return null;
  const colour = RISK_COLOUR[risk.risk_level] ?? "var(--color-muted)";
  return (
    <div className="glass grid gap-5 p-5">
      <div className="flex flex-wrap items-center gap-4">
        <div className="rounded-2xl border-2 px-5 py-3 text-center" style={{ borderColor: colour }}>
          <div className="text-3xl font-semibold leading-none" style={{ color: colour }}>
            {risk.risk_index?.toFixed(1)}
          </div>
          <div className="mt-1 text-[11px] text-[color:var(--color-muted)]">Risk index / 100</div>
        </div>
        <div>
          <span className="chip text-white" style={{ background: colour }}>{risk.risk_level} risk</span>
          <div className="mt-2 text-sm font-semibold">{risk.priority_tier}</div>
          <div className="text-xs text-[color:var(--color-muted)]">{risk.response_window}</div>
        </div>
      </div>

      {risk.components?.length > 0 && (
        <div className="grid gap-3">
          {risk.components.map((c) => (
            <div key={c.name}>
              <div className="flex justify-between text-[13px] font-medium">
                <span>{c.name}</span>
                <span className="text-[color:var(--color-muted)]">weight {(c.weight * 100).toFixed(0)}%</span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full transition-all"
                     style={{ width: `${Math.min(100, c.value)}%`, background: colour }} />
              </div>
              {c.detail && <div className="mt-1 text-xs text-[color:var(--color-muted)]">{c.detail}</div>}
            </div>
          ))}
        </div>
      )}

      <p className="text-[13px] leading-relaxed text-[color:var(--color-muted)]">{risk.summary}</p>
    </div>
  );
}

/* ----------------------------------------------------------- detections -- */
export function DetectionTable({ detections }) {
  if (!detections?.length) {
    return <p className="text-sm text-[color:var(--color-muted)]">No defects were detected in this photograph.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wider text-[color:var(--color-muted)]">
            <th className="py-2 pr-3 font-semibold">Tag</th>
            <th className="py-2 pr-3 font-semibold">Class</th>
            <th className="py-2 pr-3 font-semibold">Confidence</th>
            <th className="py-2 pr-3 font-semibold">Severity</th>
            <th className="py-2 pr-3 font-semibold">Frame area</th>
            <th className="py-2 font-semibold">Recommended action</th>
          </tr>
        </thead>
        <tbody>
          {detections.map((d) => (
            <tr key={d.id} className="border-t border-white/8">
              <td className="py-2.5 pr-3 font-mono text-xs">#{d.id}</td>
              <td className="py-2.5 pr-3">{d.class_name}</td>
              <td className="py-2.5 pr-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/10">
                    <div className="h-full rounded-full"
                         style={{ width: `${d.confidence * 100}%`,
                                  background: SEVERITY_COLOUR[d.severity] ?? "var(--color-muted)" }} />
                  </div>
                  <span className="font-mono text-xs">{(d.confidence * 100).toFixed(0)}%</span>
                </div>
              </td>
              <td className="py-2.5 pr-3 font-semibold" style={{ color: SEVERITY_COLOUR[d.severity] }}>
                {d.severity}
              </td>
              <td className="py-2.5 pr-3 font-mono text-xs">{d.area_percentage?.toFixed(2)}%</td>
              <td className="py-2.5 text-xs text-[color:var(--color-muted)]">{d.recommended_action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
