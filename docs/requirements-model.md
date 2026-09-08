# What we need from you — the detection model

You are replacing `backend/weights/best.pt`. Nothing else in the project
changes, so this is a short list. Full technical detail is in
[`INTEGRATION.md`](../INTEGRATION.md) if you want it.

---

## Deliver these six things

### 1. The checkpoint — `best.pt`

An **Ultralytics** checkpoint. YOLO11 or YOLOv8, any size, any architecture
ultralytics can load.

It must be an **object-detection** model. Not segmentation, not
classification. Please check this before sending — read the warning at the
bottom of this page, because this failure does not look like a failure.

Under ~100 MB, or tell us and we will set up Git LFS.

### 2. Your class names

The exact list, as it appears in `model.names`. Send it as text, e.g.

```
['pothole', 'crack', 'rut']
```

**Use descriptive names.** The backend matches on the class *name*, not the
index, to decide how hazardous a defect is and what repair to recommend — and
the name is printed in a PDF addressed to the Greater Hyderabad Municipal
Corporation.

These work as-is: `pothole`, `crack`, `rut`, `depression`, `ravel`, `manhole`,
`alligator`, `patch`. Substrings count, so `D40_Pothole` and `alligator_crack`
are both fine.

These will run but degrade the output: `class_0`, `damage`, `defect`, `D00`.
Every such defect gets a default hazard weight, generic repair advice, and an
unreadable label in the report. If your names look like this, either rename
them in the checkpoint or tell us the mapping and we will add them to
`app/config.py`.

### 3. Metrics on the held-out **test** split

| | |
|---|---|
| mAP50 | |
| mAP50-95 | |
| Precision | |
| Recall | |
| Per-class mAP50 | |

**Test split, not validation.** Validation numbers are what the training loop
selected the best epoch against, so they systematically overstate the model.
Ours are on test, and mixing the two makes the comparison meaningless.

If you did not hold out a test split, say so — that is fixable, but we need to
know rather than find out in the viva.

### 4. Your training configuration

- Base weights you started from (e.g. `yolo11n.pt`)
- **`imgsz`** — the image size you trained at. This one matters: a model
  trained at 640 and served at 1280 quietly gets worse, and we need to set
  `INFERENCE_IMAGE_SIZE` to match.
- Epochs, batch size, and where it ran (Colab T4, local GPU, …)
- Confidence and IoU thresholds you found best, if you tuned them

### 5. Dataset provenance

- Where the images came from, with links if public
- **Licence** — this goes in the project credits
- Image counts per split: train / valid / test
- Class balance, roughly. An 800/40 split across two classes is worth knowing
  about before someone asks why recall on the rare class is poor.

### 6. The training notebook or command

So the result can be reproduced. A `.ipynb` or the `yolo train ...` line is
enough.

---

## How we will check it

```bash
cp your_best.pt backend/weights/best.pt
python3 tools/check_model.py        # loads it, prints classes and inference time
uvicorn app.main:app --reload       # expect: status=trained | classes=[...]
```

Then a real photograph of a real defect through the app, and we look at the
annotated image that comes back.

**Pass:** boxes land on the defects, class names read sensibly, and the health
score reflects the damage.

---

## The one failure to check for before you send it

A model that loads but detects nothing produces a road health score of
**100.00** and a confident "Good" report about a visibly broken road.

Nothing errors. No warning appears. The PDF looks perfect and is completely
wrong — and it is addressed to a municipal body.

This is what happens if the model is segmentation rather than detection, or if
the confidence threshold is far too high, or if the classes do not match what
the images actually contain. **Please run at least five photographs with
obvious potholes through your model and confirm it finds them** before handing
it over. That single check catches all three causes.
