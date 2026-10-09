import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { MapContainer, TileLayer, CircleMarker, Polygon, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  Download,
  MapPin,
  AlertTriangle,
  Gauge,
  Target,
  Scan,
  ArrowLeft,
  Save,
  Send,
  CheckCircle,
  Loader2,
  Info,
} from "lucide-react";
import { useDetection } from "../context/DetectionContext";
import { useReports } from "../context/ReportsContext";
import { formatCoordinates, getNearestHyderabadArea, TELANGANA_BOUNDS, TELANGANA_OUTLINE } from "../data/hyderabadGeo";
import { downloadBlob } from "../lib/api";
import { conditionColor, damageLabel, pdfName, prettyClass, riskColor } from "../lib/present";

function ResultLocationMap({ gps }) {
  if (!gps) return null;
  const area = getNearestHyderabadArea(gps);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-2xl border border-line bg-panel shadow-card"
    >
      <div className="flex items-center justify-between border-b border-line px-5 py-4">
        <div>
          <h2 className="font-display text-lg font-semibold text-white">Complaint Location</h2>
          <p className="mt-1 text-sm text-ink/60">{area} | {formatCoordinates(gps)}</p>
        </div>
        <MapPin className="h-5 w-5 text-signal" />
      </div>
      <div className="h-72">
        <MapContainer
          center={[gps.lat, gps.lng]}
          zoom={16}
          minZoom={8}
          className="h-full w-full"
          scrollWheelZoom
          attributionControl={false}
          maxBounds={TELANGANA_BOUNDS}
          maxBoundsViscosity={0.85}
        >
          <TileLayer attribution="" noWrap url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Polygon
            positions={TELANGANA_OUTLINE}
            pathOptions={{ color: "#2563eb", weight: 3, opacity: 0.9, fillColor: "#2563eb", fillOpacity: 0.05 }}
          />
          <CircleMarker
            center={[gps.lat, gps.lng]}
            radius={12}
            pathOptions={{ color: "#ef4444", fillColor: "#ef4444", fillOpacity: 0.72, weight: 3 }}
          >
            <Popup>{area}</Popup>
          </CircleMarker>
        </MapContainer>
      </div>
    </motion.div>
  );
}

