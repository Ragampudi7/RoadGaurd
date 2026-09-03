# Where your trained model goes

Put your trained YOLO weights file in **this folder** and name it `best.pt`:

```
backend/weights/best.pt
```

That is the only step needed - `MODEL_PATH=weights/best.pt` is the default, the
backend picks the file up on the next start, and the fallback model is skipped
automatically.

After you train with Ultralytics, the file you want is:

```
runs/detect/train/weights/best.pt   ->  copy to  backend/weights/best.pt
```

Notes:

* A different filename or location is fine - set `MODEL_PATH` in `.env`
  (relative paths are resolved from the `backend/` folder).
* `*.pt` files are gitignored because they are usually 5-50 MB. To deploy on
  Render either commit the file with Git LFS, or download it in `build.sh`
  from a public URL (for example a GitHub Release asset).
* Once your real weights are in place, set `ALLOW_PRETRAINED_FALLBACK=false`
  so the server never silently serves demonstration results.
* See `../TRAINING.md` for how to produce `best.pt`.
