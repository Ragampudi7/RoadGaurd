import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, CircleMarker, Polygon, Popup, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { LocateFixed, Search } from "lucide-react";
import { useReports } from "../context/ReportsContext";
import { useAuth } from "../context/AuthContext";
import { reports as api } from "../lib/api";
import { fromApi, riskColor, RISK_LEVELS } from "../lib/present";
import {
  HYDERABAD_AREAS,
  HYDERABAD_CENTER,
  isInsideTelangana,
  TELANGANA_BOUNDS,
  TELANGANA_OUTLINE,
} from "../data/hyderabadGeo";

const HYDERABAD_MAP_CENTER = [HYDERABAD_CENTER.lat, HYDERABAD_CENTER.lng];
const cityLocations = HYDERABAD_AREAS.reduce(
  (areas, area) => ({ ...areas, [area.name.toLowerCase().split(",")[0]]: [area.lat, area.lng] }),
  {
    hyderabad: HYDERABAD_MAP_CENTER,
    telangana: HYDERABAD_MAP_CENTER,
    hitech: [17.4435, 78.3772],
    "hitech city": [17.4435, 78.3772],
    "hi tech city": [17.4435, 78.3772],
  }
);

function MapFlyTo({ center, zoom }) {
  const map = useMap();
  useEffect(() => {
    map.setMaxBounds(TELANGANA_BOUNDS);
    if (zoom <= 9) {
      map.fitBounds(TELANGANA_OUTLINE, { padding: [26, 26], animate: true });
    } else {
      map.setView(center, zoom, { animate: true, duration: 0.8 });
    }
  }, [center, map, zoom]);
  return null;
}

