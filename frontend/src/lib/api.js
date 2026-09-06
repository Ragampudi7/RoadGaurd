/**
 * Thin client for the Road Health API.
 *
 * The base URL comes from VITE_API_BASE at build time so the same source
 * deploys against localhost and against Render without edits.
 */

export const API_BASE = (
  import.meta.env.VITE_API_BASE || "http://localhost:8000"
).replace(/\/+$/, "");

/**
 * The backend returns errors as {success:false, error:{code, message}}.
 * Surface that message rather than a bare HTTP status, since the codes are
 * meaningful (unsupported_media_type, image_too_large, model_unavailable...).
 */
async function unwrap(res) {
  let body = null;
  try {
    body = await res.json();
  } catch {
    throw new Error(`Server returned ${res.status} with a non-JSON body.`);
  }
  if (!res.ok || body?.success === false) {
    const err = body?.error ?? {};
    const e = new Error(err.message || `Request failed (${res.status}).`);
    e.code = err.code;
    e.status = res.status;
    throw e;
  }
  return body;
}

export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  return unwrap(res);
}

/**
 * POST /analyze — multipart image + coordinates.
 * includeImage / includePdf map to the query flags that let the caller skip
 * the expensive base64 payloads for a fast preview.
 */
export async function analyze({ file, latitude, longitude, includeImage = true, includePdf = true, signal }) {
  const form = new FormData();
  form.append("image", file);
  form.append("latitude", String(latitude));
  form.append("longitude", String(longitude));

  const qs = new URLSearchParams({
    include_image: String(includeImage),
    include_pdf: String(includePdf),
  });

  const res = await fetch(`${API_BASE}/analyze?${qs}`, {
    method: "POST",
    body: form,
    signal,
  });
  return unwrap(res);
}

/** Turn a base64 payload from the API into a blob URL for <img> or download. */
export function b64ToUrl(b64, mime) {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return URL.createObjectURL(new Blob([bytes], { type: mime }));
}

export const CONDITION_COLOUR = {
  Good: "var(--good)",
  Fair: "var(--fair)",
  Poor: "var(--poor)",
  Dangerous: "var(--danger)",
};

export const RISK_COLOUR = {
  Critical: "var(--critical)",
  High: "var(--high)",
  Moderate: "var(--moderate)",
  Low: "var(--low)",
};

export const SEVERITY_COLOUR = {
  Critical: "var(--critical)",
  High: "var(--high)",
  Medium: "var(--moderate)",
  Minor: "var(--minor)",
};
