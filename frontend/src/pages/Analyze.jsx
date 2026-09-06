import { useEffect, useRef, useState } from "react";
import { analyze, b64ToUrl } from "../api";
import { ScoreGauge, RiskPanel, DetectionTable } from "../components/Results";

export default function Analyze() {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [geoNote, setGeoNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [media, setMedia] = useState({ annotated: null, pdf: null, pdfName: null, crops: [] });
  const abortRef = useRef(null);

  // Blob URLs are not garbage collected on their own; release them when the
  // component unmounts or the media is replaced by a fresh analysis.
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    return () => {
      if (media.annotated) URL.revokeObjectURL(media.annotated);
      if (media.pdf) URL.revokeObjectURL(media.pdf);
      media.crops.forEach((c) => URL.revokeObjectURL(c.url));
    };
  }, [media]);

  function pickFile(f) {
    if (!f) return;
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setError(null);
  }

  function useMyLocation() {
    if (!navigator.geolocation) {
      setGeoNote("This browser has no geolocation API.");
      return;
    }
    setGeoNote("Locating…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6));
        setLon(pos.coords.longitude.toFixed(6));
        setGeoNote(`Located to within about ${Math.round(pos.coords.accuracy)} m.`);
      },
      (err) => {
        // Geolocation needs a secure context; on plain http it fails silently
        // in a way that looks like a permissions bug, so say so explicitly.
        setGeoNote(
          err.code === err.PERMISSION_DENIED
            ? "Location permission denied — type the coordinates instead."
            : "Could not get a location (needs HTTPS or localhost). Type the coordinates instead."
        );
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function onSubmit(e) {
    e.preventDefault();
    if (!file) return setError(new Error("Choose a road photograph first."));

    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    setBusy(true);
    setError(null);
    setResult(null);

    try {
      const data = await analyze({
        file,
        latitude: Number(lat),
        longitude: Number(lon),
        signal: ctrl.signal,
      });

      setResult(data);
      setMedia({
        annotated: data.annotated_image?.data
          ? b64ToUrl(data.annotated_image.data, data.annotated_image.mime_type) : null,
        pdf: data.report?.data
          ? b64ToUrl(data.report.data, data.report.mime_type) : null,
        pdfName: data.report?.filename,
        // Crops carry no detection metadata of their own - they are emitted one
        // per detection, in detection order, so the tag and class come from the
        // matching entry in `detections`.
        crops: (data.defect_crops ?? []).map((c, i) => {
          const det = data.detections?.[i];
          return {
            id: det?.id ?? i + 1,
            label: det?.class_name ?? "defect",
            severity: det?.severity,
            url: b64ToUrl(c.data, c.mime_type),
          };
        }),
      });
    } catch (err) {
      if (err.name !== "AbortError") setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <h1 className="pagehead">Analyse a road photograph</h1>
      <p className="pagesub">
        Upload a photo and its coordinates. The server detects surface defects,
        scores the road, estimates remediation urgency and returns a
        complaint-ready PDF.
      </p>

      <form className="card stack" onSubmit={onSubmit}>
        <div>
          <label htmlFor="photo">Road photograph</label>
          <label className={`dropzone ${file ? "has" : ""}`} htmlFor="photo">
            {previewUrl && <img src={previewUrl} alt="Selected road photograph" />}
            <div className="small">
              {file ? <strong>{file.name}</strong> : "Choose a JPEG, PNG, WEBP or BMP"}
            </div>
            <div className="small muted">Maximum 10 MB</div>
          </label>
          <input id="photo" type="file" hidden
                 accept="image/jpeg,image/png,image/webp,image/bmp"
                 onChange={(e) => pickFile(e.target.files?.[0])} />
        </div>

        <div className="row">
          <div>
            <label htmlFor="lat">Latitude</label>
            <input id="lat" type="number" step="any" required placeholder="17.494800"
                   value={lat} onChange={(e) => setLat(e.target.value)} />
          </div>
          <div>
            <label htmlFor="lon">Longitude</label>
            <input id="lon" type="number" step="any" required placeholder="78.399600"
                   value={lon} onChange={(e) => setLon(e.target.value)} />
          </div>
          <div style={{ display: "flex", alignItems: "flex-end" }}>
            <button type="button" className="ghost" onClick={useMyLocation}>
              Use my location
            </button>
          </div>
        </div>
        {geoNote && <div className="small muted">{geoNote}</div>}

        <div>
          <button type="submit" disabled={busy || !file}>
            {busy ? "Analysing…" : "Analyse road"}
          </button>
          {busy && (
            <span className="small muted" style={{ marginLeft: 12 }}>
              CPU inference plus PDF generation — usually a second or two.
            </span>
          )}
        </div>
      </form>

      {error && (
        <div className="banner err" style={{ marginTop: 16 }} role="alert">
          <strong>{error.code ?? "Request failed"}</strong> — {error.message}
        </div>
      )}

      {result && (
        <div className="stack" style={{ marginTop: 20 }}>
          {result.warnings?.map((w, i) => (
            <div className="banner warn" key={i}>{w}</div>
          ))}

          <div className="grid2">
            <div className="card" style={{ display: "grid", placeItems: "center", gap: 14 }}>
              <ScoreGauge score={result.road_health_score} condition={result.road_condition} />
              <div className="tiles" style={{ width: "100%" }}>
                <div className="tile">
                  <b>{result.total_defects}</b><small>Defects</small>
                </div>
                <div className="tile">
                  <b>{result.defect_percentage?.toFixed(2)}%</b><small>Frame damaged</small>
                </div>
                <div className="tile">
                  <b>{result.processing_time_ms} ms</b><small>Processing</small>
                </div>
              </div>
            </div>

            <RiskPanel risk={result.risk} />
          </div>

          {media.annotated && (
            <div className="card stack">
              <h2 style={{ margin: 0, fontSize: 16 }}>Visual evidence</h2>
              <img className="preview" src={media.annotated} alt="Road photograph with detected defects outlined" />
              {media.crops.length > 0 && (
                <div className="crops">
                  {media.crops.map((c, i) => (
                    <div className="crop" key={i}>
                      <img src={c.url} alt={`Close-up of detection ${c.id}`} />
                      <div className="capt">
                        <strong>#{c.id}</strong> · {c.label}
                        {c.severity && (
                          <span className="muted"> · {c.severity}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="card stack">
            <h2 style={{ margin: 0, fontSize: 16 }}>Defect inventory</h2>
            <DetectionTable detections={result.detections} />
          </div>

          <div className="card stack">
            <h2 style={{ margin: 0, fontSize: 16 }}>Grievance</h2>
            <p className="small" style={{ margin: 0 }}>{result.complaint_description}</p>
            <p className="small muted" style={{ margin: 0 }}>
              Addressed to <strong>{result.addressed_to}</strong> ·
              evidence SHA-256 <span className="mono">{result.image?.sha256?.slice(0, 16)}…</span>
            </p>
            {media.pdf && (
              <div>
                <a href={media.pdf} download={media.pdfName ?? `road-report-${result.request_id ?? "report"}.pdf`}>
                  <button type="button">Download PDF report</button>
                </a>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
