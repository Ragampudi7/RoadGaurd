# Automated Road Health Assessment & Grievance Tool - Backend

A FastAPI service that turns a citizen's road photograph plus GPS coordinates
into a **Road Health Score**, an **annotated image** and a **complaint-ready PDF**
- all computed in memory, on CPU, with no database, no queue and no cloud storage.

```
photo + GPS  ->  validate  ->  YOLO detection  ->  bounding boxes
             ->  defect area  ->  health score  ->  condition
             ->  per-defect severity  ->  Road Risk Index  ->  priority tier
             ->  annotated image + close-ups  ->  PDF report  ->  JSON response
```

---

## 1. Quick start (local)

Requires **Python 3.11 or newer**.

```bash
# from the repository root
cd backend

# 1. create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# 2. install dependencies
#    macOS / Windows:
pip install -r requirements.txt
#    Linux (avoids downloading ~2.5 GB of unused CUDA wheels):
#    pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision
#    pip install -r requirements.txt

# 3. create your local config
cp .env.example .env

# 4. run
uvicorn app.main:app --reload --port 8000
```

Then open:

| URL | What it is |
|---|---|
| http://localhost:8000/ | status JSON |
| http://localhost:8000/health | health probe + which model is loaded |
| http://localhost:8000/docs | interactive Swagger UI - upload an image and try it |
| `test_client.html` | open this file in a browser for a real end-to-end test with live GPS |

> **You can run all of this before your model is trained.** See section 2.

---

## 2. Where your trained model goes

Put your trained weights here:

```
backend/weights/best.pt
```

That is the whole procedure - `MODEL_PATH=weights/best.pt` is the default, and the
model is loaded once when the server starts. After training with Ultralytics the
file you want is `runs/detect/train/weights/best.pt`; copy it across.

### The shipped model

`weights/best.pt` is a YOLO11n detector (5.5 MB) trained on 3,224 images merged
from two Roboflow datasets - 2,309 train / 601 val / 314 test - with two classes,
`pothole` and `crack`. Trained 100 epochs at 640 px on a Colab T4; the notebook
that produced it is `train_yolo11_colab.ipynb`.

Measured on the **held-out test split** (314 images / 595 instances, never used
for model selection or early stopping):

| | mAP50 | mAP50-95 | precision | recall |
|---|---|---|---|---|
| **overall** | **0.796** | **0.503** | **0.847** | **0.719** |
| pothole | 0.878 | - | 0.878 | 0.780 |
| crack | 0.714 | - | 0.816 | 0.658 |

Read honestly: it finds roughly three quarters of the defects present, and about
15% of what it reports is a false positive. Potholes are detected more reliably
than cracks, and recall on cracks (0.658) is the weakest number - thin or distant
cracks are still missed. Good enough to drive a triage tool; not a substitute for
inspection, and no claim of field accuracy should be made from it.

Serving resolution must match training. `INFERENCE_IMAGE_SIZE` is 640 for these
weights; changing one without the other costs accuracy silently.

### Running before `best.pt` exists

`ALLOW_PRETRAINED_FALLBACK=true` (the default) lets the server start with the
generic pretrained `yolo11n.pt`, which Ultralytics downloads automatically on
first use. This exists **only so the frontend can be built and tested** while the
model is still being trained.

That fallback model detects COCO objects - person, car, bottle - **not potholes**.
So whenever it is active:

* `model_info.status` is `"pretrained_fallback"` and `is_road_defect_model` is `false`
* a warning is returned in `warnings[]`
* the annotated image carries a red **DEMONSTRATION MODE** banner
* the PDF carries a red **"NOT A VALID COMPLAINT"** strip
* the complaint text is replaced with a demonstration notice

Once your real weights are in place, set `ALLOW_PRETRAINED_FALLBACK=false` so the
server can never silently serve demonstration results. With the flag off and no
weights present, `/analyze` returns **503** and `/health` reports `degraded`.

See `TRAINING.md` for how to produce `best.pt`.

---

## 3. API

### `GET /`

```json
{
  "status": "ok",
  "message": "Automated Road Health Assessment API is running",
  "version": "1.0.0",
  "docs_url": "/docs"
}
```

### `GET /health`

Always returns 200 (so Render does not restart a healthy container).
`status` is `"ok"` when a model is loaded, `"degraded"` otherwise.

```json
{
  "status": "ok",
  "version": "1.0.0",
  "uptime_seconds": 142.8,
  "model_loaded": true,
  "model": {
    "status": "trained",
    "name": "best.pt",
    "classes": ["pothole", "crack"],
    "device": "cpu",
    "confidence_threshold": 0.25,
    "iou_threshold": 0.45,
    "is_road_defect_model": true
  }
}
```

### `POST /analyze`

