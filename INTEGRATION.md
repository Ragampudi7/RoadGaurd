# Integrating another model or another frontend

Two independent contracts. Someone replacing the model touches nothing in the
frontend; someone building a new frontend touches nothing in the model. Both
plug into the same backend, and neither needs to modify it.

Read the half you need. What each side must hand over is listed at the end of
its section, and it is short.

---

# Part 1 — Bringing your own model

## What the backend loads

`app/services/detection_service.py` does this and nothing more:

```python
model = YOLO(weights_path)          # ultralytics
result = model.predict(image, imgsz=..., conf=..., iou=..., max_det=...)
for box in result.boxes:
    x1, y1, x2, y2 = box.xyxy[0]
    class_id, confidence = int(box.cls[0]), float(box.conf[0])
    class_name = model.names[class_id]
```

So the requirement is precise:

| | |
|---|---|
| **Format** | An Ultralytics checkpoint, `.pt`. YOLO11 and YOLOv8 both load. |
| **Task** | **Object detection.** Not segmentation, not classification — the code reads `boxes.xyxy`, and a model without boxes produces zero detections and a silent 100.00 health score. |
| **Class names** | Must be in the checkpoint (`model.names`). Everything downstream is keyed on the name, not the index. |
| **Size** | Under ~100 MB if it is to live in the repo as `best.pt` does. Larger means Git LFS or a download step in the build. |

Nothing else is assumed. Any number of classes, any input size, any
architecture ultralytics can load.

## What class names do downstream

This is the part people miss. The class *name* — not the id — drives three
things, by **case-insensitive substring match**:

**1. Hazard weight** (`DEFECT_CLASS_WEIGHTS` in `app/config.py`), which scales
the Road Risk Index:

```python
"pothole": 1.00,  "rut": 0.85,  "depression": 0.85,  "ravel": 0.70,
"manhole": 0.70,  "alligator": 0.65,  "crack": 0.55,  "patch": 0.45,
# anything unmatched: DEFAULT_CLASS_WEIGHT = 0.75
```

Matching is by substring in insertion order, so `D40_Pothole` scores as a
pothole and `alligator_crack` matches `alligator` before `crack`. That is
deliberate — the RDD2022 naming convention works unmodified.

**2. Recommended remediation** (`RECOMMENDED_ACTIONS`), same substring match,
falling back to a generic action.

**3. The report and the UI** — `defect_counts` keys, the inventory table's
Classification column, and the complaint text all print the raw class name.

**Consequence:** a model with classes like `class_0`, `damage`, `D00` will
*work*, but every defect scores the 0.75 default hazard weight, gets a generic
recommended action, and prints an unreadable label in a document addressed to
GHMC. If the names are not self-describing, either rename them in the
checkpoint or add entries to both tables in `app/config.py`.

## Swapping it in

```bash
cp their_best.pt backend/weights/best.pt
python3 tools/check_model.py          # loads it and prints its classes
uvicorn app.main:app --reload         # look for: status=trained | classes=[...]
```

`GET /health` then reports the new model, including a `version` fingerprint —
architecture plus a content hash of the weights file, e.g.
`yolo11n-935e809b`. That string is stored on every report, so a document can
always be traced to the exact weights behind it. It changes automatically when
the file changes; nobody has to remember to bump anything.

Tune without touching code, via `backend/.env`:

```
CONFIDENCE_THRESHOLD=0.25     # raise to cut false positives
IOU_THRESHOLD=0.45
INFERENCE_IMAGE_SIZE=640      # must match what they trained at
MAX_DETECTIONS=100
```

## What to ask them for

1. **`best.pt`** — the trained checkpoint.
2. **The class list**, exactly as it appears in `model.names`.
3. **Metrics on a held-out test split** — mAP50, mAP50-95, precision, recall.
   Insist on the *test* split, not validation: validation numbers are what the
   training loop selected the best epoch against, so quoting them overstates
   the model. Ours are on test.
4. **`INFERENCE_IMAGE_SIZE` they trained at** — a model trained at 640 and run
   at 1280 quietly gets worse.
5. **Dataset provenance and licence.** Where the images came from, how many,
   the split sizes. The report cites this and a viva will ask.
6. **The training notebook or command**, so the result is reproducible.

If they cannot give you 3 and 5, you have a `.pt` file and no way to defend it.

## How to tell it actually works

```bash
cd backend && pytest -q                    # 112 tests, no model needed
python3 tools/check_model.py               # loads, prints classes
```

Then upload a photograph with a defect you can see, and check the annotated
image in the result. A model that loads but detects nothing produces a health
score of 100.00 and a cheerful "Good" report about a broken road — the most
dangerous failure this system has, because it looks like a success.

---

# Part 2 — Bringing your own frontend

The backend is a plain JSON HTTP API with no session state, so any client
works: React, Vue, Flutter, Android, a Python script.

## Start here

```
http://localhost:8000/docs
```

Interactive OpenAPI documentation, generated from the code, always current.
The machine-readable schema is at `/openapi.json` — most languages can
generate a typed client from it in one command, which is a better use of an
afternoon than hand-writing request code.

## The contract

**Errors** are uniform. Every failure, at every endpoint:

```json
{ "success": false, "error": { "code": "image_too_large", "message": "..." } }
```

Show `message` to the user; branch on `code`. A Python traceback never reaches
the client.