export default function DetectionResult() {
  const { result, file, gps, saved, setSaved } = useDetection();
  const { saveAnalysis, submitReport } = useReports();
  const navigate = useNavigate();
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(null);
  const [showOriginal, setShowOriginal] = useState(false);

  useEffect(() => {
    if (!result) navigate("/app/upload");
  }, [result, navigate]);

  if (!result) return null;

  const risk = result.risk || {};
  const point = gps || { lat: result.location.latitude, lng: result.location.longitude };
  const maxConfidence = result.detections?.length
    ? Math.max(...result.detections.map((d) => d.confidence))
    : null;

  const showMsg = (text) => {
    setMessage(text);
    setTimeout(() => setMessage(""), 4000);
  };

  const run = async (key, fn) => {
    setBusy(key);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(null);
    }
  };

  const handleSaveDraft = () =>
    run("draft", async () => {
      const row = await saveAnalysis(result, { submit: false, file });
      setSaved(row);
      showMsg(`Saved as draft ${row.reference} — submit it any time from Reports.`);
    });

  const handleSubmit = () =>
    run("submit", async () => {
      // Already saved as a draft: file that one rather than creating a twin.
      const row = saved
        ? await submitReport(saved.id)
        : await saveAnalysis(result, { submit: true, file });
      setSaved(row);
      showMsg(`Complaint ${row.reference} submitted to ${result.addressed_to || "the municipal authority"}.`);
    });

  const handleDownload = () => {
    if (!result.pdfBlob) {
      setError("The backend did not return a PDF for this analysis.");
      return;
    }
    downloadBlob(result.pdfBlob, result.pdfFilename || pdfName(saved?.reference || result.request_id));
  };

  const cards = [
    {
      icon: Gauge,
      label: "Road Health Score",
      value: `${result.road_health_score.toFixed(2)}/100`,
      sub: `${result.road_condition} condition · ${result.defect_percentage.toFixed(2)}% of the frame damaged`,
      badge: conditionColor[result.road_condition],
    },
    {
      icon: AlertTriangle,
      label: "Road Risk Index",
      value: `${risk.risk_level} · ${Number(risk.risk_index).toFixed(1)}`,
      sub: risk.summary,
      badge: riskColor[risk.risk_level],
    },
    {
      icon: Scan,
      label: "Detected Damage",
      value: damageLabel(result.defect_counts, risk.dominant_defect),
      sub: result.total_defects
        ? `${result.total_defects} defect${result.total_defects === 1 ? "" : "s"} · highest confidence ${(maxConfidence * 100).toFixed(1)}%`
        : "The model found no potholes or cracks in this photo",
      color: "text-signal",
    },
    {
      icon: Target,
      label: "Repair Priority",
      value: risk.priority_tier,
      sub: risk.response_window,
      color: "text-amber-400",
    },
    {
      icon: MapPin,
      label: "GPS Location",
      value: getNearestHyderabadArea(point),
      sub: [
        formatCoordinates(point),
        `Location from: ${result.location.source_label || "Not recorded"}`,
        result.location.photo_taken_at
          ? `Photo taken ${result.location.photo_taken_at.replace(/^(\d{4}):(\d{2}):(\d{2})/, "$3-$2-$1")}`
          : `Analysed ${new Date(result.analysed_at).toLocaleString()}`,
      ].join(" | "),
      color: "text-ink",
    },
  ];

  const filed = saved && saved.status !== "Draft";

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate("/app/upload")}
          className="rounded-lg border border-line p-2 text-muted transition-colors hover:text-ink"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>
        <div>
          <h1 className="font-display text-2xl font-bold text-white lg:text-3xl">Detection Result</h1>
          <p className="mt-2 text-base text-ink/65">AI analysis complete - save, download, or submit</p>
        </div>
      </div>

      {message && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-2 rounded-xl border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm text-green-300"
        >
          <CheckCircle className="h-4 w-4" />
          {message}
        </motion.div>
      )}
      {error && (
        <div role="alert" className="flex items-start gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {error}
        </div>
      )}
      {result.warnings?.length > 0 && (
        <div className="space-y-1 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
          {result.warnings.map((w) => (
            <p key={w} className="flex gap-2"><Info className="mt-0.5 h-4 w-4 shrink-0" />{w}</p>
          ))}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="space-y-3">
          <div className="overflow-hidden rounded-2xl border border-line shadow-card">
            <img
              src={showOriginal || !result.annotatedUrl ? result.photoUrl : result.annotatedUrl}
              alt={showOriginal ? "Original road photograph" : "Road photograph with detected defects boxed"}
              className="w-full object-cover"
            />
          </div>
          {result.annotatedUrl && (
            <div className="flex gap-2 text-sm">
              {["Detections", "Original"].map((label) => {
                const active = (label === "Original") === showOriginal;
                return (
                  <button
                    key={label}
                    onClick={() => setShowOriginal(label === "Original")}
                    className={`rounded-lg px-3 py-1.5 ${active ? "bg-signal/15 text-signal" : "text-ink/60 hover:text-ink"}`}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          )}
        </motion.div>

        <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-4">
          {cards.map((item, i) => (
            <motion.div
              key={item.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className="rounded-xl border border-line bg-panel p-4"
            >
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-signal/10">
                  <item.icon className="h-4 w-4 text-signal" />
                </div>
                <div>
                  <p className="text-xs text-muted">{item.label}</p>
                  <p
                    className={`mt-0.5 font-display text-lg font-semibold ${item.badge ? "" : item.color || "text-white"}`}
                    style={item.badge ? { color: item.badge } : undefined}
                  >
                    {item.value}
                  </p>
                  <p className="text-xs text-muted">{item.sub}</p>
                </div>
              </div>
            </motion.div>
          ))}

          <div className="grid gap-3 pt-2 sm:grid-cols-3">
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleSaveDraft}
              disabled={!!saved || !!busy}
              className="flex items-center justify-center gap-2 rounded-xl border border-line py-3 text-sm font-medium text-ink hover:border-signal hover:text-signal disabled:opacity-40"
            >
              {busy === "draft" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {saved ? "Saved" : "Save Draft"}
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleDownload}
              className="flex items-center justify-center gap-2 rounded-xl border border-line py-3 text-sm font-medium text-ink hover:border-signal hover:text-signal"
            >
              <Download className="h-4 w-4" />
              Download PDF
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleSubmit}
              disabled={filed || !!busy}
              className="flex items-center justify-center gap-2 rounded-xl bg-signal py-3 text-sm font-semibold text-white shadow-card hover:bg-signalDim disabled:opacity-40"
            >
              {busy === "submit" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              {filed ? "Submitted" : "Submit Report"}
            </motion.button>
          </div>
          {saved && (
            <p className="text-xs text-ink/55">
              Report <span className="font-mono text-signal">{saved.reference}</span> is {saved.status.toLowerCase()}.{" "}
              <Link to="/app/reports" className="text-signal hover:underline">Open Reports</Link>
            </p>
          )}
        </motion.div>
      </div>

      {result.detections?.length > 0 && (
        <div className="overflow-hidden rounded-2xl border border-line bg-panel">
          <div className="border-b border-line px-5 py-4">
            <h2 className="font-display text-lg font-semibold text-white">Defect Inventory</h2>
            <p className="mt-1 text-sm text-ink/60">Each row matches a numbered box on the image and in the PDF</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-ink/50">
                  <th className="px-5 py-3 font-medium">#</th>
                  <th className="px-5 py-3 font-medium">Class</th>
                  <th className="px-5 py-3 font-medium">Confidence</th>
                  <th className="px-5 py-3 font-medium">Severity</th>
                  <th className="px-5 py-3 font-medium">Area of frame</th>
                  <th className="px-5 py-3 font-medium">Recommended action</th>
                </tr>
              </thead>
              <tbody>
                {result.detections.map((d) => (
                  <tr key={d.id} className="border-b border-line/50 last:border-0">
                    <td className="px-5 py-3 font-mono text-xs text-signal">{d.id}</td>
                    <td className="px-5 py-3 text-ink/85">{prettyClass(d.class_name)}</td>
                    <td className="px-5 py-3 text-ink/75">{(d.confidence * 100).toFixed(1)}%</td>
                    <td className="px-5 py-3 font-medium" style={{ color: d.severity_colour }}>{d.severity}</td>
                    <td className="px-5 py-3 text-ink/75">{d.area_percentage.toFixed(2)}%</td>
                    <td className="px-5 py-3 text-xs text-ink/60">{d.recommended_action}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ResultLocationMap gps={point} />

      <p className="text-xs leading-relaxed text-ink/45">
        Model {result.model_info?.version || result.model_info?.name}. Scores, severities and risk tiers follow this
        project&apos;s own conventions, not an IRC, MoRTH or GHMC standard — they are a triage aid for the
        engineering wing.
      </p>
    </div>
  );
}