`multipart/form-data`

| Field | Type | Required | Notes |
|---|---|---|---|
| `image` | file | yes | JPG, PNG, WEBP or BMP, up to `MAX_IMAGE_SIZE_MB` |
| `latitude` | float | yes | -90 to 90 |
| `longitude` | float | yes | -180 to 180 |

Optional query parameters:

| Query | Default | Notes |
|---|---|---|
| `include_image` | `true` | set `false` to omit the base64 annotated JPEG |
| `include_pdf` | `true` | set `false` for a fast JSON-only response (live preview) |

**Response (200)** - trimmed:

```json
{
  "success": true,
  "request_id": "RHA-20260902-A7F3C1",
  "analysed_at": "2026-09-02T17:42:11+05:30",

  "road_health_score": 86.59,
  "road_condition": "Fair",
  "defect_percentage": 13.41,

  "total_defects": 4,
  "defect_counts": { "pothole": 3, "alligator_crack": 1 },
  "detections": [
    {
      "id": 1,
      "class_id": 0,
      "class_name": "pothole",
      "confidence": 0.91,
      "bbox": [250, 520, 610, 790],
      "area": 97200,
      "area_percentage": 6.08,
      "severity": "High",
      "severity_rank": 2,
      "severity_colour": "#B01B1B",
      "recommended_action": "Hot-mix / cold-mix asphalt fill with mechanical compaction"
    }
  ],

  "risk": {
    "risk_index": 32.43,
    "risk_level": "Moderate",
    "risk_colour": "#C2560F",
    "priority_tier": "Priority-3",
    "response_window": "Remediate within 30 days",
    "components": [
      { "name": "Extent", "value": 14.54, "unit": "of the frame damaged",
        "value_display": "14.54% of the frame damaged", "full_scale": 25.0,
        "score": 58.16, "weight": 0.5 },
      { "name": "Worst defect", "value": 6.08, "unit": "of the frame in one box",
        "value_display": "6.08% of the frame in one box", "full_scale": 10.0,
        "score": 60.8, "weight": 0.3 },
      { "name": "Density", "value": 5.0, "unit": "defects detected",
        "value_display": "5 defects detected", "full_scale": 8.0,
        "score": 62.5, "weight": 0.2 }
    ],
    "hazard_factor": 0.89,
    "confidence_factor": 0.61,
    "max_severity": "High",
    "dominant_defect": "pothole",
    "summary": "Modelled risk is moderate (32.4 / 100). The worst single defect is rated high, ..."
  },

  "location": {
    "latitude": 17.4948,
    "longitude": 78.3996,
    "maps_url": "https://www.google.com/maps/search/?api=1&query=17.494800,78.399600"
  },
  "image": {
    "filename": "road.jpg", "width": 1600, "height": 1000, "area_pixels": 1600000,
    "sha256": "b9483e7a8780ec49c6183268d61cfc6c..."
  },

  "area_breakdown": {
    "method": "sum",
    "summed_area_pixels": 214600,
    "union_area_pixels": 214600,
    "summed_percentage": 13.41,
    "union_percentage": 13.41,
    "overlap_detected": false
  },

  "model_info": { "status": "trained", "is_road_defect_model": true, "...": "..." },
  "complaint_description": "Road surface defects were detected ...",
  "addressed_to": "Greater Hyderabad Municipal Corporation (GHMC)",
  "processing_time_ms": 812,
  "warnings": [],

  "annotated_image": {
    "filename": "RHA-20260902-A7F3C1_annotated.jpg",
    "mime_type": "image/jpeg",
    "encoding": "base64",
    "size_bytes": 184203,
    "data": "/9j/4AAQSkZJRgABAQ..."
  },
  "report": {
    "filename": "road_health_report_RHA-20260902-A7F3C1.pdf",
    "mime_type": "application/pdf",
    "encoding": "base64",
    "size_bytes": 123293,
    "data": "JVBERi0xLjQKJeLj..."
  },
  "defect_crops": [
    { "filename": "..._defect_1.jpg", "mime_type": "image/jpeg",
      "encoding": "base64", "size_bytes": 8104, "data": "/9j/4AAQ..." }
  ]
}
```

`defect_crops` is index-aligned with `detections`, so `defect_crops[0]` is the
close-up of `detections[0]`. It is populated only when `include_image=true`.

`image.sha256` is the digest of the uploaded bytes exactly as received. It is a
real, recomputable value - `shasum -a 256 road.jpg` on the citizen's own file
gives the same string - so the report can be tied to a specific photograph. It
proves which file was analysed; it does not prove when or where the photo was
taken.

### What the PDF contains

Three pages, each with one job.

