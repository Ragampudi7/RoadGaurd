import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, MapPin, Loader2, X } from "lucide-react";
import { useDetection } from "../../context/DetectionContext";
import DemoBadge from "../../components/DemoBadge";

export default function Upload() {
  const { imageUrl, file, setImage, runDetection, busy, error, isMock } = useDetection();
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [geoNote, setGeoNote] = useState("");
  const [drag, setDrag] = useState(false);
  const nav = useNavigate();

  function locate() {
    if (!navigator.geolocation) return setGeoNote("This browser has no geolocation API.");
    setGeoNote("Locating…");
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setLat(p.coords.latitude.toFixed(6));
        setLon(p.coords.longitude.toFixed(6));
        setGeoNote(`Located to within about ${Math.round(p.coords.accuracy)} m.`);
      },
      (e) =>
        // Geolocation needs a secure context. On plain http it fails in a way
        // that reads as a permissions bug, so name the real cause.
        setGeoNote(
          e.code === e.PERMISSION_DENIED
            ? "Permission denied — type the coordinates instead."
            : "Could not locate (needs HTTPS or localhost). Type the coordinates instead."
        ),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function submit(e) {
    e.preventDefault();
    await runDetection({ latitude: lat, longitude: lon });
    nav("/app/result");
  }

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Upload a road photograph</h1>
        {isMock && <DemoBadge />}
      </div>

      {isMock && (
        <div className="glass-soft demo-stripe p-3.5 text-[13px] text-[color:var(--color-fair)]">
          Demo mode: your photo is shown back to you, but the scores come from
          fixed sample data, not from the model. Set <code className="font-mono">VITE_USE_MOCK=false</code>{" "}
          to analyse for real.
        </div>
      )}

      <form onSubmit={submit} className="glass grid gap-5 p-5">
        <div>
          <span className="label">Photograph</span>
          <label
            htmlFor="photo"
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => { e.preventDefault(); setDrag(false); setImage(e.dataTransfer.files?.[0]); }}
            className={`block cursor-pointer rounded-2xl border-2 border-dashed p-6 text-center transition
                        ${drag || imageUrl ? "border-[color:var(--color-brand)]/60 bg-[color:var(--color-brand)]/6"
                                          : "border-white/15 hover:border-white/30"}`}>
            {imageUrl ? (
              <img src={imageUrl} alt="Selected road" className="mx-auto max-h-64 rounded-xl" />
            ) : (
              <UploadCloud size={28} className="mx-auto text-[color:var(--color-muted)]" />
            )}
            <div className="mt-3 text-sm font-medium">
              {file ? file.name : "Drop a photo here, or click to choose"}
            </div>
            <div className="text-xs text-[color:var(--color-muted)]">JPEG, PNG, WEBP or BMP · max 10 MB</div>
          </label>
          <input id="photo" type="file" hidden accept="image/jpeg,image/png,image/webp,image/bmp"
                 onChange={(e) => setImage(e.target.files?.[0])} />
          {file && (
            <button type="button" onClick={() => setImage(null)}
                    className="mt-2 inline-flex items-center gap-1 text-xs text-[color:var(--color-muted)] hover:text-[color:var(--color-danger)] cursor-pointer">
              <X size={13} /> Remove
            </button>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-[1fr_1fr_auto]">
          <div>
            <label className="label" htmlFor="lat">Latitude</label>
            <input id="lat" className="field" type="number" step="any" required
                   placeholder="17.494800" value={lat} onChange={(e) => setLat(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="lon">Longitude</label>
            <input id="lon" className="field" type="number" step="any" required
                   placeholder="78.399600" value={lon} onChange={(e) => setLon(e.target.value)} />
          </div>
          <div className="flex items-end">
            <button type="button" onClick={locate} className="btn btn-ghost w-full sm:w-auto">
              <MapPin size={15} /> Locate me
            </button>
          </div>
        </div>
        {geoNote && <p className="-mt-2 text-xs text-[color:var(--color-muted)]">{geoNote}</p>}

        {error && (
          <div className="glass-soft border-[color:var(--color-danger)]/40 p-3.5 text-[13px] text-[color:var(--color-danger)]" role="alert">
            <strong>{error.code ?? "Request failed"}</strong> — {error.message}
          </div>
        )}

        <div>
          <button className="btn btn-primary" disabled={busy || !file}>
            {busy ? <><Loader2 size={16} className="animate-spin" /> Analysing…</> : "Analyse road"}
          </button>
        </div>
      </form>
    </div>
  );
}
