# 🧠 Training Your Own Road Damage Detection Model on Google Colab

This guide walks you through training a custom YOLOv8 model to detect
**potholes, cracks, waterlogging, broken road, and landslide/debris** —
free, using Google Colab's GPU. At the end you'll have a `best.pt` file
to drop into `model/best.pt` in this project.

Total time: roughly 1–3 hours depending on dataset size and epochs.

---

## Step 1 — Get a dataset

You have three good free options. Pick one (or combine a couple with Roboflow):

1. **Roboflow Universe — "Pothole Detection"** datasets (several public
   ones, already labelled in YOLO format, some multi-class with cracks).
   Search: https://universe.roboflow.com/search?q=pothole
2. **Kaggle — "Pothole Detection Dataset"** (raw images; you'll need to
   annotate boxes yourself or use Roboflow's auto-label tools).
3. **Your own photos** — take road photos around your pilot city (e.g.
   Dehradun) with a phone and annotate them. Even 200–400 well-labelled
   images per class produces a usable demo model.

**Recommended path (fastest):** create a free Roboflow account, either
fork an existing pothole/crack dataset or upload your own images, draw
bounding boxes in Roboflow's annotation tool, then **Export → YOLOv8** —
Roboflow gives you a ready-to-use code snippet that downloads the dataset
straight into Colab.

Your exported dataset must produce a `data.yaml` that looks like:

```yaml
train: ../train/images
val: ../valid/images
nc: 5
names: ['Pothole', 'Road Crack', 'Waterlogging', 'Broken Road', 'Landslide']
```

(If your source dataset only has "pothole" and "crack", that's fine — just
update `CLASS_NAMES` in `utils/detection.py` to match whatever classes you
actually train, in the same order as `data.yaml`.)

---

## Step 2 — Open a new Google Colab notebook

Go to https://colab.research.google.com → **New Notebook**, then:

`Runtime → Change runtime type → Hardware accelerator → GPU (T4)`

---

## Step 3 — Install Ultralytics YOLOv8

In the first cell:

```python
!pip install ultralytics -q
import ultralytics
ultralytics.checks()
```

This confirms GPU is detected (it will print `CUDA:0` details).

---

## Step 4 — Bring in your dataset

**If using Roboflow:**

```python
!pip install roboflow -q
from roboflow import Roboflow
rf = Roboflow(api_key="YOUR_ROBOFLOW_API_KEY")
project = rf.workspace("your-workspace").project("your-pothole-project")
dataset = project.version(1).download("yolov8")
```

**If using your own zipped dataset**, upload it via the Colab file panel
(left sidebar → folder icon → upload), then:

```python
!unzip -q /content/your_dataset.zip -d /content/dataset
```

Make sure the extracted folder has `train/`, `valid/`, and `data.yaml`.

---

## Step 5 — Train the model

```python
from ultralytics import YOLO

model = YOLO("yolov8n.pt")  # start from a small pretrained model (fast, good for demos)

model.train(
    data="/content/dataset/data.yaml",   # path to your data.yaml
    epochs=60,
    imgsz=640,
    batch=16,
    patience=15,
    project="roadrakshak_training",
    name="run1",
)
```

Notes:
- `yolov8n.pt` (nano) trains fastest and is plenty for a hackathon/SIH
  demo. For higher accuracy later, try `yolov8s.pt` or `yolov8m.pt`.
- If you get a CUDA out-of-memory error, lower `batch` to 8 or `imgsz` to 512.
- Training progress (loss curves, mAP) prints per epoch and is also saved
  as plots inside the run folder.

---

## Step 6 — Evaluate

```python
metrics = model.val()
print(metrics.box.map)     # mAP50-95
print(metrics.box.map50)   # mAP50
```

Also check `roadrakshak_training/run1/confusion_matrix.png` and
`results.png` (auto-generated) to see per-class performance.

---

## Step 7 — Quick test on a sample image

```python
results = model("/content/dataset/valid/images/some_test_image.jpg")
results[0].show()
```

---

## Step 8 — Download your trained weights

Your best-performing checkpoint is saved at:

```
roadrakshak_training/run1/weights/best.pt
```

Download it:

```python
from google.colab import files
files.download("roadrakshak_training/run1/weights/best.pt")
```

---

## Step 9 — Plug it into RoadRakshak AI

1. Rename the downloaded file to `best.pt` if it isn't already.
2. Copy it into this project at: `model/best.pt`
3. If your class names/order differ from the default, update
   `CLASS_NAMES` in `utils/detection.py` to match your `data.yaml`.
4. Restart the Streamlit app — the sidebar will now show
   **"✅ Custom trained YOLO model loaded"** instead of Heuristic Demo Mode.

---

## Tips for a stronger SIH/hackathon model

- **Balance your classes** — if you have 800 pothole images but only 40
  waterlogging images, the model will be much worse at waterlogging.
  Aim for at least 150–200 images per class.
- **Augment your data** — Roboflow's export step offers free augmentation
  (brightness/rotation/blur) which helps a lot with a small dataset.
- **Mix conditions** — include photos in daylight, overcast, wet roads,
  and shadows so the model generalizes beyond "sunny demo day" photos.
- **Re-train iteratively** — run the app, collect a few real misclassified
  photos, add them to your dataset with correct labels, and retrain. This
  "collect → correct → retrain" loop is exactly the story to tell judges
  about how the system will keep improving in production.
- **Don't over-promise** — be upfront (as this project's docs are) that
  automatic accident detection from citizen photos isn't reliable; frame
  accidents as citizen-reported-and-verified in the MVP, with CCTV/dashcam
  computer-vision detection as a clearly-labelled future roadmap item.
