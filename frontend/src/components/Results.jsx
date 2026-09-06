import { CONDITION_COLOUR, RISK_COLOUR, SEVERITY_COLOUR } from "../api";
import "./results.css";

/* ---------------------------------------------------------------- gauge --
   Same 3/4-circle arc as the PDF report's Road Health Index, so the screen
   and the printed grievance look like one document. Score runs 0-100 and
   higher is better, which is the opposite direction to the risk meter. */
export function ScoreGauge({ score, condition, size = 168 }) {
  const stroke = 14;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const SWEEP = 270; // degrees of arc
  const START = 135; // start angle, bottom-left

  const polar = (deg) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
  };
  const arc = (fromDeg, toDeg) => {
    const [x1, y1] = polar(fromDeg);
    const [x2, y2] = polar(toDeg);
    const large = toDeg - fromDeg > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
  };

  const pct = Math.max(0, Math.min(100, Number(score ?? 0))) / 100;
  const colour = CONDITION_COLOUR[condition] ?? "var(--muted)";

  return (
    <div className="gauge">
      <svg width={size} height={size} role="img"
           aria-label={`Road health score ${score} out of 100, condition ${condition}`}>
        <path d={arc(START, START + SWEEP)} fill="none" stroke="var(--line)"
              strokeWidth={stroke} strokeLinecap="round" />
        {pct > 0 && (
          <path d={arc(START, START + SWEEP * pct)} fill="none" stroke={colour}
                strokeWidth={stroke} strokeLinecap="round" />
        )}
      </svg>
      <div className="gaugetext">
        <b style={{ color: colour }}>{Number(score ?? 0).toFixed(2)}</b>
        <small>out of 100</small>
      </div>
      <div className="chip" style={{ background: colour }}>{condition}</div>
    </div>
  );
}

/* ----------------------------------------------------------------- risk --
   Shows the weighted components too. Without them the index is a number the
   user has to take on faith; with them it is auditable. */
export function RiskPanel({ risk }) {
  if (!risk) return null;
  const colour = RISK_COLOUR[risk.risk_level] ?? "var(--muted)";
  return (
    <div className="card stack">
      <div className="riskhead">
        <div className="riskbig" style={{ borderColor: colour }}>
          <b style={{ color: colour }}>{risk.risk_index?.toFixed(1)}</b>
          <small>Risk index / 100</small>
        </div>
        <div>
          <div className="chip solid" style={{ background: colour }}>{risk.risk_level} risk</div>
          <div className="small" style={{ marginTop: 8 }}>
            <strong>{risk.priority_tier}</strong>
          </div>
          <div className="small muted">{risk.response_window}</div>
        </div>
      </div>

      {risk.components?.length > 0 && (
        <div className="components">
          {risk.components.map((c) => (
            <div className="comp" key={c.name}>
              <div className="complabel">
                <span>{c.name}</span>
                <span className="muted small">weight {(c.weight * 100).toFixed(0)}%</span>
              </div>
              <div className="track">
                <div className="fill" style={{ width: `${Math.min(100, c.value)}%`, background: colour }} />
              </div>
              <div className="small muted">{c.detail ?? ""}</div>
            </div>
          ))}
        </div>
      )}

      <p className="small muted" style={{ margin: 0 }}>{risk.summary}</p>
    </div>
  );
}

/* ----------------------------------------------------------- detections -- */
export function DetectionTable({ detections }) {
  if (!detections?.length) {
    return <p className="muted small">No defects were detected in this photograph.</p>;
  }
  return (
    <div className="scroll-x">
      <table>
        <thead>
          <tr>
            <th>Tag</th><th>Class</th><th>Confidence</th>
            <th>Severity</th><th>Frame area</th><th>Recommended action</th>
          </tr>
        </thead>
        <tbody>
          {detections.map((d) => (
            <tr key={d.id}>
              <td className="mono">#{d.id}</td>
              <td>{d.class_name}</td>
              <td>
                <div className="confbar">
                  <div className="track sm">
                    <div className="fill" style={{
                      width: `${d.confidence * 100}%`,
                      background: SEVERITY_COLOUR[d.severity] ?? "var(--muted)",
                    }} />
                  </div>
                  <span className="mono small">{(d.confidence * 100).toFixed(0)}%</span>
                </div>
              </td>
              <td>
                <span className="sev" style={{ color: SEVERITY_COLOUR[d.severity] }}>
                  {d.severity}
                </span>
              </td>
              <td className="mono">{d.area_percentage?.toFixed(2)}%</td>
              <td className="small">{d.recommended_action}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
