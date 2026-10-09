# Deploying RoadGuard AI

Two services from one repository: the FastAPI backend and the static frontend.
Each has its own `Dockerfile`, so the build is identical wherever it runs and
nothing depends on a platform's language auto-detection guessing right.

**The live deployment runs on Render**, from the `render.yaml` blueprint in the
repository root (API: `roadguard-api`, UI: `roadguard-ui`, built from
`frontend-v2/`). Render → New → Blueprint → this repository, then enter
`DATABASE_URL`, `JWT_SECRET` and `OFFICIAL_EMAILS` when prompted. The step-by-
step sections below were written for **Railway** and still work there as an
alternative.

---

## Before you start

Have these three to hand:

| | |
|---|---|
| `DATABASE_URL` | your Aiven connection string |
| `JWT_SECRET` | generate a fresh one: `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `OFFICIAL_EMAILS` | who may acknowledge and resolve complaints — a second email of your own, or a domain suffix like `@ghmc.gov.in` |

Do not reuse your local `JWT_SECRET`. It signs session tokens, and a key that
has been on a laptop and in a `.env` file is not one you want signing them in
production.

---

## 1. The API

**railway.app** → **New Project** → **Deploy from GitHub repo** → pick the
repository.

Then, in the service's **Settings**:

- **Root Directory:** `backend`
- **Service Name:** `roadguard-api`

Railway finds `backend/Dockerfile` and uses it — the build log will say so.
Leave the build and start commands empty; the Dockerfile carries both.

In **Variables**, add:

```
DATABASE_URL      = <your Aiven string>
JWT_SECRET        = <the one you just generated>
OFFICIAL_EMAILS   = <your second email, or @yourdomain>
ENVIRONMENT       = production
```

Everything else the service needs — model path, thresholds, thread pinning —
is baked into the Dockerfile.

Then **Settings → Networking → Generate Domain**. That gives the API a public
hostname, which the frontend needs in the next step.

The first build takes roughly 5–10 minutes, nearly all of it PyTorch. Later
deploys that do not touch `requirements.txt` reuse that layer and take under a
minute.

**Check it:**

```
https://<your-api-domain>/health
```

You want `"model_loaded": true` and `"status": "trained"`. If it says
`pretrained_fallback`, `weights/best.pt` did not make it into the image and
the detections would not be road defects.

---

## 2. The UI

In the same project: **New** → **GitHub Repo** → the same repository again.

**Settings**:

- **Root Directory:** `frontend`
- **Service Name:** `roadguard-ui`

**Variables**:

```
VITE_API_BASE   = ${{roadguard-api.RAILWAY_PUBLIC_DOMAIN}}
VITE_USE_MOCK   = false
```

That `${{...}}` is Railway's reference syntax — it resolves to the API
service's hostname, so you never paste a URL twice or update one after a
redeploy.

**This one has a trap worth understanding.** Vite substitutes those two values
into the JavaScript *at build time*, and Railway only passes a variable into a
Docker build if the Dockerfile declares it with `ARG` — which
`frontend/Dockerfile` does, for exactly this reason. If you rename either
variable, rename the matching `ARG` too, or the build will quietly succeed
pointing at `http://localhost:8000` and the deployed site will fail to reach
its own API with nothing in any log to explain why.

The reference variable resolves to a bare hostname with no `https://`.
`src/lib/api.js` adds the scheme when it is missing, so this works as written.

Then **Generate Domain** for this service too.

---

## 3. Close the CORS loop

Go back to **roadguard-api → Variables** and add:

```
FRONTEND_URL = ${{roadguard-ui.RAILWAY_PUBLIC_DOMAIN}}
```

The API refuses browser requests from origins it does not know. Until this is
set, the UI loads perfectly and every API call fails — which looks like a
broken backend and is not one.

`app/config.py` adds the scheme to this bare hostname the same way the
frontend does.

The API redeploys automatically. When it comes back, open the UI's domain and
sign up.

---

## Deploy order, and why it is this one

1. API first — the UI's build needs its hostname.
2. UI second.
3. `FRONTEND_URL` last — it needs the UI's hostname, and the UI did not have
   one until step 2.

Setting them in a different order is not fatal; it just means an extra
redeploy.

---

## What "working" looks like

- `GET /health` → `"status": "ok"`, `"model_loaded": true`. For the first
  minute after a (re)start it says `"status": "starting"`, `"model_loading":
  true` - the API already serves logins and reports then; only `/analyze`
  waits for the model.
- Sign up, upload a road photograph, and the analysis returns real detections.
- File the report, then reload the page — it is still there. That is the
  database.
- Sign in on a phone: the same reports. That is the database again, and it is
  the thing localStorage could never do.

---

## Keeping the free API awake (demo day)

Render's free plan puts the API to sleep after 15 minutes without a request.
The next visitor then waits while it starts again - the UI says "The server
is waking up" instead of looking frozen, and opening any page of the site
pings the API so it is usually awake by the time someone has typed their
password. The AI model loads in the background after start-up, so login does
not wait for it; only the first photo analysis does.

For a presentation, keep it awake instead:

1. Sign up at **uptimerobot.com** (free).
2. **Add New Monitor** → type **HTTP(s)**.
3. URL: `https://roadguard-api-f019.onrender.com/health`
4. Monitoring interval: **5 minutes**. Save.

A ping every 5 minutes means the API never idles for 15. Render's free plan
includes 750 instance hours a month, enough for this one service to run
around the clock. Pause the monitor afterwards if you prefer it to sleep.

The UI (`roadguard-ui`) is a static site: it uses no instance hours, and only
the API needs waking. (Source: https://render.com/docs/free)

---

## Troubleshooting

**`Failed to fetch` / CORS errors in the browser console.** `FRONTEND_URL` is
missing or does not match the UI's domain. Check the API's start-up log — it
prints the full allow-list on every boot.

**UI shows demo data.** `VITE_USE_MOCK` was not `false` at build time. Set it
and **redeploy** — a restart is not enough, because the value is compiled into
the bundle.

**`"status": "pretrained_fallback"` in `/health`.** `weights/best.pt` is not in
the image. Confirm it is committed (`git ls-files backend/weights`) — it is
5.3 MB and `backend/.gitignore` re-includes it explicitly with a `!` line.

**Build runs out of memory or time.** Nearly always torch. Confirm the build
log shows it installing from `download.pytorch.org/whl/cpu` and not from
PyPI — the CUDA wheels are roughly ten times the size and this service cannot
use them.

**First request after a quiet period takes ~30 seconds.** The container spun
down and is reloading PyTorch. Hit `/health` a minute before you demo it.

**Service builds, then the domain returns 502 or "Application failed to
respond".** The platform could not work out which port the process is
listening on. Both Dockerfiles read `$PORT` and fall back to a fixed port if
it is unset, so the fix is to set `PORT` explicitly in the service's
variables — `8000` for the API, `3000` for the UI — and redeploy.

**A variable change did nothing.** Runtime variables (`DATABASE_URL`,
`JWT_SECRET`, `FRONTEND_URL`, `OFFICIAL_EMAILS`) take effect on restart. Build
variables (`VITE_API_BASE`, `VITE_USE_MOCK`) require a full rebuild, because
they are compiled into the bundle. If in doubt, redeploy rather than restart.
