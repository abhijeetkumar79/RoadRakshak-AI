# `model/` — Trained Detection Weights

Place your custom-trained YOLOv8 weights file here, named exactly:

```
model/best.pt
```

Once this file exists, `utils/detection.py` will automatically switch from
**Heuristic Demo Mode** (a lightweight OpenCV fallback, no training required)
to **Trained Model Mode** and use your model for real pothole / crack /
waterlogging / landslide / broken-road detection.

## Class order

Train your model with these five classes, in this order, so labels line up
with the rest of the app (`utils/detection.py::CLASS_NAMES`):

```
0: Pothole
1: Road Crack
2: Waterlogging
3: Broken Road
4: Landslide
```

You can rename/reorder classes, but if you do, update `CLASS_NAMES` in
`utils/detection.py` to match your `data.yaml`.

See **`COLAB_TRAINING_GUIDE.md`** in the project root for full step-by-step
instructions on training this model for free on Google Colab.
