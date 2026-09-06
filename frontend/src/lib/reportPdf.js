/**
 * Browser-side PDF export via a print window.
 *
 * This is a stand-in. The backend already generates a far better report with
 * ReportLab (vector gauge, weighted risk breakdown, evidence hash, 4 pages);
 * once DetectionContext talks to the real API, prefer `result.report`, which
 * arrives as base64 PDF, and keep this only for demo mode.
 */
const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

export function generateReportPdf(result, { demo = true, imageUrl = null } = {}) {
  const w = window.open("", "_blank", "width=900,height=1000");
  if (!w) {
    // Popup blockers are the usual cause and fail silently otherwise.
    return { ok: false, reason: "popup-blocked" };
  }

  const rows = (result.detections ?? [])
    .map((d) => `<tr>
        <td>#${d.id}</td><td>${esc(d.class_name)}</td>
        <td>${(d.confidence * 100).toFixed(0)}%</td>
        <td>${esc(d.severity)}</td>
        <td>${d.area_percentage?.toFixed(2)}%</td>
        <td>${esc(d.recommended_action)}</td>
      </tr>`).join("");

  w.document.write(`<!doctype html><html><head><meta charset="utf-8">
<title>Road health report ${esc(result.request_id ?? "")}</title>
<style>
  body{font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
       color:#16181d;margin:34px;}
  h1{font-size:20px;margin:0 0 2px} .sub{color:#666;font-size:12px;margin:0 0 18px}
  .demo{border:2px solid #b8860b;background:#fdf6e3;color:#7a5a00;padding:10px 14px;
        border-radius:8px;margin:0 0 18px;font-weight:600}
  .grid{display:flex;gap:14px;margin:0 0 18px;flex-wrap:wrap}
  .box{border:1px solid #dcdfe4;border-radius:9px;padding:12px 15px;min-width:130px}
  .box b{display:block;font-size:21px} .box small{color:#666;font-size:10.5px;
        text-transform:uppercase;letter-spacing:.04em}
  table{width:100%;border-collapse:collapse;font-size:12px;margin-top:6px}
  th,td{text-align:left;padding:7px 8px;border-bottom:1px solid #e6e8ec}
  th{font-size:10.5px;text-transform:uppercase;color:#666;letter-spacing:.04em}
  img{max-width:100%;border:1px solid #dcdfe4;border-radius:8px;margin-top:8px}
  .note{color:#666;font-size:11px;margin-top:22px;line-height:1.45}
</style></head><body>
${demo ? `<div class="demo">DEMO DATA — the figures in this document were generated for demonstration and describe no real road. Not for submission to any authority.</div>` : ""}
<h1>Road Health &amp; Citizen Grievance Report</h1>
<p class="sub">Reference ${esc(result.request_id ?? "-")} &middot;
   ${esc(result.location?.latitude)}, ${esc(result.location?.longitude)} &middot;
   ${new Date(result.analysed_at ?? Date.now()).toLocaleString()}</p>
<div class="grid">
  <div class="box"><b>${result.road_health_score?.toFixed(2)}</b><small>Health score</small></div>
  <div class="box"><b>${esc(result.road_condition)}</b><small>Condition</small></div>
  <div class="box"><b>${result.risk?.risk_index?.toFixed(1)}</b><small>Risk index</small></div>
  <div class="box"><b>${esc(result.risk?.priority_tier)}</b><small>Tier</small></div>
  <div class="box"><b>${result.total_defects}</b><small>Defects</small></div>
</div>
${imageUrl ? `<img src="${imageUrl}" alt="Road photograph">` : ""}
<h3 style="margin:22px 0 0;font-size:14px">Defect inventory</h3>
<table><thead><tr><th>Tag</th><th>Class</th><th>Conf.</th><th>Severity</th>
<th>Frame area</th><th>Recommended action</th></tr></thead><tbody>${rows}</tbody></table>
<h3 style="margin:22px 0 0;font-size:14px">Grievance</h3>
<p style="font-size:12.5px">${esc(result.complaint_description)}</p>
<p style="font-size:12.5px">Addressed to <b>${esc(result.addressed_to)}</b></p>
<p class="note">Automated visual estimate from a single photograph. Score, severity and
risk thresholds are defined by this project and are not taken from IRC, MoRTH, GHMC or any
other official standard. A photograph carries no depth or scale. This does not replace
physical inspection by a qualified engineer.</p>
</body></html>`);
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 350);
  return { ok: true };
}
