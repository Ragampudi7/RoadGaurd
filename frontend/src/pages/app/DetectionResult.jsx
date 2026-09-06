import { Link, useNavigate } from "react-router-dom";
import { FileDown, Save, RotateCcw, ImageOff } from "lucide-react";
import { useDetection } from "../../context/DetectionContext";
import { useReports } from "../../context/ReportsContext";
import { ScoreGauge, RiskPanel, DetectionTable } from "../../components/Results";
import DemoBadge from "../../components/DemoBadge";
import { generateReportPdf } from "../../lib/reportPdf";
import { useState } from "react";

export default function DetectionResult() {
  const { result, imageUrl, clear, isMock } = useDetection();
  const { saveDraft } = useReports();
  const nav = useNavigate();
  const [saved, setSaved] = useState(null);

  if (!result) {
    return (
      <div className="glass grid place-items-center gap-3 p-12 text-center">
        <ImageOff size={26} className="text-[color:var(--color-muted)]" />
        <p className="text-[color:var(--color-muted)]">No analysis yet.</p>
        <Link to="/app/upload" className="btn btn-primary">Upload a photograph</Link>
      </div>
    );
  }

  function onSave() {
    const row = saveDraft({
      title: `Report at ${result.location.latitude.toFixed(4)}, ${result.location.longitude.toFixed(4)}`,
      score: result.road_health_score,
      condition: result.road_condition,
      risk_index: result.risk.risk_index,
      risk_level: result.risk.risk_level,
      tier: result.risk.priority_tier,
      defects: result.total_defects,
      lat: result.location.latitude,
      lon: result.location.longitude,
      is_demo: !!result.is_demo,
    });
    setSaved(row.id);
  }

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Detection result</h1>
        {(isMock || result.is_demo) && <DemoBadge />}
        <div className="ml-auto flex flex-wrap gap-2">
          <button className="btn btn-ghost" onClick={() => { clear(); nav("/app/upload"); }}>
            <RotateCcw size={15} /> New analysis
          </button>
          <button className="btn btn-ghost" onClick={onSave} disabled={!!saved}>
            <Save size={15} /> {saved ? `Saved ${saved}` : "Save as draft"}
          </button>
          <button className="btn btn-primary"
                  onClick={() => generateReportPdf(result, { demo: isMock || result.is_demo, imageUrl })}>
            <FileDown size={15} /> Export PDF
          </button>
        </div>
      </div>

      {(isMock || result.is_demo) && (
        <div className="glass-soft demo-stripe p-3.5 text-[13px] text-[color:var(--color-fair)]">
          These figures are sample data and describe no real road. The exported
          PDF is watermarked accordingly and must not be submitted to any authority.
        </div>
      )}

      {result.warnings?.map((w, i) => (
        <div key={i} className="glass-soft border-[color:var(--color-fair)]/35 p-3.5 text-[13px] text-[color:var(--color-fair)]">{w}</div>
      ))}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="glass grid place-items-center gap-5 p-5">
          <ScoreGauge score={result.road_health_score} condition={result.road_condition} />
          <div className="grid w-full grid-cols-3 gap-3">
            {[
              [result.total_defects, "Defects"],
              [`${result.defect_percentage?.toFixed(2)}%`, "Frame damaged"],
              [`${result.processing_time_ms} ms`, "Processing"],
            ].map(([v, l]) => (
              <div key={l} className="glass-soft p-3 text-center">
                <div className="text-lg font-semibold">{v}</div>
                <div className="text-[10.5px] uppercase tracking-wider text-[color:var(--color-muted)]">{l}</div>
              </div>
            ))}
          </div>
        </div>

        <RiskPanel risk={result.risk} />
      </div>

      {(result.annotated_image?.data || imageUrl) && (
        <div className="glass grid gap-3 p-5">
          <h2 className="font-semibold">Visual evidence</h2>
          <img
            src={result.annotated_image?.data
              ? `data:${result.annotated_image.mime_type};base64,${result.annotated_image.data}`
              : imageUrl}
            alt="Road photograph"
            className="max-h-[70vh] w-full rounded-xl border border-white/10 object-contain" />
          {!result.annotated_image?.data && (
            <p className="text-xs text-[color:var(--color-muted)]">
              Your original photograph — the model did not run, so there are no
              boxes drawn on it.
            </p>
          )}
        </div>
      )}

      <div className="glass grid gap-3 p-5">
        <h2 className="font-semibold">Defect inventory</h2>
        <DetectionTable detections={result.detections} />
      </div>

      <div className="glass grid gap-2.5 p-5">
        <h2 className="font-semibold">Grievance</h2>
        <p className="text-[13.5px] leading-relaxed">{result.complaint_description}</p>
        <p className="text-xs text-[color:var(--color-muted)]">
          Addressed to <strong className="text-[color:var(--color-ink)]">{result.addressed_to}</strong>
          {" · "}evidence SHA-256 <span className="font-mono">{result.image?.sha256?.slice(0, 16)}…</span>
        </p>
      </div>
    </div>
  );
}