| Page | Contents |
|---|---|
| 1 - **Assessment & risk** | Masthead with the condition and risk chips and the reference; a Road Health Index gauge with three KPI tiles; the **Road Risk Assessment** panel - risk index, banded remediation-urgency meter, and the three weighted components each shown as a bar with its measurement and weight; capture telemetry and municipal routing cards; the official grievance statement |
| 2 - **Inventory & analytics** | Defect inventory (one row per detection: class chip, confidence bar, severity, frame area, suggested remediation), then three charts - defect count by severity band, frame share per defect, and the health score plotted against the project's condition bands - and the methodology panel |
| 3 - **Visual evidence** | The annotated photograph with a figure caption, and a grid of isolated close-ups, one per detection |

Every chart is drawn with ReportLab's own vector primitives - no chart library,
no raster images - so they stay sharp at any zoom and cost nothing at install
time.

The page footer carries **only the reference number**. Nothing else: no page
numbers, no hash, no strapline. Everything a reader needs to judge the document
is in the body, and the methodology panel carries the caveats where they can
actually be read.

A clean road with no defects collapses to a shorter report - the inventory
becomes a single "nothing detected" note and the close-up grid disappears. When
no trained model is installed, a red **DEMONSTRATION OUTPUT - NOT A VALID
COMPLAINT** strip sits directly under the masthead and the evidence photo
carries a matching banner.

#### Why the PDF is base64 inside the JSON

A grievance report is only useful next to the numbers that justify it, and this
project is meant to run without persistent storage. Returning both in a single
response means:

* **one** request, so **one** YOLO inference - the expensive part is never repeated;
* nothing is written to disk and there is no temporary file, no cleanup job, no
  expiring cache and no `/report/{id}` endpoint that breaks when Render's free
  instance sleeps or restarts;
* the frontend can render the score *and* offer the download from the same
  `await response.json()`.

The cost is payload size (base64 is ~33% larger than raw bytes). That is why
gzip compression is enabled server-side, why the annotated image is downscaled
to 1280 px before encoding, and why `?include_pdf=false` exists for a fast
preview call.

### Errors

Every failure returns the same shape - never a stack trace:

```json
{ "success": false, "error": { "code": "image_too_large", "message": "Image exceeds the 10.0 MB limit." } }
```

| HTTP | `error.code` | Cause |
|---|---|---|
| 400 | `image_missing` / `image_empty` | no file, or a zero-byte file |
| 413 | `image_too_large` | over `MAX_IMAGE_SIZE_MB` |
| 415 | `image_type_unsupported` | wrong MIME type, extension or real format |
| 422 | `request_invalid` | a required form field is missing |
| 422 | `image_invalid` | bytes are not a decodable image |
| 422 | `image_dimensions_invalid` | too small, or absurdly large |
| 422 | `coordinates_invalid` | latitude/longitude out of range or not a number |
| 500 | `inference_failed` | the model threw during prediction |
| 500 | `image_processing_failed` / `report_generation_failed` | annotation or PDF failed |
| 500 | `internal_error` | anything unexpected (details go to the server log only) |
| 503 | `model_unavailable` | no model loaded |
| 503 | `server_busy` | inference queue timed out |

### curl

```bash
curl -X GET http://localhost:8000/health

curl -X POST "http://localhost:8000/analyze" \
  -F "image=@/path/to/road.jpg" \
  -F "latitude=17.4948" \
  -F "longitude=78.3996" \
  -o result.json

# pull the PDF out of the response
python -c "import json,base64;d=json.load(open('result.json'));open('report.pdf','wb').write(base64.b64decode(d['report']['data']))"

# fast, JSON-only preview
curl -X POST "http://localhost:8000/analyze?include_pdf=false&include_image=false" \
  -F "image=@road.jpg" -F "latitude=17.4948" -F "longitude=78.3996"
```

---

## 4. Accounts, reports and the grievance loop

Everything in section 3 works with no database at all: `POST /analyze` takes a
photograph and hands back a scored assessment and a PDF. That is the whole
product for one visit. What it cannot do is remember - close the tab and the
complaint is gone.

Set `DATABASE_URL` and the rest of this section switches on. Leave it unset and
the API behaves exactly as before, endpoints and all; nothing here is required
to demonstrate detection.

### Accounts

| | |
|---|---|
| `POST /auth/signup` | `{name, email, password, city?}` -> a token and the profile |
| `POST /auth/login` | `{email, password}` -> the same |
| `GET /auth/me` | the profile behind the bearer token |
| `PATCH /auth/me` | change name or city |

Passwords are bcrypt-hashed. A password over 72 bytes is **rejected** rather
than silently truncated, which is what bcrypt does on its own and what turns a
long passphrase into its first 72 bytes without telling anybody.

