import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { MapContainer, TileLayer, CircleMarker, Polygon, Popup, useMap, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import {
  Upload,
  Camera,
  Image,
  X,
  MapPin,
  Loader2,
  Save,
  FileText,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";
import { useDetection } from "../context/DetectionContext";
import { getDeviceLocation, readPhotoLocation } from "../lib/photoLocation";
import { usePlaceName } from "../lib/usePlaceName";
import { useSlowHint } from "../lib/useSlowHint";
import WakingNote from "../components/WakingNote";
import { useReports } from "../context/ReportsContext";
import {
  formatCoordinates,
  HYDERABAD_CENTER,
  isInsideTelangana,
  TELANGANA_BOUNDS,
  TELANGANA_OUTLINE,
} from "../data/hyderabadGeo";

const STEPS = [
  "Uploading image...",
  "Running YOLO detection...",
  "Analyzing severity...",
  "Calculating road score...",
  "Generating report...",
];

const DEFAULT_GPS = HYDERABAD_CENTER;
const ACCEPTED = ["image/jpeg", "image/png", "image/webp", "image/bmp"];
const MAX_BYTES = 10 * 1024 * 1024;

// What the citizen is told about where the location came from, or why they
// must tap the map. `tone` picks the colour.
const LOCATION_NOTE = {
  photo: { tone: "ok", text: "Location read from the photo itself." },
  device: { tone: "ok", text: "Location from your phone's GPS, taken just now." },
  map: { tone: "ok", text: "Location set on the map." },
  "need-pin-upload": {
    tone: "warn",
    text: "This photo has no location saved in it (common for WhatsApp images and screenshots). Tap the map where the pothole is.",
  },
  "need-pin-camera": {
    tone: "warn",
    text: "Couldn't get your phone's location. Allow location access, or tap the map where the pothole is.",
  },
  "need-pin-outside": {
    tone: "warn",
    text: "This location is outside Telangana, which this service covers. Tap the map where the pothole is.",
  },
};

function RecenterMap({ point, zoom }) {
  const map = useMap();

  useEffect(() => {
    map.flyTo([point.lat, point.lng], zoom, { duration: 0.7 });
  }, [map, point.lat, point.lng, zoom]);

  return null;
}

function PickOnClick({ onPick }) {
  useMapEvents({
    click(e) {
      onPick?.({ lat: e.latlng.lat, lng: e.latlng.lng });
    },
  });
  return null;
}

function ComplaintLocationMap({ gps, compact = false, onPick, needsPin = false, placeName }) {
  const point = gps || DEFAULT_GPS;
  const zoom = gps ? 16 : 12;
  const area = placeName || formatCoordinates(point);

  return (
    <div className="overflow-hidden rounded-xl border border-line">
      <div className={compact ? "h-[26rem]" : "h-64"}>
        <MapContainer
          center={[point.lat, point.lng]}
          zoom={zoom}
          minZoom={8}
          className="h-full w-full"
          scrollWheelZoom={false}
          dragging
          doubleClickZoom={false}
          zoomControl
          attributionControl={false}
          maxBounds={TELANGANA_BOUNDS}
          maxBoundsViscosity={0.85}
        >
          <RecenterMap point={point} zoom={zoom} />
          <PickOnClick onPick={onPick} />
          <TileLayer
            attribution=""
            noWrap
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <Polygon
            positions={TELANGANA_OUTLINE}
            pathOptions={{
              color: "#2563eb",
              weight: 3,
              opacity: 0.9,
              fillColor: "#2563eb",
              fillOpacity: 0.05,
            }}
          />
          {/* No pin until there is a real location - a grey dot at the city
              centre would read as "the location" when there is none yet. */}
          {gps && (
            <CircleMarker
              center={[point.lat, point.lng]}
              radius={10}
              pathOptions={{ color: "#2563eb", fillColor: "#2563eb", fillOpacity: 0.75, weight: 3 }}
            >
              <Popup>{area}</Popup>
            </CircleMarker>
          )}
        </MapContainer>
      </div>
      <div className="bg-panel2 px-4 py-3 text-xs text-ink/60">
        {gps
          ? `${placeName ? `${placeName} | ` : ""}${formatCoordinates(gps)} — tap the map to correct the pin`
          : needsPin
            ? "Tap the map where the pothole is."
            : "After a photo is selected, this map shows where it was taken."}
      </div>
    </div>
  );
}

export default function UploadPage() {
  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState(null);
  const [gpsSource, setGpsSource] = useState(null);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [stepIndex, setStepIndex] = useState(0);
  const [gps, setGps] = useState(null);
  const [savedMsg, setSavedMsg] = useState("");
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const cameraInputRef = useRef(null);
  const uploadInputRef = useRef(null);
  const { analyzeImage } = useDetection();
  const { saveAnalysis, drafts } = useReports();
  const navigate = useNavigate();

  // gpsSource is "photo" | "device" | "map" once a location is set, or one of
  // the "need-pin-*" reasons while the citizen still has to tap the map.
  const [locating, setLocating] = useState(false);
  const place = usePlaceName(gps);
  const slowAnalysis = useSlowHint(analyzing, 15000);
  const lookupRef = useRef(0); // ignore a slow lookup for a photo since replaced

  // A complaint's location is evidence, so it is never guessed: it comes from
  // the photo, from the phone at the moment of an in-app capture, or from the
  // citizen's tap on the map.
  const locatePhoto = async (file, origin) => {
    const token = ++lookupRef.current;
    setGps(null);
    setGpsSource(null);
    setLocating(true);

    let point = await readPhotoLocation(file);
    let source = "photo";
    if (!point && origin === "camera") {
      point = await getDeviceLocation();
      source = "device";
    }
    if (token !== lookupRef.current) return;
    setLocating(false);

    if (!point) {
      setGpsSource(origin === "camera" ? "need-pin-camera" : "need-pin-upload");
    } else if (!isInsideTelangana(point)) {
      setGpsSource("need-pin-outside");
    } else {
      setGps(point);
      setGpsSource(source);
    }
  };

  const pickOnMap = (point) => {
    if (!isInsideTelangana(point)) return;
    lookupRef.current += 1; // a tap overrides a lookup still in flight
    setLocating(false);
    setGps(point);
    setGpsSource("map");
  };

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setCameraOpen(false);
  }, []);

  // origin: "camera" (just taken, so the phone is at the pothole) or
  // "upload" (from the gallery, so only the photo knows where it was taken).
  const handleFile = useCallback((file, origin = "upload") => {
    if (!file) return;
    // The server enforces the same limits; checking here saves an upload.
    if (!ACCEPTED.includes(file.type)) {
      setError("Use a JPG, PNG, WEBP or BMP photograph.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError("That image is over 10 MB. Use a smaller photo.");
      return;
    }
    setError("");
    if (preview) URL.revokeObjectURL(preview);
    setPhoto(file);
    setPreview(URL.createObjectURL(file));
    stopCamera();
    locatePhoto(file, origin);
  }, [stopCamera, preview]);

  const startCamera = async () => {
    setCameraError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      cameraInputRef.current?.click();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: "environment" } },
        audio: false,
      });
      streamRef.current = stream;
      setCameraOpen(true);
      window.setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
      }, 0);
    } catch {
      setCameraError("Camera could not open. You can still upload an image from files.");
      cameraInputRef.current?.click();
    }
  };

  const captureFromCamera = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;

    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (!blob) return;
      handleFile(new File([blob], `roadguard-${Date.now()}.jpg`, { type: "image/jpeg" }), "camera");
    }, "image/jpeg", 0.92);
  };

  useEffect(() => stopCamera, [stopCamera]);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  };

  const onFileSelect = (e) => {
    handleFile(e.target.files[0], "upload");
    e.target.value = ""; // allow choosing the same file again
  };

  const onCameraFile = (e) => {
    handleFile(e.target.files[0], "camera");
    e.target.value = "";
  };

  const clearPreview = () => {
    if (preview) URL.revokeObjectURL(preview);
    setPhoto(null);
    setPreview(null);
    setGps(null);
    setGpsSource(null);
    setLocating(false);
    lookupRef.current += 1;
    setError("");
    stopCamera();
  };

  /**
   * Runs the real model. The step labels advance on a timer while the request
   * is in flight (inference takes 2-10 s on CPU) but the bar never reaches
   * 100% until the backend has actually answered.
   */
  const runAnalysis = async () => {
    setAnalyzing(true);
    setError("");
    setProgress(5);
    setStepIndex(0);
    let step = 0;
    const timer = setInterval(() => {
      step = Math.min(step + 1, STEPS.length - 1);
      setStepIndex(step);
      setProgress((p) => Math.min(p + 15, 90));
    }, 900);
    try {
      const result = await analyzeImage(photo, gps, gpsSource);
      setStepIndex(STEPS.length - 1);
      setProgress(100);
      return result;
    } finally {
      clearInterval(timer);
      setAnalyzing(false);
    }
  };

  const handleAnalyze = async () => {
    if (!photo || !gps || analyzing) return;
    try {
      await runAnalysis();
      navigate("/app/result");
    } catch (e) {
      setError(e.message);
    }
  };

  // The backend stores a report together with its analysis, so "save draft"
  // analyses first and files the result as an unsent draft.
  const handleSaveDraft = async () => {
    if (!photo || !gps || analyzing) return;
    try {
      const result = await runAnalysis();
      const row = await saveAnalysis(result, { submit: false, file: photo });
      setSavedMsg(`Draft ${row.reference} saved. Submit it from Reports when ready.`);
      setTimeout(() => setSavedMsg(""), 4000);
    } catch (e) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-2xl font-bold text-white lg:text-3xl">Create Complaint</h1>
        <p className="mt-2 text-base text-ink/65">
          Capture a road image, attach GPS, save as draft, or run AI analysis instantly
        </p>
      </div>

      <div className={`grid gap-8 ${preview ? "xl:grid-cols-[minmax(0,0.95fr)_minmax(420px,1.05fr)]" : "lg:grid-cols-5"}`}>
        <div className={preview ? "" : "lg:col-span-3"}>
          {error && (
            <div role="alert" className="mb-4 flex items-start gap-2 rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-300">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              {error}
            </div>
          )}
          <AnimatePresence mode="wait">
            {analyzing ? (
              <motion.div
                key="analyzing"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
                className="rounded-2xl border border-line bg-panel p-10 text-center"
              >
                <Loader2 className="mx-auto h-12 w-12 animate-spin text-signal" />
                <p className="mt-6 font-display text-lg font-semibold text-white">
                  {STEPS[stepIndex] || STEPS[STEPS.length - 1]}
                </p>
                <div className="mx-auto mt-6 h-2 max-w-md overflow-hidden rounded-full bg-panel2">
                  <motion.div
                    className="h-full rounded-full bg-signal"
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3 }}
                  />
                </div>
                <p className="mt-3 text-sm text-ink/60">{Math.round(progress)}% complete</p>
                {slowAnalysis && (
                  <div className="mx-auto mt-6 max-w-md text-left">
                    <WakingNote>
                      Taking longer than usual: the server has just started and the AI model is
                      still loading. The first analysis after a restart can take about a minute.
                    </WakingNote>
                  </div>
                )}
              </motion.div>
            ) : (
              <motion.div key="upload" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                {!preview ? (
                  <div
                    onDragOver={(e) => {
                      e.preventDefault();
                      setDragging(true);
                    }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={onDrop}
                    className={`rounded-2xl border-2 border-dashed p-8 text-center transition-all sm:p-10 ${
                      dragging
                        ? "border-signal bg-signal/10"
                        : "border-line bg-panel2 hover:border-signal/50"
                    }`}
                  >
                    <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-signal/15">
                      <Camera className="h-7 w-7 text-signal" />
                    </div>
                    <p className="mt-5 font-display text-lg font-semibold text-white">
                      Capture or upload road evidence
                    </p>
                    <p className="mx-auto mt-2 max-w-md text-sm text-ink/60">
                      Use your camera at the pothole location or upload an existing JPG, PNG, or WEBP image.
                    </p>

                    <div className="mx-auto mt-7 grid max-w-lg gap-3 sm:grid-cols-2">
                      <input
                        ref={cameraInputRef}
                        type="file"
                        accept="image/jpeg,image/png,image/webp,image/bmp"
                        capture="environment"
                        onChange={onCameraFile}
                        className="sr-only"
                      />
                      <button
                        type="button"
                        onClick={startCamera}
                        className="group rounded-xl border border-signal/30 bg-signal px-5 py-4 text-white shadow-glow transition hover:bg-signalDim"
                      >
                        <span className="flex items-center justify-center gap-2 font-semibold">
                          <Camera className="h-4 w-4" />
                          Take Photo
                        </span>
                        <span className="mt-1 block text-xs text-white/75">Open device camera</span>
                      </button>

                      <label className="group cursor-pointer rounded-xl border border-line bg-panel px-5 py-4 text-ink transition hover:border-signal hover:text-white">
                        <input
                          ref={uploadInputRef}
                          type="file"
                          accept="image/jpeg,image/png,image/webp,image/bmp"
                          onChange={onFileSelect}
                          className="sr-only"
                        />
                        <span className="flex items-center justify-center gap-2 font-semibold">
                          <Upload className="h-4 w-4" />
                          Upload Image
                        </span>
                        <span className="mt-1 block text-xs text-ink/55">Browse gallery or files</span>
                      </label>
                    </div>

                    {cameraError && (
                      <p className="mt-4 text-sm text-amber-300">{cameraError}</p>
                    )}

                    {cameraOpen && (
                      <div className="mx-auto mt-6 max-w-2xl overflow-hidden rounded-2xl border border-line bg-base text-left">
                        <video ref={videoRef} playsInline muted className="max-h-80 w-full object-cover" />
                        <canvas ref={canvasRef} className="hidden" />
                        <div className="flex flex-col gap-3 p-4 sm:flex-row">
                          <button
                            type="button"
                            onClick={captureFromCamera}
                            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-signal px-5 py-3 font-semibold text-white hover:bg-signalDim"
                          >
                            <Camera className="h-4 w-4" />
                            Capture Photo
                          </button>
                          <button
                            type="button"
                            onClick={stopCamera}
                            className="rounded-xl border border-line px-5 py-3 font-medium text-ink hover:border-signal hover:text-signal"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    )}

                    <p className="mt-5 text-xs text-ink/45">Drag and drop also works on desktop.</p>
                  </div>
                ) : (
                  <div className="space-y-4 rounded-2xl border border-line bg-panel p-5">
                    <div className="relative overflow-hidden rounded-xl">
                      <img src={preview} alt="Preview" className="max-h-72 w-full object-cover" />
                      <button
                        onClick={clearPreview}
                        className="absolute right-3 top-3 rounded-lg bg-base/80 p-2 text-ink backdrop-blur-sm hover:text-white"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>

                    {gps && (
                      <div className="flex items-start gap-3 rounded-xl border border-line bg-panel2 px-4 py-3 text-sm text-ink/75">
                        <MapPin className="h-4 w-4 text-signal" />
                        <div>
                          <p data-testid="place-name" className="font-semibold text-white">
                            {place.label || (place.loading ? "Looking up the address..." : "Place name unavailable")}
                          </p>
                          <p className="text-xs text-ink/55">Latitude {gps.lat.toFixed(4)} | Longitude {gps.lng.toFixed(4)}</p>
                          {LOCATION_NOTE[gpsSource] && (
                            <p data-testid="location-note" className="mt-1 text-xs text-green-300">
                              {LOCATION_NOTE[gpsSource].text} Wrong spot? Tap the map to move the pin.
                            </p>
                          )}
                        </div>
                      </div>
                    )}

                    {locating && (
                      <div className="flex items-center gap-2 rounded-xl border border-line bg-panel2 px-4 py-3 text-sm text-ink/70">
                        <Loader2 className="h-4 w-4 animate-spin text-signal" />
                        Finding where this photo was taken...
                      </div>
                    )}

                    {!gps && !locating && LOCATION_NOTE[gpsSource] && (
                      <div data-testid="location-note" className="flex items-start gap-2 rounded-xl border border-amber-500/40 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                        <MapPin className="mt-0.5 h-4 w-4 shrink-0" />
                        {LOCATION_NOTE[gpsSource].text}
                      </div>
                    )}

                    {savedMsg && (
                      <div className="flex items-center gap-2 rounded-xl border border-green-500/30 bg-green-500/10 px-4 py-3 text-sm text-green-400">
                        <CheckCircle className="h-4 w-4" />
                        {savedMsg}
                      </div>
                    )}

                    <div className="grid gap-3 sm:grid-cols-2">
                      <motion.button
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        onClick={handleSaveDraft}
                        disabled={!gps}
                        className="flex items-center justify-center gap-2 rounded-xl border border-line py-3.5 font-medium text-ink transition-colors hover:border-signal hover:text-signal disabled:opacity-40"
                      >
                        <Save className="h-4 w-4" />
                        Save as Draft
                      </motion.button>
                      <motion.button
                        whileHover={{ scale: 1.01 }}
                        whileTap={{ scale: 0.99 }}
                        onClick={handleAnalyze}
                        disabled={!gps}
                        className="flex items-center justify-center gap-2 rounded-xl bg-signal py-3.5 font-semibold text-white shadow-glow hover:bg-signalDim disabled:opacity-40"
                      >
                        <Image className="h-4 w-4" />
                        Analyze Now
                      </motion.button>
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        <div className={preview ? "space-y-6" : "lg:col-span-2 space-y-6"}>
          <div className="overflow-hidden rounded-2xl border border-line bg-panel">
            <ComplaintLocationMap gps={gps} compact={!!preview} onPick={preview && !analyzing ? pickOnMap : undefined}
              needsPin={!!preview && !gps && !locating}
              placeName={place.label}
            />
            <div className="bg-panel p-5">
              <h3 className="font-display text-lg font-semibold text-white">Complaint Location</h3>
              <p className="mt-2 text-sm leading-relaxed text-ink/65">
                The location comes from the photo itself, or from your phone when you take the photo here. If neither is available, tap the spot on the map. You can always tap to correct the pin.
              </p>
              <ul className="mt-4 space-y-2.5 text-sm text-ink/70">
                <li className="flex gap-2">
                  <span className="font-bold text-signal">1.</span> Select or capture the road photo
                </li>
                <li className="flex gap-2">
                  <span className="font-bold text-signal">2.</span> GPS pins the location — tap the map to correct it
                </li>
                <li className="flex gap-2">
                  <span className="font-bold text-signal">3.</span> Save, analyze, or submit with the location attached
                </li>
              </ul>
            </div>
          </div>

          {drafts.length > 0 && (
            <div className="rounded-2xl border border-line bg-panel p-5">
              <div className="flex items-center justify-between">
                <h3 className="font-display font-semibold text-white">Saved Drafts</h3>
                <span className="rounded-full bg-amber-500/15 px-2.5 py-0.5 text-xs font-medium text-amber-400">
                  {drafts.length}
                </span>
              </div>
              <ul className="mt-4 space-y-2">
                {drafts.slice(0, 3).map((d) => (
                  <li
                    key={d.id}
                    className="flex items-center gap-3 rounded-lg border border-line bg-panel2 px-3 py-2.5 text-sm"
                  >
                    <FileText className="h-4 w-4 shrink-0 text-signal" />
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-mono text-xs text-signal">{d.reference}</div>
                      <div className="truncate text-xs text-ink/50">{d.area} · {d.date}</div>
                    </div>
                  </li>
                ))}
              </ul>
              <Link to="/app/reports" className="mt-3 block text-sm font-medium text-signal hover:underline">
                View all in Reports {"->"}
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
