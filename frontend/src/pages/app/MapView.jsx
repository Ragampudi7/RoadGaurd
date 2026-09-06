import { useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import { Search, Crosshair } from "lucide-react";
import "leaflet/dist/leaflet.css";
import { useReports } from "../../context/ReportsContext";
import { RISK_COLOUR, STATUS_COLOUR } from "../../lib/mockData";

/* A few Indian cities so the search does something useful without a geocoding
   API key. Anything else falls through to "not found" rather than pretending. */
const CITIES = {
  hyderabad: [17.385, 78.4867],
  bengaluru: [12.9716, 77.5946],
  bangalore: [12.9716, 77.5946],
  chennai: [13.0827, 80.2707],
  mumbai: [19.076, 72.8777],
  delhi: [28.6139, 77.209],
  pune: [18.5204, 73.8567],
  kolkata: [22.5726, 88.3639],
};

/** Imperative map moves have to happen from inside MapContainer. */
function Recenter({ target }) {
  const map = useMap();
  if (target) map.flyTo(target, target[2] ?? 13, { duration: 0.8 });
  return null;
}

export default function MapView() {
  const { reports } = useReports();
  const [query, setQuery] = useState("");
  const [note, setNote] = useState("");
  const [target, setTarget] = useState(null);

  const pins = useMemo(
    () => reports.filter((r) => typeof r.lat === "number" && typeof r.lon === "number"),
    [reports]
  );

  const centre = pins.length
    ? [pins.reduce((s, r) => s + r.lat, 0) / pins.length,
       pins.reduce((s, r) => s + r.lon, 0) / pins.length]
    : [17.385, 78.4867];

  function search(e) {
    e.preventDefault();
    const hit = CITIES[query.trim().toLowerCase()];
    if (hit) { setTarget([...hit, 12]); setNote(""); }
    else setNote(`No coordinates for "${query}". Known: ${Object.keys(CITIES).slice(0, 6).join(", ")}.`);
  }

  function locate() {
    if (!navigator.geolocation) return setNote("This browser has no geolocation API.");
    navigator.geolocation.getCurrentPosition(
      (p) => { setTarget([p.coords.latitude, p.coords.longitude, 15]); setNote(""); },
      () => setNote("Could not locate you (geolocation needs HTTPS or localhost)."),
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold tracking-tight">Reported locations</h1>
        <span className="text-sm text-[color:var(--color-muted)]">{pins.length} pinned</span>
      </div>

      <form onSubmit={search} className="flex flex-wrap gap-2">
        <div className="relative min-w-56 flex-1">
          <Search size={15} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[color:var(--color-muted)]" />
          <input className="field pl-9" placeholder="Jump to a city — try Hyderabad"
                 value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <button className="btn btn-ghost" type="submit">Search</button>
        <button className="btn btn-ghost" type="button" onClick={locate}>
          <Crosshair size={15} /> My location
        </button>
      </form>
      {note && <p className="-mt-2 text-xs text-[color:var(--color-muted)]">{note}</p>}

      <div className="glass overflow-hidden p-1.5">
        <MapContainer center={centre} zoom={11} scrollWheelZoom
                      style={{ height: "clamp(360px, 62vh, 640px)", width: "100%", borderRadius: "0.85rem" }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <Recenter target={target} />

          {pins.map((r) => {
            const colour = RISK_COLOUR[r.risk_level] ?? "var(--color-minor)";
            // Radius carries severity too, so risk is not signalled by colour alone.
            const radius = 7 + (r.risk_index ?? 0) / 12;
            return (
              <CircleMarker key={r.id} center={[r.lat, r.lon]} radius={radius}
                pathOptions={{ color: colour, fillColor: colour, fillOpacity: 0.42, weight: 2 }}>
                <Popup>
                  <div className="min-w-52">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[11px] opacity-70">{r.id}</span>
                      <span className="chip text-white" style={{ background: STATUS_COLOUR[r.status] }}>{r.status}</span>
                    </div>
                    <div className="mt-1 font-semibold">{r.title}</div>
                    <div className="mt-1 text-[12px] opacity-80">
                      Score {r.score?.toFixed(1)} · {r.condition}<br />
                      Risk {r.risk_index?.toFixed(1)} ({r.risk_level}) · {r.tier}<br />
                      {r.defects} defects
                    </div>
                    <a className="mt-1.5 inline-block text-[12px]"
                       href={`https://www.openstreetmap.org/?mlat=${r.lat}&mlon=${r.lon}#map=18/${r.lat}/${r.lon}`}
                       target="_blank" rel="noreferrer">Open in OpenStreetMap</a>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>

      {/* legend: risk is ordered, so it is listed in order with labels, never colour alone */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs text-[color:var(--color-muted)]">
        <span className="font-medium text-[color:var(--color-ink)]">Risk level</span>
        {["Low", "Moderate", "High", "Critical"].map((k) => (
          <span key={k} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLOUR[k] }} />
            {k}
          </span>
        ))}
        <span className="opacity-70">· marker size also scales with the risk index</span>
      </div>
    </div>
  );
}