**Auth** is a bearer token.

| Endpoint | Body | Returns |
|---|---|---|
| `POST /auth/signup` | `{name, email, password, city?}` | `{access_token, user}` |
| `POST /auth/login` | `{email, password}` | same |
| `GET /auth/me` | — | the profile behind the token |

Send `Authorization: Bearer <token>` on everything except `/analyze`, `/health`
and `/`. On a 401, discard the token — it is expired or revoked.

**Analysis** is the one multipart endpoint:

```
POST /analyze?include_image=true&include_pdf=true
Content-Type: multipart/form-data

image=<file>  latitude=17.4948  longitude=78.3996
```

Constraints the client must respect, because the server enforces them:

- **≤ 10 MB**, JPEG / PNG / WEBP / BMP. The content type, the extension **and**
  the actual decoded format are all checked — renaming a `.gif` to `.jpg` is
  rejected.
- **Latitude and longitude are required** and validated (-90..90, -180..180).
- Takes **2–10 seconds** on CPU. Show a spinner and disable the button; do not
  let a double click run inference twice.

The response carries the scores, the full detection list, the risk assessment,
and — as base64 inside the JSON — the annotated image and **the complete PDF
report**:

```js
const r = await (await fetch(`${API}/analyze?...`, {method:'POST', body: form})).json();
r.road_health_score      // 81.56
r.total_defects          // 5
r.detections             // [{id, class_name, confidence, bbox, severity, ...}]
r.risk                   // {risk_index, risk_level, priority_tier, components, ...}
r.annotated_image.data   // base64 JPEG, boxes drawn on
r.report.data            // base64 PDF — the real report
```

**Use `r.report`.** Do not build your own PDF from the JSON. That document has
the gauge, the weighted risk components, the geospatial and jurisdiction
panels, the per-defect inventory and the annotated evidence pages. Our own
frontend made this exact mistake for a while: it printed the screen instead,
and shipped a document with none of the analysis in it.

Set `include_pdf=false&include_image=false` for a fast JSON-only preview.

**Reports** need persistence configured on the server.

| Endpoint | Purpose |
|---|---|
| `POST /reports` | File an analysis. `submit: true` files it; otherwise a draft. |
| `GET /reports` | Yours, filterable by `status` and a lat/lon bounding box. |
| `GET /reports/stats` | Totals by condition, risk and status. **Use this for a dashboard** — the list is paginated, so counting the returned page understates the truth. |
| `GET /reports/{id}/pdf` | The document, rebuilt from the stored row. |
| `PATCH /reports/{id}/status` | Move it through the workflow. |

Two rules the server enforces regardless of what a UI shows:

- **A citizen may file and withdraw. Only an `official` may acknowledge or
  resolve.** Hide those buttons by all means, but the server answers 403 —
  the UI is not the guard.
- **A draft is private.** Officials never see one, and reading another user's
  report by id returns **404, not 403**, so the response does not confirm the
  id exists.

Send the photograph with `POST /reports` as `image_base64`. Without it the
report has no evidence and `GET /reports/{id}/pdf` can only refuse with a 409.

## Two things that will cost an afternoon if nobody says them

**CORS.** The browser blocks any origin the API does not know. Add theirs to
`backend/.env`:

```
EXTRA_CORS_ORIGINS=http://localhost:3000,https://their-app.example.com
```

The API prints its full allow-list on every startup. When a request fails with
"Failed to fetch" and no status code, check that line first.

**Build-time vs runtime config.** If they use Vite, Next or CRA, the API base
URL is compiled into the bundle at build time. Changing it needs a rebuild, not
a restart. A deployment pointing at `localhost:8000` fails with no error
anywhere, because nothing failed — it just built against the wrong value.

## An obligation, not a suggestion

If they ship a demo or offline mode with placeholder numbers, **it must be
marked as such on every screen that shows a figure, and in any exported
document.** This app produces a complaint addressed to a municipal body. A
fabricated report that looks official is the specific harm this project has to
avoid, and it is not a design preference.

Ours marks it in four places: a badge in the header, on the dashboard, on the
result page, and a warning block printed at the top of the PDF.

## What to ask them for

1. **The origin(s) their app runs on**, dev and deployed, for the CORS list.
2. **Which endpoints they intend to use.** If they only need `/analyze`, they
   need no accounts, no database and no auth — worth knowing before anyone
   builds a login screen.
3. **Confirmation they render `r.report`** rather than generating their own.
4. **How demo data is marked**, if they have a demo mode.

## Checking their integration

```bash
curl -s http://localhost:8000/health
curl -s -X POST "http://localhost:8000/analyze?include_pdf=false&include_image=false" \
  -F "image=@road.jpg" -F "latitude=17.4948" -F "longitude=78.3996"
```

If those two work from their machine, the API is fine and anything still
broken is in their client.

---

# Deciding what to keep

If both teams have a working frontend, compare on what a viva will actually
probe, not on looks:

- Does it say where every number came from, and that the thresholds are this
  project's own conventions rather than an IRC or MoRTH standard?
- Does it mark demo data everywhere, including in the exported PDF?
- Does it hide privileged actions *and* does the server refuse them?
- Does a filed report survive a refresh, and appear on a second device?
- Can it hand you back the complaint document for a report filed last week?

Those are answerable by clicking, and they are the questions that separate a
demo from a system.
