/**
 * Client for the Road Health API.
 *
 * Two switches, both read at build time by Vite:
 *   VITE_API_BASE   where the backend lives
 *   VITE_USE_MOCK   "true" keeps the app on fixed sample data (see mockData.js)
 *
 * When mock mode is off, every context in this app talks to the real backend
 * and nothing is stored in the browser except the session token.
 */

// Render's blueprint supplies this from the API service's `host` property,
// which is a bare hostname with no scheme. fetch() cannot use that, so add one
// rather than making the deploy depend on somebody remembering to type https://.
const RAW_BASE = (import.meta.env.VITE_API_BASE || "http://localhost:8000")
  .trim()
  .replace(/\/+$/, "");

export const API_BASE = /^https?:\/\//i.test(RAW_BASE) ? RAW_BASE : `https://${RAW_BASE}`;

export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== "false";

const TOKEN_KEY = "roadguard_token";

/* ------------------------------------------------------------------ token --
   Kept in localStorage so a refresh does not sign the user out. That is the
   usual XSS tradeoff: any script running on this origin can read it. Acceptable
   for this app, and the reason the backend keeps token lifetime short. */
export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
}
export function setToken(t) {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY); } catch { /* private mode */ }
}

/* ------------------------------------------------------------------ core -- */
class ApiError extends Error {
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
    // fetch only rejects on network/CORS failure, which is by far the most
    // common problem in practice and deserves a message that says so.
    throw new ApiError(
      `Cannot reach the API at ${API_BASE}. Check the backend is running and that this origin is in its CORS allow-list.`,
      { code: "network_error" }
    );
  }

  if (res.status === 204) return null;

  let payload = null;
  try { payload = await res.json(); } catch { /* empty or non-JSON body */ }

  if (!res.ok || payload?.success === false) {
    const err = payload?.error ?? {};
    // A 401 means the stored token is dead; drop it so the UI can show the
    // signed-out state instead of retrying forever with a bad credential.
    if (res.status === 401) setToken(null);
    throw new ApiError(err.message || `Request failed (${res.status}).`,
                       { code: err.code, status: res.status });
  }
  return payload;
}

/* ------------------------------------------------------------------ auth -- */
export const auth = {
  signup: (b) => request("/auth/signup", { method: "POST", body: b, auth: false }),
  login: (b) => request("/auth/login", { method: "POST", body: b, auth: false }),
  me: () => request("/auth/me"),
  updateMe: (b) => request("/auth/me", { method: "PATCH", body: b }),
};

/* --------------------------------------------------------------- reports -- */
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
  imageUrl: (id) => `${API_BASE}/reports/${id}/image`,
};

/* --------------------------------------------------------------- analyse -- */
export async function analyze({ file, latitude, longitude, includeImage = true, includePdf = true, signal }) {
  const form = new FormData();
  form.append("image", file);
  form.append("latitude", String(latitude));
  form.append("longitude", String(longitude));
  const qs = new URLSearchParams({
    include_image: String(includeImage),
    include_pdf: String(includePdf),
  });
  return request(`/analyze?${qs}`, { method: "POST", form, signal });
}

export const getHealth = () => request("/health", { auth: false });

/** base64 payload -> blob URL for <img src> or a download link. */
export function b64ToUrl(b64, mime) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mime }));
}

export { ApiError };