Login answers **the same message** for an unknown email and a wrong password.
Distinguishing them turns the login form into an account-enumeration oracle:
type an address, read the error, learn whether that person has an account.
There is a test asserting the two strings are identical, because this is the
kind of thing that gets "improved" into a friendlier message.

Tokens are HS256 JWTs. `JWT_SECRET` must be at least 32 bytes (RFC 7518 §3.2)
and the app **refuses to start in production** with the development default -
a signing key that ships in a repository signs anybody's tokens.

### Reports

| | |
|---|---|
| `POST /reports` | file an assessment; `submit: true` files it, otherwise it is a draft |
| `GET /reports` | your reports, filterable by status and by map bounding box |
| `GET /reports/stats` | totals by condition, risk, status; average score; worst |
| `GET /reports/{id}` | one report, with its full detection list |
| `GET /reports/{id}/image` | the original photograph |
| `GET /reports/{id}/pdf` | **the complaint document, rebuilt** |
| `PATCH /reports/{id}/status` | move it through the workflow |
| `DELETE /reports/{id}` | only your own |

**What is stored, and what is not.** Metadata, the full detection list, and the
original photograph. The annotated image, the close-up crops and the PDF are
all thrown away and rebuilt on demand. That is roughly 102 KB per report
instead of 415 KB - about 10,000 reports on a 1 GB free tier instead of 2,400.

That bargain only holds because `GET /reports/{id}/pdf` exists. It replays the
stored numbers; it never re-runs the model. The rebuilt document is stamped
**REGENERATED COPY** with the date and the weights fingerprint the figures were
produced under, and if the scoring configuration has changed since it was filed,
it says so on the page instead of quietly showing the new number. This is why
`model_name` and `model_version` are columns: a report rendered under different
weights is a different document, and the version is how anyone notices.

### The workflow, and who may move it

```
Draft  ──file──▶  Submitted  ──acknowledge──▶  Acknowledged  ──resolve──▶  Resolved
  ▲                    │                             │                        │
  └────withdraw────────┘                             └──────reopen────────────┘
       (citizen)                                              (official)
```

A citizen files and withdraws their own reports. An official acknowledges,
resolves, and reopens a resolution that did not hold. **Neither reaches into
the other's half**: a citizen who could mark their own complaint Resolved makes
the status meaningless, and an official who could push one back to Draft would
be un-filing a complaint the citizen did send. Both refusals are 403 from the
server, not a hidden button - the UI hides them too, but the UI is not the
guard.

### Who is an official

`OFFICIAL_EMAILS`, a comma-separated list of whole addresses
(`engineer@ghmc.gov.in`) or domain suffixes (`@ghmc.gov.in`). Checked at signup
and re-checked at every login, so adding an address promotes that account the
next time it signs in and removing one demotes it, without touching the
database.

Two things it is deliberately **not**:

* **Not a field on the signup form.** A self-declared role is no role. Send
  `{"role": "official"}` to `/auth/signup` and you get a citizen account; there
  is a test for it.
* **Not an invite code.** A shared secret in the UI is a password that every
  holder can pass to anybody else, and nobody can revoke it without changing it
  for everyone.

The grant belongs to whoever configures the deployment, because that is the
only party that actually holds the authority.

An official sees `GET /reports?mine=false` - every **filed** complaint, worst
first. Drafts never appear: an unsent working copy is not a complaint. Reading
one by id returns **404 rather than 403**, so the response does not confirm the
id exists either. The queue carries no reporter contact details; the complaint
is about a road, and handing every official the citizen's email would be
collecting personal data the job does not need.

### Schema changes

`Base.metadata.create_all` only ever **creates** tables. On a database whose
tables already exist it does nothing at all, silently - including when a model
has grown a column since. That fails in exactly the worst way: a fresh local
database gets the new column from the create, the deployed one does not, and
the first insert dies with `UndefinedColumnError` in production.

So start-up reconciles. Any column the models declare, the table lacks, and
which is nullable or has a default is added with `ALTER TABLE`. Anything else -
a dropped column, a changed type, a new `NOT NULL` over existing rows - is
logged loudly and left alone, because those need a migration that decides what
happens to the data already there. This is not a substitute for Alembic on a
system with real users; it is what keeps a small deployment honest.

---

## 5. Frontend integration

