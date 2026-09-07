# RoadGuard AI

**Automated Road Health Assessment & Grievance Tool**

A citizen photographs a road defect. A YOLO11 model finds the potholes and
cracks, the backend scores the surface and estimates how urgently it needs
attention, and the result comes back as a complaint-ready PDF addressed to the
Greater Hyderabad Municipal Corporation. A municipal official picks it up from
a queue and works it through to resolution.

[**See what it produces →** `docs/sample-report.pdf`](docs/sample-report.pdf)

---

## What is actually in here

| | |
|---|---|
| [`backend/`](backend/README.md) | FastAPI. Detection, scoring, risk, PDF generation, accounts, reports. 112 unit tests. |
| [`frontend/`](frontend/README.md) | React 19 + Vite. Glass UI, map, dashboard, the official's queue. |
| [`render.yaml`](render.yaml) | One blueprint, both services, wired to each other. |
| `backend/weights/best.pt` | The trained model, 5.3 MB, committed so a deploy cannot silently run without it. |

Each directory's README is the real documentation. This page is the map.

---

## Run it

```bash
# backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload          # http://localhost:8000/docs

# frontend, in another terminal
cd frontend
npm install
cp .env.example .env                   # demo mode by default
npm run dev                            # http://localhost:5173
```

That gives you the app on fixed sample data, with no database and no model
download. To run the real thing, set `VITE_USE_MOCK=false` in `frontend/.env`
and put a `DATABASE_URL` in `backend/.env` — see
[`backend/.env.aiven.example`](backend/.env.aiven.example).

---

## The model

YOLO11n, trained on a Colab T4 over two merged Roboflow Universe datasets
(potholes and cracks), 100 epochs at 640 px. Two classes: `pothole`, `crack`.
Inference runs on CPU — the whole thing is designed to fit a free-tier
instance. [`backend/TRAINING.md`](backend/TRAINING.md) covers the dataset
merge and the class-id remapping;
[`backend/train_yolo11_colab.ipynb`](backend/train_yolo11_colab.ipynb) is the
notebook that produced `best.pt`.

---

## Things worth knowing before you read the code

**None of the thresholds are official.** The condition bands, the hazard
weights and the Road Risk Index are this project's own conventions, defined in
one place (`backend/app/config.py`) and labelled as such in the code, in the
API responses and on the PDF itself. They are not from IRC, MoRTH or GHMC, and
the report says so on the page. A photograph carries no depth or scale, so
"severity" here means how much of the frame a defect covers — not how deep it
is.

**Demo data is marked wherever it appears.** With `VITE_USE_MOCK=true` every
number on screen is fabricated, and the app says so: a badge in the header, on
the dashboard and on the result, a striped banner on the result page, and a
warning block printed at the top of any exported PDF. This app produces a
document addressed to a municipal body; an invented report that looked
official would be a real problem, so the marking is load-bearing rather than
decorative.

**A report knows which model made it.** `model_version` is a content
fingerprint of the weights (`yolo11n-935e809b`), not a number somebody has to
remember to bump. A PDF regenerated after a retrain is stamped as a
regenerated copy and names the version behind its figures, because a report
re-rendered under different weights is a different document.

**Only the photograph and the numbers are stored.** The annotated image, the
close-up crops and the PDF are all rebuilt on demand from the stored row —
about 102 KB per report instead of 415 KB, which is roughly 10,000 reports on
a 1 GB free tier instead of 2,400.

**Roles are granted by the deployment, never requested.** Whether an account
can acknowledge and resolve complaints comes from an `OFFICIAL_EMAILS`
allow-list, not a field on the signup form and not an invite code. A citizen
files and withdraws; an official acknowledges, resolves and reopens; neither
reaches into the other's half, enforced server-side rather than by a hidden
button.

---

## Tests

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q                    # 112 tests, no model and no database needed
```

Three further suites need a live PostgreSQL (`db_e2e.py`,
`pdf_regen_test.py`, `official_e2e.py`), and two drive a real browser against
a running stack (`frontend/e2e_real.py`, `frontend/e2e_official.py`). Those
last two exist because a test client cannot see everything a browser does — a
CORS preflight and a `File` turning into base64 are both invisible to `httpx`,
and both hid real bugs.

---

## Deploying

`render.yaml` at the repository root brings up both services. See
[section 10 of the backend README](backend/README.md) for the full walkthrough
and the four values Render will prompt for.

---

## Credits

Datasets: [Pothole](https://universe.roboflow.com/siva-ragampudi/pothole-vhmow-jwwzq)
and [Road](https://universe.roboflow.com/siva-ragampudi/road-c013o-tlkm7) on
Roboflow Universe, CC BY 4.0. Detection by
[Ultralytics YOLO11](https://github.com/ultralytics/ultralytics) (AGPL-3.0).
Map tiles © OpenStreetMap contributors.
