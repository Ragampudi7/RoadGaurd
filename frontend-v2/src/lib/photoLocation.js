/**
 * Where a complaint photo was taken.
 *
 * Order of trust:
 *   1. "photo"  - the GPS the camera saved inside the image (EXIF). For a
 *                 gallery upload this is the pothole, not wherever the
 *                 citizen is uploading from. The server re-reads it and
 *                 refuses the claim if the photo disagrees.
 *   2. "device" - the phone's live GPS, but ONLY for a photo just taken with
 *                 the camera, when the citizen is standing at the pothole.
 *   3. "map"    - the citizen taps the spot. Required whenever 1 and 2 are
 *                 unavailable; the app never guesses a location silently.
 */
import exifr from "exifr";

/** GPS saved in the photo, or null. Never throws. */
export async function readPhotoLocation(file) {
  try {
    const gps = await exifr.gps(file);
    const lat = gps?.latitude;
    const lng = gps?.longitude;
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
    if (lat === 0 && lng === 0) return null; // "no fix" placeholder some cameras write
    return { lat, lng };
  } catch {
    return null; // unreadable metadata is the same as none
  }
}

/** The device's current position, or null if denied/unavailable/slow. */
export function getDeviceLocation({ timeout = 10000 } = {}) {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      () => resolve(null),
      { enableHighAccuracy: true, timeout, maximumAge: 30000 }
    );
  });
}
