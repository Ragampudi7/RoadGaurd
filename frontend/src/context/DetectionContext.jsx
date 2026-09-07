import { createContext, useContext, useState } from "react";
import { mockDetectionResult } from "../lib/mockData";
import { analyze as callApi, USE_MOCK as API_USE_MOCK } from "../lib/api";

/**
 * Detection state.
 *
 * `USE_MOCK` is the single seam between demo data and the real model. Flip it
 * to false (or set VITE_USE_MOCK=false) and every screen keeps working, because
 * mockDetectionResult is shaped exactly like the real AnalyzeResponse.
 */
export const USE_MOCK = API_USE_MOCK;

const DetectionCtx = createContext(null);

export function DetectionProvider({ children }) {
  const [imageUrl, setImageUrl] = useState(null);
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  function setImage(f) {
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setFile(f);
    setImageUrl(f ? URL.createObjectURL(f) : null);
    setResult(null);
    setError(null);
  }

  async function runDetection({ latitude, longitude }) {
    setBusy(true);
    setError(null);
    try {
      if (USE_MOCK) {
        // Simulated latency so the loading state is exercised, not skipped.
        await new Promise((r) => setTimeout(r, 1400));
        setResult({
          ...mockDetectionResult,
          location: {
            latitude: Number(latitude),
            longitude: Number(longitude),
            maps_url: `https://maps.google.com/?q=${latitude},${longitude}`,
          },
          analysed_at: new Date().toISOString(),
        });
      } else {
        const data = await callApi({ file, latitude, longitude });
        setResult({ ...data, is_demo: false });
      }
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  function clear() {
    if (imageUrl) URL.revokeObjectURL(imageUrl);
    setImageUrl(null);
    setFile(null);
    setResult(null);
    setError(null);
  }

  return (
    <DetectionCtx.Provider
      value={{ imageUrl, file, result, busy, error, setImage, runDetection, clear, isMock: USE_MOCK }}>
      {children}
    </DetectionCtx.Provider>
  );
}

export const useDetection = () => useContext(DetectionCtx);
