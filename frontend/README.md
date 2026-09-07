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

Both are read by Vite at **build** time, not at runtime. Changing either on a
deployed site needs a rebuild, not a restart.

## Two modes, and the difference is not cosmetic

`VITE_USE_MOCK` picks which one runs, and every screen's copy follows it. Get
this wrong and the app tells the user something untrue about their own data,
which is why the contexts branch on it rather than the screens.

**Mock (`true`).** `AuthContext` is a localStorage key: no password is checked,
nothing reaches a server, and anyone can forge a session from devtools. It gates
navigation so the shell can be built; it protects nothing. `ReportsContext`
persists to `localStorage`, so reports filed on a phone never appear on a laptop
and clearing site data loses them. The auth and profile screens say so.

**Real (`false`).** Real accounts - bcrypt-hashed passwords, a signed token, and
reports owned by the account that filed them and reachable from any device.
A refresh resumes the session by calling `/auth/me` rather than trusting a
cached profile the token may no longer match. The "stays in this browser"
notices come out, because they are no longer true.

Screens do not branch on the mode; the contexts normalise the server's rows into
the same flat shape the mock data already used. Only the copy differs.

## Roles

An account is a citizen or an official, decided by the **server** from its
`OFFICIAL_EMAILS` allow-list. The client only ever reads `user.role` out of the
profile the server sent.

An official gets `/app/queue`: filed complaints, worst first, with Acknowledge,
Mark resolved and Reopen. A citizen navigating there is redirected. That guard
is navigation, not security - the server re-checks the role on every request, so
bypassing it gets an empty screen and a 403, never data.

Drafts never reach the queue. An unsent working copy is not a complaint.

## Structure

```
src/
├── context/     Auth · Detection · Reports  (server-backed, or localStorage in mock mode)
├── lib/         api.js (real client) · mockData.js · reportPdf.js
├── components/  ProtectedRoute · DashboardLayout · Navbar · AuthLayout
│                Results (gauge, risk panel, table) · Reveal · DemoBadge
│                landing/  Hero · Features · HowItWorks · Stats · CTA · Footer
└── pages/       Landing · Login · Signup
    └── app/     Dashboard · Upload · DetectionResult · Reports · MapView · Profile
                  Queue  (officials only)
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

## Getting a filed report back

The complaint PDF is not stored. `GET /reports/{id}/pdf` rebuilds it from the
row and the photograph, so the **PDF** button on a report card is a request that
can fail and can take a moment — not an instant link. It cannot be a plain
`<a href>` either: the endpoint needs the `Authorization` header and a browser
sends none on a navigation, so `api.pdf()` fetches the blob and hands it to a
temporary object URL.

The rebuilt document is stamped as a regenerated copy, with the date and the
weights version the figures were filed under.
