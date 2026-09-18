# 🛣️ RoadRakshak AI

**Intelligent Road Damage, Accident & Alert Management System**
*Detect. Report. Alert. Repair.*

An AI-powered, dark-themed Streamlit platform for road damage monitoring —
piloted on Dehradun's road network, architected to scale pan-India.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🛰️ Satellite Map + Search | Search any Indian location, switch between Normal / Satellite / Risk map layers, click to pin the exact road spot |
| 🤖 AI Damage Detection | Upload a photo → pothole / crack / waterlogging / landslide / broken-road classification, confidence & risk score |
| 📸 Live Webcam Detection | Real-time browser-based webcam detection with on-frame overlay (boxes, confidence, pavement condition score) |
| 📍 Point & Report | Report an issue anywhere without being physically present |
| 🩺 Road Health Score | Aggregated 0–100 health score per road from all its open reports |
| ♻️ Duplicate Detection | Reports within ~60m of an existing open issue are merged, not duplicated |
| 🏛️ Authority Dashboard | Auto-prioritised repair queue, status workflow, before/after photo verification |
| ⭐ Citizen Verification | "Was this actually repaired?" — flags repairs citizens dispute |
| 🤖 AI Assistant | Chat interface answering questions grounded in the live report database |
| 📄 Professional PDF Reports | One-click branded PDF export for authorities |

---

## 🗂️ Project Structure

```
roadrakshak_ai/
├── app.py                          # Home page (run this with streamlit)
├── pages/
│   ├── 1_🗺️_Map_and_Report.py
│   ├── 2_📸_Live_Detection.py
│   ├── 3_🏛️_Authority_Dashboard.py
│   ├── 4_🤖_AI_Assistant.py
│   └── 5_📄_Reports.py
├── utils/
│   ├── db.py                       # SQLite storage layer
│   ├── detection.py                # YOLO model + OpenCV heuristic fallback
│   ├── risk.py                     # Severity / risk score / priority logic
│   ├── geo.py                      # Geocoding + distance helpers
│   ├── chatbot.py                  # AI assistant (rule-based + optional LLM)
│   ├── report_pdf.py               # Professional PDF generator
│   ├── seed_data.py                # Demo data seeding (Dehradun pilot)
│   └── ui.py                       # Shared dark-theme UI components
├── assets/style.css                # Dark animated theme
├── model/                          # Put your trained best.pt here
├── data/                           # SQLite DB lives here (auto-created)
├── .streamlit/config.toml          # Dark theme config
├── requirements.txt
├── COLAB_TRAINING_GUIDE.md         # Train your own YOLO model, free, on Colab
└── README.md
```

---

## 🚀 Quick Start

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. Demo data for six Dehradun
roads is seeded automatically on first run so every page has something
to show immediately.

---

## 🧠 About the AI Detection

Out of the box, the app runs in **Heuristic Demo Mode** — a lightweight
OpenCV-based estimator (edge density + dark-blob analysis) that lets the
*entire pipeline* (upload → detect → risk score → map → dashboard → PDF)
work end-to-end with zero setup. It is intentionally labelled in the UI as
a demo heuristic, not a production detector.

For real detection accuracy, train a YOLOv8 model on a pothole/crack
dataset — it's free on Google Colab and takes about an hour. Full
step-by-step instructions are in **[`COLAB_TRAINING_GUIDE.md`](COLAB_TRAINING_GUIDE.md)**.
Once you drop the resulting `best.pt` into `model/best.pt`, the app
automatically switches to **Trained Model Mode**.

---

## 🤖 AI Assistant

The AI Assistant page answers questions like *"what are the highest risk
roads?"* using a rule-based engine grounded in your live database — no
API key required. If you set an `ANTHROPIC_API_KEY` environment variable
(and have the `anthropic` package installed, already in requirements.txt),
free-form questions are additionally routed to Claude, always grounded in
a summary of your current report data so it never invents numbers.

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # optional
```

---

## 📸 Live Webcam Detection

Uses `streamlit-webrtc` for real, continuous, browser-based webcam
detection (works when deployed, not just localhost) with an on-frame
overlay similar to commercial road-scanning dashboards. If the webcam
packages aren't available, the page automatically falls back to a
single-shot "Take Photo" mode using Streamlit's built-in camera input.

---

## 👥 Suggested Team Split (for a 3-person hackathon team)

- **AI / Data Science:** `utils/detection.py`, model training (Colab
  guide), `utils/risk.py`, dashboard analytics.
- **Frontend / Maps:** `pages/1_🗺️_Map_and_Report.py`, `assets/style.css`,
  overall UI polish.
- **Backend:** `utils/db.py`, alert/duplicate logic, `pages/3_🏛️_Authority_Dashboard.py`.

---

## ⚠️ Honest Scope Notes

- **Accidents** are citizen-reported → verified → alerted in this MVP.
  Automatic accident detection from CCTV/dashcam feeds is a real,
  clearly-labelled future roadmap item, not something claimed here.
- **Satellite imagery** is used for location context and large-scale
  disaster damage — not for detecting individual potholes, which isn't
  realistic at typical satellite resolution. Ground-level photo/video +
  computer vision handles pothole-level detection.
- **Heuristic Demo Mode** detection accuracy is intentionally modest and
  clearly labelled — it exists so the full pipeline runs before you've
  trained a model, not as a claim of production-grade CV.

---

## 📦 Tech Stack

Streamlit · Folium / streamlit-folium · Geopy · OpenCV · Ultralytics
YOLOv8 (optional trained model) · Plotly · ReportLab · streamlit-webrtc ·
SQLite