```js
// 1. live GPS from the browser
const position = await new Promise((resolve, reject) =>
  navigator.geolocation.getCurrentPosition(resolve, reject, {
    enableHighAccuracy: true,
    timeout: 15000,
  })
);

// 2. upload
const form = new FormData();
form.append("image", fileInput.files[0]);
form.append("latitude", position.coords.latitude);
form.append("longitude", position.coords.longitude);

const response = await fetch(`${API_BASE}/analyze`, { method: "POST", body: form });
const result = await response.json();

if (!result.success) {
  showError(result.error.message);      // always safe to display
  return;
}

// 3. show the findings
scoreEl.textContent = result.road_health_score.toFixed(2);
conditionEl.textContent = result.road_condition;
previewEl.src = `data:image/jpeg;base64,${result.annotated_image.data}`;

// 4. offer the PDF download
const bytes = Uint8Array.from(atob(result.report.data), (c) => c.charCodeAt(0));
const url = URL.createObjectURL(new Blob([bytes], { type: "application/pdf" }));
const link = Object.assign(document.createElement("a"), {
  href: url,
  download: result.report.filename,
});
link.click();
URL.revokeObjectURL(url);
```

Set `FRONTEND_URL` (and `EXTRA_CORS_ORIGINS` for Vercel preview deployments) on
the server, or the browser will block the request before it is even sent.

`test_client.html` in this folder is a working, dependency-free implementation of
exactly the above - open it in a browser to test the whole flow.

---

## 6. How the numbers are calculated

For every detection the model gives a class, a confidence and a box:

```
box_area          = (x2 - x1) * (y2 - y1)
image_area        = image_width * image_height
total_defect_area = sum(box_area for every detection)
defect_percentage = total_defect_area / image_area * 100
road_health_score = max(0, 100 - defect_percentage)
```

All of this lives in `app/services/scoring_service.py`.

### Overlapping boxes - read this before your viva

Following the project specification, **version 1 simply sums the box areas**.
When two boxes overlap, the shared pixels are therefore counted twice, which
over-states the damage; with many overlapping boxes the summed figure could even
exceed 100% (it is clamped so the score never goes below 0).

Because that is a genuine limitation, the backend **also** computes the exact
overlap-free area on every request and returns both:

```json
"area_breakdown": {
  "method": "sum",
  "summed_percentage": 31.40,
  "union_percentage": 24.05,
  "overlap_detected": true
}
```

When overlap is detected, an explanatory entry appears in `warnings[]`, and the
methodology note at the bottom of the PDF prints both figures.

To score on the overlap-corrected number instead, set `AREA_METHOD=union` - no
code change. The union is computed exactly (not approximated) by coordinate
compression: the distinct box edges cut the frame into a small grid, each cell is
wholly inside or outside the boxes, and the covered cells' real areas are summed.

### Classification bands

| Score | Condition |
|---|---|
| 90.00 - 100.00 | Good |
| 70.00 - 89.99 | Fair |
| 40.00 - 69.99 | Poor |
| 0.00 - 39.99 | Dangerous |

**These bands are defined by this project team.** They are a reasonable, easy to
justify starting point - they are *not* taken from IRC, MoRTH, GHMC or any other
official road-condition standard, and the report says so. Change them in one
place: `ROAD_CONDITION_BANDS` in `app/config.py`. The API, the PDF and the tests
all follow automatically.

### Estimating road risk

The health score answers *"how much of this photograph is damaged?"*. That is
not the question a municipal desk actually needs answered, which is *"how
urgently should someone be sent?"* - so the backend computes a separate **Road
Risk Index** (0-100, higher is worse). All of it lives in
`app/services/risk_service.py`.

**Per-defect severity.** Every detection is banded by the share of the frame its
own box covers, then demoted one band if the model was unsure, so a large
low-confidence blob cannot manufacture a "Critical" finding:

| Box covers | Severity |
|---|---|
| >= 8% of the frame | Critical |
| 3 - 8% | High |
| 1 - 3% | Medium |
| < 1% | Minor |

Confidence below `0.40` drops the result one band. Each severity also picks a
suggested remediation from a small per-class table (`RECOMMENDED_ACTIONS` in
`config.py`) - a starting point for the engineering wing, offered as such in the
report, not an engineering instruction.

**The index.** Three interpretable components, each divided by the value at
which it counts as maxed out, then weighted:

| Component | Measures | Full scale | Weight |
|---|---|---|---|
| Extent | defect percentage of the frame | 25% | 0.50 |
| Worst defect | largest single box as a share of the frame | 10% | 0.30 |
| Density | number of detections | 8 | 0.20 |

```
raw        = 0.50*extent + 0.30*worst_defect + 0.20*density        # each 0-100
hazard     = area-weighted mean class weight   (pothole 1.00 ... patch 0.45)
confidence = mean detection confidence, floored at 0.50
risk_index = min(100, raw * hazard * confidence)
```

`hazard` is why a pothole outranks a hairline crack of the same size;
`confidence` is why an uncertain model produces a correspondingly softer claim
rather than a confident one. Both factors, every weight and every full scale are
environment variables (`RISK_WEIGHT_EXTENT`, `RISK_EXTENT_FULL_SCALE`, ...) and
the class weights are a dict in `config.py`, so the whole model is tunable
without touching a formula.

**Bands and grievance tier.**

