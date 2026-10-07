# RoadGuard AI — frontend v2

The new RoadGuard UI (React 18 + Vite + Tailwind 3 + Leaflet), wired to the
FastAPI backend in `../backend`. Every figure on every screen comes from the
backend: there is no demo or mock data in this app.

## Run it locally

```bash
# 1. backend (in another terminal)
cd ../backend
uvicorn app.main:app --reload            # http://localhost:8000

# 2. this app
cd frontend-v2
cp .env.example .env.local               # only needed if the API is not on :8000
npm install
npm run dev                              # http://localhost:5173
```

`localhost:5173` and `localhost:3000` are already in the backend's CORS
allow-list. For any other origin add it to `EXTRA_CORS_ORIGINS` in
`backend/.env`.

`VITE_API_BASE` is compiled in at build time — after changing it, rebuild
(`npm run build`); a restart is not enough.

## What talks to what

| Screen | Backend calls |
|---|---|
| Sign up / Sign in | `POST /auth/signup`, `POST /auth/login`, `GET /auth/me` |
| Upload → Analyze Now | `POST /analyze` (multipart: photo + latitude + longitude) |
| Upload → Save as Draft | `POST /analyze`, then `POST /reports` with `submit: false` |
| Detection Result | Annotated image and PDF come from the `/analyze` response (base64); Save/Submit → `POST /reports`, `PATCH /reports/{id}/status` |
| Reports | `GET /reports`; PDF → `GET /reports/{id}/pdf` (rebuilt by the server); submit / withdraw → `PATCH …/status`; delete draft → `DELETE /reports/{id}` |
| Dashboard | `GET /reports/stats` (computed by Postgres over every row) |
| Map View | Citizen: own reports. Official: `GET /reports?mine=false` |
| Grievance Queue (officials only) | `GET /reports?mine=false&status=…`, `PATCH …/status` |
| Profile | `PATCH /auth/me` (name, city) |

The client lives in `src/lib/api.js`; the translation from backend fields to
what the screens show is in one place, `src/lib/present.js`.

## Behaviour worth knowing

- **Officials** are whoever is listed in `OFFICIAL_EMAILS` in `backend/.env`.
  They get an extra *Grievance Queue* page. The server enforces the role; the
  hidden nav item is only convenience.
- **Location.** The device GPS is used when it is inside Telangana. If it is
  unavailable or outside, the pin falls back to Hyderabad city centre and the
  page says so. Tapping the map moves the pin.
- **PDFs** are always the backend's report, never a print of the screen. A
  report stored without a photograph cannot be rebuilt, so its download button
  is disabled.
- Labels (risk *Low / Moderate / High / Critical*, condition, priority tier,
  status) are the backend's own words, so the screen matches the PDF.

## Deploying

Same pattern as `../frontend`: build with `VITE_API_BASE` set to the deployed
API, serve `dist/` as a single-page app (all paths → `index.html`). To make
this the deployed frontend, point `rootDir` in `render.yaml` (or `base` /
`publish` in `netlify.toml`) at `frontend-v2` instead of `frontend`.
