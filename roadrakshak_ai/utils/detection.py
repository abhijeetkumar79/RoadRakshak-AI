"""
RoadRakshak AI — Road Damage Detection Module
==============================================

Two modes, selected automatically:

1. TRAINED MODEL MODE
   If a custom-trained YOLOv8 weights file exists at model/best.pt
   (see COLAB_TRAINING_GUIDE.md for how to train one), it is loaded via
   the `ultralytics` package and used for real detection of
   pothole / crack / waterlogging / etc.

2. HEURISTIC DEMO MODE (fallback, zero extra downloads required)
   If no trained model is present, or ultralytics isn't installed,
   the app falls back to a classical OpenCV heuristic (edge density +
   dark-blob analysis) so the whole pipeline still runs end-to-end for
   a demo. Results in this mode are clearly labelled "Heuristic Demo
   Mode" in the UI — they are NOT a substitute for a trained model and
   should not be presented to judges/users as production-grade CV.

Both modes return the same output shape so the rest of the app doesn't
need to know which one is active.
"""
import os
import cv2
import numpy as np
from functools import lru_cache

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model", "best.pt")

CLASS_NAMES = ["Pothole", "Road Crack", "Waterlogging", "Broken Road", "Landslide"]

BOX_COLOR = {
    "Pothole": (60, 60, 255),
    "Road Crack": (0, 200, 255),
    "Waterlogging": (255, 180, 0),
    "Broken Road": (255, 60, 180),
    "Landslide": (120, 60, 255),
}


@lru_cache(maxsize=1)
def _load_yolo_model():
    """Try to load a custom-trained YOLOv8 model. Returns None if unavailable."""
    if not os.path.exists(MODEL_PATH):
        return None
    try:
        from ultralytics import YOLO
        return YOLO(MODEL_PATH)
    except Exception:
        return None


def model_status() -> str:
    """Human-readable status string for the sidebar / UI."""
    model = _load_yolo_model()
    if model is not None:
        return "✅ Custom trained YOLO model loaded (model/best.pt)"
    return "⚠️ Heuristic Demo Mode — no trained model found at model/best.pt (see COLAB_TRAINING_GUIDE.md)"


def _heuristic_detect(bgr_image: np.ndarray, issue_hint: str = None):
    """
    Classical CV fallback: estimates 'damage-like' regions using edge density
    and dark irregular blobs (common visual signature of potholes / cracks /
    patched or broken asphalt in road-level photos). This is a DEMO heuristic,
    not a trained detector — accuracy will be modest and it should be
    presented as such.
    """
    img = bgr_image.copy()
    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(gray, 40, 130)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    # Dark irregular regions (pothole shadows / wet patches)
    _, dark_mask = cv2.threshold(gray, 70, 255, cv2.THRESH_BINARY_INV)
    dark_mask = cv2.morphologyEx(dark_mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))

    combined = cv2.bitwise_or(edges, dark_mask)
    contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    detections = []
    total_area = 0
    min_area = (h * w) * 0.0025

    for c in sorted(contours, key=cv2.contourArea, reverse=True)[:8]:
        area = cv2.contourArea(c)
        if area < min_area:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        aspect = bw / float(bh + 1e-5)

        # crude class guess from shape hints (demo-level heuristic only)
        if issue_hint and issue_hint != "Other":
            label = issue_hint
        elif aspect > 2.5:
            label = "Road Crack"
        else:
            label = "Pothole"

        conf = float(np.clip(0.45 + (area / (h * w)) * 3.0, 0.35, 0.93))
        detections.append({"label": label, "confidence": round(conf, 2), "bbox": (x, y, x + bw, y + bh)})
        total_area += area

    damage_ratio = min(total_area / float(h * w), 1.0)
    annotated = _draw_boxes(img, detections)
    return detections, annotated, damage_ratio


def _yolo_detect(model, bgr_image: np.ndarray):
    results = model.predict(source=bgr_image, verbose=False, conf=0.25)
    detections = []
    h, w = bgr_image.shape[:2]
    total_area = 0
    r = results[0]
    names = r.names if hasattr(r, "names") else {i: n for i, n in enumerate(CLASS_NAMES)}
    for box in r.boxes:
        x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
        conf = float(box.conf[0])
        cls_id = int(box.cls[0])
        label = names.get(cls_id, f"class_{cls_id}")
        detections.append({"label": label, "confidence": round(conf, 2), "bbox": (x1, y1, x2, y2)})
        total_area += max(0, (x2 - x1)) * max(0, (y2 - y1))
    damage_ratio = min(total_area / float(h * w), 1.0)
    annotated = _draw_boxes(bgr_image.copy(), detections)
    return detections, annotated, damage_ratio


def _draw_boxes(img, detections):
    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        color = BOX_COLOR.get(d["label"], (0, 229, 255))
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        label_text = f"{d['label']} {d['confidence']:.2f}"
        (tw, th), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
        cv2.rectangle(img, (x1, max(0, y1 - th - 10)), (x1 + tw + 8, y1), color, -1)
        cv2.putText(img, label_text, (x1 + 4, max(12, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    return img


def analyze_image(bgr_image: np.ndarray, issue_hint: str = None):
    """
    Main entry point used by the app.

    Returns dict:
        detections: list of {label, confidence, bbox}
        annotated_image: BGR numpy array with boxes drawn
        damage_ratio: 0-1 float, fraction of frame covered by detected damage
        mode: 'trained_model' | 'heuristic_demo'
        top_label: best-guess primary damage type (or issue_hint if none found)
        top_confidence: confidence of the top detection (0 if none)
    """
    model = _load_yolo_model()
    if model is not None:
        detections, annotated, damage_ratio = _yolo_detect(model, bgr_image)
        mode = "trained_model"
    else:
        detections, annotated, damage_ratio = _heuristic_detect(bgr_image, issue_hint)
        mode = "heuristic_demo"

    if detections:
        top = max(detections, key=lambda d: d["confidence"])
        top_label, top_confidence = top["label"], top["confidence"]
    else:
        top_label, top_confidence = (issue_hint or "Other"), 0.0

    return {
        "detections": detections,
        "annotated_image": annotated,
        "damage_ratio": damage_ratio,
        "mode": mode,
        "top_label": top_label,
        "top_confidence": top_confidence,
    }