export default function MapView() {
  const { reports: userReports } = useReports();
  const { isOfficial } = useAuth();
  const [queue, setQueue] = useState(null);

  // An official sees every filed complaint; a citizen sees their own.
  useEffect(() => {
    if (!isOfficial) return;
    api.list({ mine: false, limit: 200 })
      .then((page) => setQueue(page.items.map(fromApi)))
      .catch(() => setQueue(null));
  }, [isOfficial]);
  const [query, setQuery] = useState("");
  const [target, setTarget] = useState({ center: HYDERABAD_MAP_CENTER, zoom: 8 });
  const [message, setMessage] = useState("");

  const reports = useMemo(() => {
    return (queue || userReports).filter(
      (r) => Number.isFinite(r.lat) && Number.isFinite(r.lng) && isInsideTelangana({ lat: r.lat, lng: r.lng })
    );
  }, [queue, userReports]);

  const nearbyReports = useMemo(() => {
    const text = query.trim().toLowerCase();
    if (!text) return reports;
    return reports.filter((report) => {
      return (
        report.location?.toLowerCase().includes(text) ||
        report.reference?.toLowerCase().includes(text) ||
        report.riskLevel?.toLowerCase().includes(text)
      );
    });
  }, [query, reports]);

  const handleSearch = (event) => {
    event.preventDefault();
    const text = query.trim().toLowerCase();
    const reportMatch = reports.find((report) => report.location?.toLowerCase().includes(text));
    const cityMatch = cityLocations[text];

    if (reportMatch) {
      setTarget({ center: [reportMatch.lat, reportMatch.lng], zoom: 13 });
      setMessage(`Showing potholes near ${reportMatch.location}`);
    } else if (cityMatch) {
      setTarget({ center: cityMatch, zoom: 14 });
      setMessage(`Showing mapped hazards near ${query.trim()}, Hyderabad`);
    } else {
      setMessage("Try Hyderabad, HITEC City, Gachibowli, Madhapur, Jubilee Hills, Banjara Hills, or Secunderabad.");
    }
  };

  const useCurrentLocation = () => {
    if (!navigator.geolocation) {
      setMessage("Current location is not available in this browser.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const point = { lat: pos.coords.latitude, lng: pos.coords.longitude };
        if (isInsideTelangana(point)) {
          setTarget({ center: [point.lat, point.lng], zoom: 14 });
          setMessage("Showing your current Telangana location with nearby Hyderabad pothole markers.");
        } else {
          setTarget({ center: HYDERABAD_MAP_CENTER, zoom: 8 });
          setMessage("Your current location is outside Telangana, so the map stayed focused on Hyderabad.");
        }
      },
      () => setMessage("Location permission was blocked, so the map stayed on the last selected area.")
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="font-display text-2xl font-bold text-white lg:text-3xl">Pothole Map</h1>
          <p className="mt-2 max-w-2xl text-base text-ink/65">
            Search Hyderabad areas or use your Telangana location to see mapped potholes and road damage severity.
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex w-full flex-col gap-3 sm:flex-row lg:max-w-xl">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search Hyderabad area, road, report ID..."
              className="w-full rounded-xl border border-line bg-panel2 py-3 pl-10 pr-4 text-sm text-ink outline-none transition-colors placeholder:text-muted focus:border-signal"
            />
          </div>
          <button className="rounded-xl bg-signal px-5 py-3 text-sm font-semibold text-white shadow-card transition hover:bg-signalDim">
            Search
          </button>
          <button
            type="button"
            onClick={useCurrentLocation}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-line px-4 py-3 text-sm font-semibold text-ink transition hover:border-signal hover:text-signal"
          >
            <LocateFixed className="h-4 w-4" />
            Current
          </button>
        </form>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-4">
          {RISK_LEVELS.map((label) => ({ label, color: riskColor[label] })).map((item) => (
            <div key={item.label} className="flex items-center gap-2 text-sm text-muted">
              <span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.color }} />
              {item.label}
            </div>
          ))}
        </div>
        <p className="text-sm text-muted">
          {nearbyReports.length} {isOfficial ? "filed complaints" : "of your reports"} on the map
        </p>
      </div>

      {message && (
        <div className="rounded-xl border border-signal/20 bg-signal/10 px-4 py-3 text-sm text-ink/80">
          {message}
        </div>
      )}

      <div
        className="overflow-hidden rounded-2xl border border-line shadow-card"
        style={{ height: "calc(100vh - 330px)", minHeight: 430 }}
      >
        <MapContainer
          center={target.center}
          zoom={target.zoom}
          minZoom={7}
          className="h-full w-full"
          scrollWheelZoom
          attributionControl={false}
          maxBounds={TELANGANA_BOUNDS}
          maxBoundsViscosity={0.85}
        >
          <MapFlyTo center={target.center} zoom={target.zoom} />
          <TileLayer
            attribution=""
            noWrap
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Polygon
            positions={TELANGANA_OUTLINE}
            pathOptions={{
              color: "#2563eb",
              weight: 4,
              opacity: 0.95,
              fillColor: "#2563eb",
              fillOpacity: 0.06,
            }}
          >
            <Popup>Telangana service boundary</Popup>
          </Polygon>
          {nearbyReports.map((report) => (
            <CircleMarker
              key={report.id}
              center={[report.lat, report.lng]}
              radius={report.riskLevel === "Critical" ? 14 : report.riskLevel === "High" ? 12 : 10}
              pathOptions={{
                color: riskColor[report.riskLevel] || "#64748b",
                fillColor: riskColor[report.riskLevel] || "#64748b",
                fillOpacity: 0.72,
                weight: 2,
              }}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-semibold">{report.reference}</p>
                  <p className="text-gray-600">{report.area}</p>
                  <p>
                    Risk:{" "}
                    <span style={{ color: riskColor[report.riskLevel], fontWeight: 600 }}>
                      {report.riskLevel} ({report.riskIndex?.toFixed(1)})
                    </span>
                  </p>
                  <p>Road Score: {report.score?.toFixed(1)}/100 · {report.status}</p>
                  <p>{report.damageType} · {report.date}</p>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  );
}
