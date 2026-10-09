import { useEffect, useState } from "react";
import { reverseGeocode } from "./api";

/**
 * The place name for a point, from the backend's OpenStreetMap lookup.
 * Returns { label, loading }. label stays null when the lookup fails or the
 * point has no name: callers then show coordinates, never a guessed area.
 * Waits briefly after the point changes so dragging/tapping around the map
 * does not fire a lookup per tap.
 */
export function usePlaceName(point) {
  const [state, setState] = useState({ label: null, loading: false });
  const lat = point?.lat;
  const lng = point?.lng;

  useEffect(() => {
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      setState({ label: null, loading: false });
      return undefined;
    }
    const controller = new AbortController();
    setState({ label: null, loading: true });
    const timer = setTimeout(() => {
      reverseGeocode(lat, lng, { signal: controller.signal })
        .then((r) => setState({ label: r?.label ?? null, loading: false }))
        .catch((e) => {
          if (e.name !== "AbortError") setState({ label: null, loading: false });
        });
    }, 400);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [lat, lng]);

  return state;
}
