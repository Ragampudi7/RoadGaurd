import { createContext, useContext, useEffect, useRef, useState } from "react";
import { analyze as callAnalyze, b64ToBlob } from "../lib/api";

/**
 * The analysis in progress: the photograph, where it was taken, and the
 * backend's AnalyzeResponse for it.
 *
 * `result` is the backend response untouched, plus two object URLs made from
 * its base64 payloads: the annotated image (real model boxes) and the PDF the
 * backend generated. `saved` remembers the report once it has been filed so a
 * second click updates nothing twice.
 */
const DetectionContext = createContext(null);

export function DetectionProvider({ children }) {
  const [file, setFile] = useState(null);
  const [gps, setGps] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(null);
  const urls = useRef([]);

  const revokeAll = () => {
    urls.current.forEach((u) => URL.revokeObjectURL(u));
    urls.current = [];
  };
  useEffect(() => revokeAll, []);

  const track = (u) => { urls.current.push(u); return u; };

  /** Runs the model. Resolves to the result, or throws an ApiError. */
  const analyzeImage = async (photo, point, locationSource) => {
    setBusy(true);
    setError(null);
    try {
      const data = await callAnalyze({
        file: photo, latitude: point.lat, longitude: point.lng, locationSource,
      });
      revokeAll();
      const annotatedUrl = data.annotated_image
        ? track(URL.createObjectURL(b64ToBlob(data.annotated_image.data, data.annotated_image.mime_type)))
        : null;
      const pdfBlob = data.report ? b64ToBlob(data.report.data, data.report.mime_type) : null;
      const photoUrl = track(URL.createObjectURL(photo));
      const next = { ...data, annotatedUrl, photoUrl, pdfBlob, pdfFilename: data.report?.filename };
      setFile(photo);
      setGps(point);
      setResult(next);
      setSaved(null);
      return next;
    } catch (e) {
      setError(e);
      throw e;
    } finally {
      setBusy(false);
    }
  };

  const clearDetection = () => {
    revokeAll();
    setFile(null);
    setGps(null);
    setResult(null);
    setSaved(null);
    setError(null);
  };

  return (
    <DetectionContext.Provider
      value={{ file, gps, result, busy, error, saved, setSaved, analyzeImage, clearDetection }}
    >
      {children}
    </DetectionContext.Provider>
  );
}

export function useDetection() {
  const ctx = useContext(DetectionContext);
  if (!ctx) throw new Error("useDetection must be used within DetectionProvider");
  return ctx;
}
