# RoadGuard AI — frontend

React + Vite SPA for the Automated Road Health Assessment backend.
Glass UI over real road photographs, Tailwind v4, Framer Motion, Leaflet, Recharts.

## Run

```bash
npm install
cp .env.example .env
npm run dev            # http://localhost:5173
```

## Demo mode — read this before showing anyone

`VITE_USE_MOCK=true` (the default) makes `DetectionContext` return fixed sample
data from `src/lib/mockData.js` instead of calling the model. **Every score you
see in that mode is fabricated.** The UI marks it — a "Demo data" badge in the
header, on the dashboard and on the result, a striped banner on the result page,
and a warning block printed at the top of the exported PDF.

That marking is not decoration. This app produces a grievance document addressed
to a municipal body; an invented report that looked official would be a real
problem. Do not remove the badges while mock mode is on.

To use the real model:

```bash
VITE_USE_MOCK=false
VITE_API_BASE=http://localhost:8000
```

`mockDetectionResult` is shaped field-for-field like the backend's
`AnalyzeResponse`, so nothing else changes — the swap is one flag.

## Auth is not auth

`AuthContext` is a localStorage key. No password is checked, nothing reaches a
server, and anyone can forge a session from devtools. It gates navigation so the
app shell can be built; it protects nothing. Real accounts need the database.

Same for reports: `ReportsContext` persists to `localStorage`, so reports filed
on a phone will not appear on a laptop and clearing site data loses them.

## Structure

```
src/
├── context/     Auth · Detection · Reports  (all localStorage-backed)
├── lib/         api.js (real client) · mockData.js · reportPdf.js
├── components/  ProtectedRoute · DashboardLayout · Navbar · AuthLayout
│                Results (gauge, risk panel, table) · Reveal · DemoBadge
│                landing/  Hero · Features · HowItWorks · Stats · CTA · Footer
└── pages/       Landing · Login · Signup
    └── app/     Dashboard · Upload · DetectionResult · Reports · MapView · Profile
```

`Dashboard` and `MapView` are lazy-loaded — Recharts and Leaflet are the two
heaviest dependencies and neither is needed to render the landing page. Initial
bundle is ~131 kB gzipped.

## CORS

The backend allow-list covers ports 3000 and 5173. `npm run dev` works; `npm run
preview` defaults to 4173 and will fail with "Failed to fetch" — run
`npm run preview -- --port 5173` or add the port to `EXTRA_CORS_ORIGINS`.

## Colour

`src/index.css` carries the condition and risk colours from the backend's
`app/config.py`, so the UI, the annotated image and the PDF share one palette.

The dashboard's two-line chart pair (`#4a9eff` / `#f2a03d`) was checked for
colour-vision separation: ΔE 32 normal, 27 under CVD. The Good/Fair/Poor/
Dangerous ramp does **not** pass that bar — adjacent steps sit ~10 ΔE apart —
which is why every chart using it also prints the band name and the count. Never
let those four carry meaning by colour alone.

## Images

Road photographs in `public/img/` come from the training datasets, used at native
resolution (640 px — do not upscale, they go soft). Sources are the
[Pothole](https://universe.roboflow.com/siva-ragampudi/pothole-vhmow-jwwzq) and
[Road](https://universe.roboflow.com/siva-ragampudi/road-c013o-tlkm7) datasets on
Roboflow Universe, CC BY 4.0 — attribution is in the site footer.
