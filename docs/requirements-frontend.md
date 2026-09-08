# What we need from you — the frontend

You are building a client for an existing JSON API. The backend does not
change, so you can use anything: React, Vue, Angular, Flutter, plain HTML.
Full API detail is in [`INTEGRATION.md`](../INTEGRATION.md).

---

## Start here, before writing any code

```
http://localhost:8000/docs
```

Interactive documentation, generated from the code, always current. The
machine-readable schema is at `/openapi.json` — most languages will generate a
typed client from it in one command, which beats hand-writing request code.

---

## Deliver these six things

### 1. The code

A repository, a branch, or a folder we can run. Include a lockfile
(`package-lock.json` / `yarn.lock`) so `npm ci` reproduces your build exactly.

### 2. Run instructions that work from a clean clone

```bash
npm ci
cp .env.example .env
npm run dev
```

Three commands or fewer. If it needs a specific Node version, say which.

### 3. Every origin your app runs on

Development and deployed, e.g.:

```
http://localhost:3000
https://your-app.vercel.app
```

We add these to the API's CORS allow-list. **Until we do, every request from
your app fails** with "Failed to fetch" and no status code — so send these
early rather than debugging a network error that is really a config gap.

### 4. Which endpoints you use

If you only call `/analyze`, you need no accounts, no database and no auth —
worth confirming before anyone builds a login screen that is not required.

### 5. Confirmation you render the API's PDF

`/analyze` returns a complete report in `r.report.data` — base64, decode to a
Blob. It has the score gauge, the weighted risk components, the geospatial and
jurisdiction panels, the per-defect inventory and the annotated evidence
pages.

**Do not generate your own PDF from the JSON.** Our own frontend printed the
screen instead for a while and shipped a document with none of the analysis in
it. Same for `r.annotated_image.data` — the boxes are already drawn.

### 6. How demo data is marked, if you have a demo mode

See the obligation below.

---

## Two things that will cost you an afternoon each

**Build-time config.** Vite, Next and CRA compile the API base URL into the
bundle at **build** time. Changing it needs a rebuild, not a restart — and a
deployment built against `localhost:8000` fails with no error anywhere,
because nothing failed. It just built against the wrong value.

**The upload endpoint is multipart, not JSON.**

```
POST /analyze?include_image=true&include_pdf=true
image=<file>  latitude=17.4948  longitude=78.3996
```

Coordinates are required and validated. The image must be ≤ 10 MB and JPEG,
PNG, WEBP or BMP — the content type, the extension *and* the decoded format
are all checked, so renaming a `.gif` will not get through. Inference takes
2–10 seconds on CPU: show a spinner and disable the button, or a double click
runs it twice.

---

## Two rules the server enforces, whatever your UI does

**Only an `official` account may acknowledge or resolve a report.** A citizen
gets a 403. Hide the buttons by all means, but the guard is server-side — a UI
that assumes otherwise will show an action that always fails.

**A draft is private.** Officials never see one, and reading another user's
report by id returns **404, not 403** — deliberately, so the response does not
confirm the id exists. Do not treat that 404 as a bug.

---

## One requirement that is not a preference

If you ship a demo or offline mode with placeholder numbers, **it must be
marked on every screen that shows a figure, and in any exported document.**

This app produces a complaint addressed to the Greater Hyderabad Municipal
Corporation. A fabricated report that looks official is the one outcome this
project must not produce, and no amount of visual polish compensates for it.

For reference, ours marks it in four places: a badge in the header, on the
dashboard, on the result page, and a warning block printed at the top of the
exported PDF.

---

## How we will check it

From a clean clone: `npm ci && npm run build`, then click through:

| | |
|---|---|
| Sign up, then **refresh the page** | Still signed in |
| Upload a road photo, analyse | Real boxes and a real score, no demo badge |
| File the report, then **hard-refresh** | Still in the list — that is the database, not the browser |
| Export the PDF | 4+ pages with the risk assessment and defect inventory, **not** a print-out of the screen |
| Sign in on a second device or private window | The same reports are there |
| As a citizen, look for Acknowledge / Resolve | Absent — and refused by the server if forced |

The PDF check is the one that catches the most common mistake, so it is worth
running yourself before you hand anything over.

---

## Quick sanity check from your machine

```bash
curl -s http://localhost:8000/health

curl -s -X POST "http://localhost:8000/analyze?include_pdf=false&include_image=false" \
  -F "image=@road.jpg" -F "latitude=17.4948" -F "longitude=78.3996"
```

If both work, the API is fine and anything still broken is in the client.
