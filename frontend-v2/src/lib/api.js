/**
 * Client for the RoadGuard FastAPI backend.
 *
 * One build-time switch, read by Vite:
 *   VITE_API_BASE   where the backend lives (default http://localhost:8000)
 *
 * Nothing is stored in the browser except the session token. Reports, scores
 * and PDFs all come from the server.
 */

// Render's blueprint supplies a bare hostname with no scheme; fetch() cannot
// use that, so add one rather than relying on someone typing https://.
const RAW_BASE = (import.meta.env.VITE_API_BASE || "http://localhost:8000")
  .trim()
  .replace(/\/+$/, "");

// Render's `host` property is the short private-network service name
// ("roadguard-api-f019"), which a browser cannot resolve; the public address
// is the same name under onrender.com.
const WITH_DOMAIN = /^https?:\/\//i.test(RAW_BASE) || /^[^/:]+\./.test(RAW_BASE) || /^localhost(:|$)/i.test(RAW_BASE)
  ? RAW_BASE
  : RAW_BASE.replace(/^([^/:]+)/, "$1.onrender.com");

export const API_BASE = /^https?:\/\//i.test(WITH_DOMAIN) ? WITH_DOMAIN : `https://${WITH_DOMAIN}`;

const TOKEN_KEY = "roadguard_token";

/* ------------------------------------------------------------------ token -- */
export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(t) {
  try {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  } catch { /* private mode */ }
}

/* ------------------------------------------------------------------- core -- */
export class ApiError extends Error {
  constructor(message, { code, status } = {}) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(path, { method = "GET", body, form, auth = true, signal } = {}) {
  const headers = {};
  if (auth) {
    const t = getToken();
    if (t) headers.Authorization = `Bearer ${t}`;
  }
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
      signal,
    });
  } catch (e) {
    if (e.name === "AbortError") throw e;
    // fetch only rejects on a network or CORS failure.
    throw new ApiError(
      `Cannot reach the API at ${API_BASE}. Check the backend is running and that this site's address is in its CORS allow-list.`,
      { code: "network_error" }
    );
  }

  if (res.status === 204) return null;

  let payload = null;
  try { payload = await res.json(); } catch { /* empty or non-JSON body */ }

  if (!res.ok || payload?.success === false) {
    const err = payload?.error ?? {};
    // A 401 means the stored token is dead; drop it so the UI signs out
    // instead of retrying forever with a bad credential.
    if (res.status === 401) {
      setToken(null);
      window.dispatchEvent(new Event("roadguard:signed-out"));
    }
    throw new ApiError(err.message || `Request failed (${res.status}).`,
                       { code: err.code, status: res.status });
  }
  return payload;
}

/* ------------------------------------------------------------------- auth -- */
export const auth = {
  signup: (b) => request("/auth/signup", { method: "POST", body: b, auth: false }),
  login: (b) => request("/auth/login", { method: "POST", body: b, auth: false }),
  me: () => request("/auth/me"),
  updateMe: (b) => request("/auth/me", { method: "PATCH", body: b }),
};

/* ---------------------------------------------------------------- reports -- */
async function authedBlob(path, what) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      headers: { Authorization: `Bearer ${getToken()}` },
    });
  } catch {
    throw new ApiError(`Cannot reach the API at ${API_BASE}.`, { code: "network_error" });
  }
  if (!res.ok) {
    let message = `Could not load the ${what} (${res.status}).`;
    try { message = (await res.json())?.error?.message || message; } catch { /* not JSON */ }
    throw new ApiError(message, { status: res.status });
  }
  return res.blob();
}

export const reports = {
  list: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
    );
    return request(`/reports${qs.toString() ? `?${qs}` : ""}`);
  },
  get: (id) => request(`/reports/${id}`),
  create: (b) => request("/reports", { method: "POST", body: b }),
  setStatus: (id, status) => request(`/reports/${id}/status`, { method: "PATCH", body: { status } }),
  remove: (id) => request(`/reports/${id}`, { method: "DELETE" }),
  stats: (params = {}) => {
    const qs = new URLSearchParams(params);
    return request(`/reports/stats${qs.toString() ? `?${qs}` : ""}`);
  },
  /** Both need the Authorization header, so neither can be a plain <a href>/<img src>. */
  pdf: (id) => authedBlob(`/reports/${id}/pdf`, "report"),
  image: (id) => authedBlob(`/reports/${id}/image`, "photograph"),
};

/* ---------------------------------------------------------------- analyse -- */
export async function analyze({ file, latitude, longitude, locationSource, includeImage = true, includePdf = true, signal }) {
  const form = new FormData();
  form.append("image", file);
  form.append("latitude", String(latitude));
  form.append("longitude", String(longitude));
  // photo | device | map. The server re-checks "photo" against the image.
  if (locationSource) form.append("location_source", locationSource);
  const qs = new URLSearchParams({
    include_image: String(includeImage),
    include_pdf: String(includePdf),
  });
  return request(`/analyze?${qs}`, { method: "POST", form, signal });
}

export const getHealth = () => request("/health", { auth: false });

/**
 * Place name for a point, looked up by the backend from OpenStreetMap (cached
 * and rate-limited there). `label` is null when no name is available.
 */
export const reverseGeocode = (lat, lng, { signal } = {}) =>
  request(`/geocode/reverse?latitude=${lat.toFixed(6)}&longitude=${lng.toFixed(6)}`, { auth: false, signal });

/* ---------------------------------------------------------------- helpers -- */
/** base64 payload -> Blob. The API returns media inside JSON this way. */
export function b64ToBlob(b64, mime) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Blob([bytes], { type: mime });
}

/** Save a blob under `filename`, then release the object URL. */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Revoking immediately can cancel the download in some browsers.
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** File -> bare base64 (no data: prefix), which is what POST /reports accepts. */
export function fileToBase64(f) {
  return new Promise((resolve, reject) => {
    const r = new FileReader();
    r.onload = () => resolve(String(r.result).split(",", 2)[1]);
    r.onerror = () => reject(r.error);
    r.readAsDataURL(f);
  });
}