| Risk index | Level | Tier | Suggested response |
|---|---|---|---|
| 75 - 100 | Critical | Priority-1 | Immediate action - within 48 hours |
| 50 - 75 | High | Priority-2 | Remediate within 7 days |
| 25 - 50 | Moderate | Priority-3 | Remediate within 30 days |
| 0 - 25 | Low | Routine | Routine maintenance cycle |

Like the health bands, **these are project conventions, not an official
standard**, and the PDF states that explicitly rather than implying municipal
endorsement.

### What the score does and does not mean

It measures **how much of one photograph is covered by defect bounding boxes**.
It does not know depth, road width, traffic volume or how far away the camera
was. Two photos of the same pothole taken from different distances give different
scores. It is a screening and prioritisation aid, not a survey instrument - which
is exactly what the PDF's methodology panel tells the reader.

The same caveat applies with more force to risk. "Severity" here is an *extent*
proxy - how much of the frame a defect occupies - and a photograph carries no
depth and no scale, so a close-up of a shallow pothole will out-score a distant
shot of a dangerous one. Say this plainly in your report; it is a better answer
than pretending the number means more than it does.

Two things the tool deliberately does **not** claim: the report is never marked
as verified, logged or accepted by any authority (its status line reads
"Prepared by the citizen - not yet filed"), and no detection is ever described
as "deep" or otherwise depth-measured.

---

## 7. Configuration

Everything is an environment variable; nothing is hardcoded. Copy `.env.example`
to `.env` for local development. On Render, set these in the dashboard or in
`render.yaml`.

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | free-form label used in logs |
| `LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL` |
| `MODEL_PATH` | `weights/best.pt` | trained weights, relative to `backend/` |
| `ALLOW_PRETRAINED_FALLBACK` | `true` | use a generic model when weights are missing |
| `FALLBACK_MODEL_NAME` | `yolo11n.pt` | which generic model (`yolov8n.pt` also works) |
| `CONFIDENCE_THRESHOLD` | `0.25` | minimum confidence to keep a detection |
| `IOU_THRESHOLD` | `0.45` | NMS IoU threshold |
| `MAX_DETECTIONS` | `100` | hard cap per image |
| `INFERENCE_IMAGE_SIZE` | `640` | longest side YOLO runs at |
| `MAX_IMAGE_SIZE_MB` | `10` | upload limit |
| `MIN_IMAGE_DIMENSION` | `64` | reject thumbnails |
| `MAX_IMAGE_DIMENSION` | `8000` | reject decompression bombs |
| `MAX_ANNOTATED_DIMENSION` | `1280` | size of the delivered annotated JPEG |
| `ANNOTATED_JPEG_QUALITY` | `82` | JPEG quality of that image |
| `AREA_METHOD` | `sum` | `sum` (specification) or `union` (overlap-corrected) |
| `RISK_EXTENT_FULL_SCALE` | `25.0` | defect % at which the extent component scores 100 |
| `RISK_SEVERITY_FULL_SCALE` | `10.0` | single-box % at which the worst-defect component scores 100 |
| `RISK_DENSITY_FULL_SCALE` | `8` | defect count at which the density component scores 100 |
| `RISK_WEIGHT_EXTENT` | `0.50` | weight of extent in the index (weights are normalised) |
| `RISK_WEIGHT_SEVERITY` | `0.30` | weight of the worst-defect component |
| `RISK_WEIGHT_DENSITY` | `0.20` | weight of the density component |
| `INCLUDE_DEFECT_CROPS` | `true` | render per-defect close-ups in the report and response |
| `MAX_DEFECT_CROPS` | `6` | cap on how many close-ups are produced |
| `CROP_THUMBNAIL_SIDE` | `360` | longest side of each close-up, in pixels |
| `DATABASE_URL` | *(unset)* | Postgres. Unset means no accounts, no stored reports - `/analyze` is unaffected |
| `JWT_SECRET` | dev default | signs session tokens; production start-up **refuses** the default or anything under 32 bytes |
| `JWT_EXPIRES_HOURS` | `72` | session lifetime |
| `OFFICIAL_EMAILS` | *(empty)* | who may acknowledge and resolve: whole addresses or `@domain` suffixes, comma-separated (section 4) |
| `FRONTEND_URL` | `http://localhost:3000` | CORS origin for your frontend |
| `EXTRA_CORS_ORIGINS` | *(empty)* | comma-separated extra origins |
| `MUNICIPAL_AUTHORITY` | GHMC | who the complaint is addressed to |
| `ENGINEERING_WING` | Roads & Maintenance Division | printed in the routing card |
| `COMPLAINT_REGION` | Hyderabad, Telangana, India | printed on the report |
| `REPORT_TIMEZONE_OFFSET_MINUTES` | `330` | IST; report timestamps use this |
| `MAX_CONCURRENT_INFERENCES` | `1` | how many images may be analysed at once |

