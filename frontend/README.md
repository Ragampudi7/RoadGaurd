# Road Health — frontend

React + Vite single-page app for the Automated Road Health Assessment backend.

## Run locally

```bash
npm install
cp .env.example .env        # point VITE_API_BASE at your backend
npm run dev                 # http://localhost:5173
```

`VITE_API_BASE` is read at **build time**, not runtime — Vite inlines it into the
bundle. Changing it means rebuilding, which matters for the Render deploy.

## CORS

The backend only accepts browser requests from origins in its allow-list
(`FRONTEND_URL` plus `EXTRA_CORS_ORIGINS`). Its defaults cover ports 3000 and
5173, so `npm run dev` works out of the box but `vite preview` on its default
port 4173 does **not** — run `npm run preview -- --port 5173`, or add the port to
`EXTRA_CORS_ORIGINS` on the backend.

## Screens

| Route | Status |
|---|---|
| `/` Analyse | working — upload, geolocation, score, risk, annotated image, crops, PDF |
| `/history` | stub — needs `GET /reports` |
| `/map` | stub — needs `GET /reports`; Leaflet installed |
| `/admin` | stub — needs `PATCH /reports/{id}/status`; needs an auth decision first |
| `/analytics` | stub — needs `GET /reports/stats`; Recharts installed |

The four stubs are deliberately not populated with mock data: a History page full
of invented rows looks finished and hides the fact that nothing is persisted yet.

## Design tokens

`src/theme.css` carries the condition and risk colours from the backend's
`app/config.py`, so the UI, the annotated image and the PDF report use one
palette. Change them in both places or not at all.
