# Producing `weights/best.pt`

The backend does not care how the model was trained - it only needs an
Ultralytics-compatible `.pt` detection model. This file is the shortest path
from "no model" to "a model the API can serve".

Train on a machine with a GPU (Google Colab's free tier is enough for a nano
model). **Inference** then runs fine on CPU, which is what the deployed backend
does.

---

## 1. Get a dataset

You need road images with **bounding-box** labels (not segmentation masks).
Well-known public options - search for these by name rather than trusting a
pasted link, since hosting moves around:

| Dataset | Notes |
|---|---|
| **RDD2022** (Road Damage Detection, Arya et al.) | ~47k images from several countries. Classes `D00` longitudinal crack, `D10` transverse crack, `D20` alligator crack, `D40` pothole. The most academically citable option - good for a project report. |
| **Roboflow Universe** - search "pothole" / "road damage" | Many community datasets, already in YOLO format, one-click export. Fastest way to start. Check the licence and the label quality before you rely on one. |
| **Kaggle** - search "pothole detection" | Mixed quality; several are usable after cleaning. |

For a college project, **2 or 3 classes is plenty** - `pothole` and `crack` is a
perfectly defensible scope, and a small clean dataset beats a large noisy one.
Whatever you choose, write down the dataset name, size, class list and licence:
that paragraph belongs in your report.

## 2. Put it in YOLO format

```
dataset/
├── data.yaml
├── train/
│   ├── images/   img001.jpg ...
│   └── labels/   img001.txt ...
└── valid/
    ├── images/
    └── labels/
```

Each label file has one line per object, coordinates **normalised to 0-1**:

```
<class_id> <x_center> <y_center> <width> <height>
0 0.4812 0.6530 0.2250 0.2700
```

`data.yaml`:

```yaml
path: /content/dataset
train: train/images
val: valid/images

names:
  0: pothole
  1: crack
```

The names you write here are exactly the strings that appear in the API's
`class_name`, in the PDF's defect table and on the annotated image - so use
lowercase, human-readable words. `pothole` renders as "Pothole",
`alligator_crack` renders as "Alligator Crack".

## 3. Train

```bash
pip install ultralytics

yolo detect train \
  model=yolov8n.pt \
  data=/content/dataset/data.yaml \
  epochs=100 \
  imgsz=640 \
  batch=16 \
  patience=20 \
  project=road_health \
  name=v1
```

Or the equivalent in Python:

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")          # or "yolo11n.pt"
model.train(data="dataset/data.yaml", epochs=100, imgsz=640, batch=16, patience=20)
```

Notes that matter for this project:

* **Use a nano model** (`yolov8n.pt` or `yolo11n.pt`). `s`/`m`/`l` variants are
  more accurate but will not fit comfortably in 512 MB of RAM on Render's free
  tier, and CPU inference gets several times slower.
* Start from the pretrained checkpoint (transfer learning). Training from
  scratch on a small dataset gives much worse results.
* `imgsz=640` should match `INFERENCE_IMAGE_SIZE` in the backend.
* 100 epochs on a few thousand images is roughly 1-2 hours on a Colab T4.

## 4. Check the result

```bash
yolo detect val model=road_health/v1/weights/best.pt data=/content/dataset/data.yaml
```

Record **mAP50**, **mAP50-95**, precision and recall per class - your report
needs them. For a nano model on a modest pothole dataset, mAP50 in the 0.5-0.7
range is a normal, honest result. Do not expect (or claim) 0.95.

## 5. Install it

```bash
cp road_health/v1/weights/best.pt  backend/weights/best.pt
```

Then, in `backend/.env`:

```env
ALLOW_PRETRAINED_FALLBACK=false
```

Restart the server and confirm:

```bash
python tools/check_model.py
curl http://localhost:8000/health
```

`model.status` must read `"trained"` and `is_road_defect_model` must be `true`.
Any report generated before that point is demonstration output and is watermarked
as such.

## 6. Tuning after deployment

You do not need to retrain to adjust behaviour:

* too many false detections -> raise `CONFIDENCE_THRESHOLD` (`0.35`, `0.45`)
* real potholes being missed -> lower it (`0.15`, `0.20`)
* the same pothole detected as several overlapping boxes -> lower `IOU_THRESHOLD`
  so non-maximum suppression merges them more aggressively, and/or set
  `AREA_METHOD=union` so the duplicates stop inflating the damage percentage
* inference too slow on Render -> `INFERENCE_IMAGE_SIZE=512` or `416`

### Teaching the risk model about your classes

The risk model keys off class *names*, so once you know your final label list,
spend five minutes in `app/config.py`:

* `DEFECT_CLASS_WEIGHTS` - how hazardous each class is relative to a pothole
  (1.00). Keys are matched as substrings, so `pothole` already covers
  `D40_pothole`. Add anything your model emits that is not in the list, or it
  silently takes `DEFAULT_CLASS_WEIGHT`.
* `RECOMMENDED_ACTIONS` - the remediation wording printed in the inventory
  table. Three families ship (`pothole`, `crack`, `default`); add more if your
  classes need them, and check with a civil-engineering reference before you
  put specific wording in front of a municipal body.
* `DEFECT_SEVERITY_BANDS` - the box-area cut-offs. If your photographs are shot
  much closer or much further away than the ones these bands were tuned on,
  every defect will land in the wrong band; take twenty representative photos,
  look at the reported `area_percentage` values, and move the cut-offs.

The risk weights and full scales are environment variables
(`RISK_WEIGHT_*`, `RISK_*_FULL_SCALE`), so you can tune those from `.env`
without editing code.