---

## 8. Project structure

```
backend/
├── app/
│   ├── main.py                     FastAPI app, CORS, error handlers, startup model load
│   ├── config.py                   ALL settings + the classification bands
│   ├── api/
│   │   ├── routes.py               GET /, GET /health, POST /analyze
│   │   ├── auth.py                 signup, login, profile; the bearer-token dependency
│   │   └── reports.py              filing, listing, stats, status, evidence, rebuilt PDF
│   ├── services/
│   │   ├── assessment_service.py   the pipeline, start to finish
│   │   ├── detection_service.py    YOLO singleton, CPU inference, fallback logic
│   │   ├── scoring_service.py      area, percentage, score, classification, complaint text
│   │   ├── risk_service.py         severity bands, hazard weights, Road Risk Index
│   │   ├── image_service.py        annotation, close-up crops, JPEG encoding (all in BytesIO)
│   │   ├── pdf_service.py          ReportLab report: gauge, risk meter, inventory, evidence
│   │   └── report_render.py        rebuilds a filed report's PDF from the stored row
│   ├── models/
│   │   └── schemas.py              every request/response shape
│   ├── db/
│   │   ├── base.py                 engine, session, URL normalisation, schema reconcile
│   │   └── models.py               User and Report, and what is deliberately not stored
│   └── utils/
│       ├── validation.py           image + GPS validation
│       ├── security.py             bcrypt hashing, JWT sign and verify
│       ├── errors.py               typed errors -> HTTP status codes
│       └── logging_config.py       stdout logging
├── tests/                          112 tests, no model and no database needed
├── db_e2e.py                       auth + persistence against a real Postgres
├── pdf_regen_test.py               rebuilding a filed report's document
├── official_e2e.py                 the official role, the queue, and its limits
├── tools/check_model.py            verify best.pt loads and print its classes
├── weights/best.pt                 <- your trained model goes here
├── test_client.html                browser test page with live GPS
├── build.sh                        Render build (CPU torch, headless cv2)
├── requirements.txt
├── .env.example
├── .env.aiven.example              DATABASE_URL, JWT_SECRET, OFFICIAL_EMAILS
├── TRAINING.md
└── README.md
```

Layering rule: **routes never contain business logic, services never import
FastAPI.** That is what makes the pipeline testable without a web server.

---

## 9. Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

86 tests, all of which run **without torch or Ultralytics installed** - a stub
detector is injected in place of the real model - so the suite is fast (under a
second) and works in CI. It covers:

* the area / score / classification maths, including the overlapping-box case;
* the risk model - severity bands and the low-confidence demotion, class hazard
  weights, band boundaries, weight normalisation, and the properties that matter
  (more damage raises the index, potholes outrank cracks at identical geometry,
  low confidence softens it, the index stays inside 0-100);
* image validation, including the renamed-file and path-traversal guards;
* annotation and crop extraction, and real JPEG / PDF output (`%PDF-` header and
  `%%EOF` trailer checked);
* the evidence hash matching the uploaded bytes;
* every error code, and an assertion that no traceback or filesystem path ever
  appears in a response body.

To verify the real model loads:

```bash
python tools/check_model.py
```

---

## 10. Deploying to Render (free tier)

1. Push this repository to GitHub.
2. In Render: **New +** -> **Blueprint** -> select the repository. `render.yaml`
   lives at the **repository root** - that is where Render looks, and each
   service names its own `rootDir` from there.
3. The blueprint brings up **two** services: `roadguard-api` and the static
   site `roadguard-ui`. They reference each other's hostnames, so no URL is
   pasted twice - the API learns the UI's origin for CORS, and the UI is built
   against the API's host. Render supplies both as bare hostnames with no
   scheme; `app/config.py` and `src/lib/api.js` each add one, which is the only
   reason this works.
4. Render prompts for the values marked `sync: false`. Set them:
   * `DATABASE_URL` - the Aiven connection string
   * `JWT_SECRET` - at least 32 bytes; generate with
     `python3 -c "import secrets; print(secrets.token_urlsafe(48))"`
   * `OFFICIAL_EMAILS` - who may acknowledge and resolve (see section 4). Leave
     it blank and every account is a citizen.
   * `EXTRA_CORS_ORIGINS` - optional; a custom domain or a preview URL.
5. Deploy. First build takes 5-10 minutes, mostly PyTorch.
5. Check `https://<your-service>.onrender.com/health`.

Doing it manually instead of with the blueprint:

* Root directory: `backend`
* Build command: `bash build.sh`
* Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
* Health check path: `/health`

`$PORT` is injected by Render and must never be hardcoded; `0.0.0.0` is required
or the platform cannot reach the process.

### Getting `best.pt` onto Render

Already done: `.gitignore` ignores `weights/*.pt` but re-includes
`!weights/best.pt`, and the 5.3 MB trained model is committed. Worth knowing
why the exception is written that way - without it `git add weights/best.pt`
fails **silently**, the push succeeds, and Render serves the generic COCO model
to citizens filing municipal complaints.

That is also why the blueprint sets `ALLOW_PRETRAINED_FALLBACK=false` in
production. The fallback exists so the API can start before you have trained
anything; it must never quietly stand in for a model that failed to deploy.

If the model ever outgrows what a repository should hold (say past 100 MB),
switch to Git LFS or download it in `build.sh` from a GitHub Release.

---

## 11. Performance on Render's free tier - be realistic

A free instance is **0.1 CPU (shared) and 512 MB RAM**. Measured expectations:

| | |
|---|---|
| Cold start after sleep | **50-90 s** - free instances sleep after 15 min idle, and the whole Python + torch + model load happens on the first request |
| Warm inference (YOLO11n, 640 px, CPU) | **~0.9 s** per image (measured end to end on the shipped `best.pt`) |
| Full request (inference + annotation + PDF) | **2-6 s** |
| Memory at rest | ~350-450 MB, uncomfortably close to the 512 MB ceiling |
| Concurrency | effectively **one image at a time** |

What this backend already does about it:

* the model is loaded **once at startup** and warmed up with a dummy inference,
  never per request;
* inference runs in a worker thread so `/health` still answers while YOLO works;
* `MAX_CONCURRENT_INFERENCES=1` serialises inference - a second upload waits
  instead of causing an out-of-memory kill (and gets `503 server_busy` after 55 s);
* `OMP_NUM_THREADS=1` / `MKL_NUM_THREADS=1` stop torch from spawning threads that
  only fight each other on a shared core;
* images are annotated once, downscaled once, and never copied unnecessarily;
* CPU-only torch wheels keep the build inside the free disk budget;
* gzip shrinks the base64 response.

What you cannot fix on the free tier: the cold start. For a demo, hit `/health`
a minute before you present, or use an uptime pinger to keep the instance awake.
If it is still too slow, use a smaller `INFERENCE_IMAGE_SIZE` (`512` or `416`),
or export the model to ONNX and run it with `onnxruntime`.

---

## 12. Security

* **File type** checked three times: declared MIME type, file extension, and the
  real format Pillow detects after decoding (a `.txt` renamed to `.jpg` is rejected).
* **File size** enforced *while streaming* the upload, so an oversized request is
  abandoned early rather than buffered in full.
* **Dimensions** bounded on both ends; `Image.MAX_IMAGE_PIXELS` guards against
  decompression bombs.
* **Nothing is written to disk and nothing is executed.** Uploads exist only as
  bytes in memory for the duration of the request.
* **Filenames are sanitised** to a basename before they reach the PDF, so
  `../../etc/passwd.jpg` cannot travel anywhere.
* **No secrets in code.** Every setting is an environment variable; `.env` is
  gitignored.
* **CORS is explicit** and configurable per deployment; it is never `*` unless you
  deliberately set it.
* **No stack traces, no internal paths** in responses - the full exception goes to
  the server log, the client gets a stable error code and a readable sentence.
  There is a test that asserts this.

Not included, and worth saying out loud in a report: there is no authentication
and no rate limiting. Anyone who knows the URL can post images. For a college
project on a free tier that is acceptable; for anything real, put the API behind
an API key or a reverse proxy with rate limiting.

---

## 13. Troubleshooting

| Symptom | Fix |
|---|---|
| `ImportError: libGL.so.1` | `pip uninstall opencv-python && pip install opencv-python-headless` (`build.sh` does this) |
| Build fails / disk full on Render | torch pulled the CUDA wheels - make sure the build uses `build.sh` |
| `/analyze` returns 503 `model_unavailable` | no `weights/best.pt` and `ALLOW_PRETRAINED_FALLBACK=false` |
| Results look like `person`, `car`, `chair` | the fallback model is active - add `weights/best.pt` |
| Browser: "blocked by CORS policy" | set `FRONTEND_URL` to your frontend origin, no trailing slash, then redeploy |
| `navigator.geolocation` is undefined / permission denied | geolocation needs HTTPS (or `localhost`); open `test_client.html` from `localhost`, not `file://`, if your browser refuses |
| First request takes over a minute | free-instance cold start - see section 10 |
| `422 request_invalid` from a working form | the field names must be exactly `image`, `latitude`, `longitude` |
| Score is 100 for an obviously bad road | the model found nothing above `CONFIDENCE_THRESHOLD` - lower it, or the model needs more training data |
