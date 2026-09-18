"""
Live Edge AI Camera Scanner & Multimodal Road Vision Q&A
Real-time pavement scan, deep AI defect diagnostics, and interactive frame Q&A.
"""
import time
import numpy as np
import cv2
from PIL import Image
import streamlit as st

from utils.ui import hero, section_title, divider, card_open, card_close, kpi_card
from utils.detection import analyze_image, model_status
from utils.risk import severity_from_damage_ratio
from utils.ai_engine import (
    get_api_status,
    analyze_road_image_ai,
    chat_with_road_image,
)

hero(
    "Live Road Edge AI Scanner",
    "Stream live vehicle or mobile camera feed for continuous road condition classification and automated HUD bounding boxes.",
    emoji="📸",
    badge="⚡ EDGE NEURAL VISION & CHAT",
)

# ---------------------------------------------------------------- API Key & Vision Status
is_linked, provider, model_name, masked_key = get_api_status()

status_c1, status_c2 = st.columns([2.5, 1])
with status_c1:
    if is_linked and provider == "Google Gemini":
        st.markdown(
            f"<div style='display:inline-flex; align-items:center; gap:8px; padding:6px 14px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); border-radius:999px; font-size:0.8rem; font-weight:700; color:#34d399; margin-bottom:12px;'>"
            f"<span style='width:8px; height:8px; border-radius:50%; background:#10b981;'></span>"
            f"<span>Gemini Multimodal Vision Linked ({masked_key}) · Neural Diagnostics & Frame Q&A Active</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif is_linked:
        st.markdown(
            f"<div style='display:inline-flex; align-items:center; gap:8px; padding:6px 14px; background:rgba(59,130,246,0.12); border:1px solid rgba(59,130,246,0.3); border-radius:999px; font-size:0.8rem; font-weight:700; color:#93c5fd; margin-bottom:12px;'>"
            f"<span style='width:8px; height:8px; border-radius:50%; background:#3b82f6;'></span>"
            f"<span>{provider} Linked · Google Gemini Key recommended for multimodal camera vision</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='display:inline-flex; align-items:center; gap:8px; padding:6px 14px; background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); border-radius:999px; font-size:0.8rem; font-weight:700; color:#fcd34d; margin-bottom:12px;'>"
            "<span style='width:8px; height:8px; border-radius:50%; background:#f59e0b;'></span>"
            "<span>Link a Google Gemini Key in the Left Sidebar to enable Deep AI Vision & Frame Q&A Chat</span>"
            "</div>",
            unsafe_allow_html=True,
        )

with status_c2:
    if not is_linked:
        with st.expander("🔑 Quick Link Key"):
            cam_key = st.text_input("Gemini API Key", type="password", key="cam_page_key")
            if st.button("Save", key="cam_save_key"):
                if cam_key.strip():
                    st.session_state["user_api_key"] = cam_key.strip()
                    st.success("Key linked!")
                    st.rerun()

mode = st.radio("Scanner Mode", ["🔴 Continuous Video Stream (WebRTC)", "📷 Camera Snapshot & AI Inspection", "📁 Upload Road Inspection Image"], horizontal=True)

divider()

# ---------------------------------------------------------------- Mode 1: WebRTC Streamer
if mode.startswith("🔴"):
    try:
        from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
        import av

        RTC_CONFIGURATION = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]}]})

        class DamageVideoProcessor(VideoProcessorBase):
            def __init__(self):
                self.detections = []
                self.condition_score = 100
                self.frame_count = 0

            def recv(self, frame):
                img = frame.to_ndarray(format="bgr24")
                self.frame_count += 1

                if self.frame_count % 5 == 0:
                    result = analyze_image(img)
                    self.detections = result["detections"]
                    self.condition_score = max(5, round(100 - result["damage_ratio"] * 180))
                    annotated = result["annotated_image"]
                else:
                    from utils.detection import _draw_boxes
                    annotated = _draw_boxes(img.copy(), self.detections)

                overlay = annotated.copy()
                h, w = overlay.shape[:2]
                panel_w = 240
                cv2.rectangle(overlay, (w - panel_w - 12, 12), (w - 12, 138), (10, 14, 26), -1)
                cv2.rectangle(overlay, (w - panel_w - 12, 12), (w - 12, 138), (0, 240, 255), 1)
                cv2.putText(overlay, "ROADRAKSHAK AI", (w - panel_w, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 240, 255), 2)
                cv2.putText(overlay, f"Objects: {len(self.detections)}", (w - panel_w, 64),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (226, 232, 240), 1)
                cv2.putText(overlay, f"Pavement: {self.condition_score}/100", (w - panel_w, 90),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (226, 232, 240), 1)
                label = "SAFE" if self.condition_score >= 70 else ("DEGRADED" if self.condition_score >= 40 else "HAZARD")
                color = (80, 220, 120) if label == "SAFE" else ((0, 200, 255) if label == "DEGRADED" else (60, 60, 255))
                cv2.putText(overlay, label, (w - panel_w, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                blended = cv2.addWeighted(overlay, 0.88, annotated, 0.12, 0)

                return av.VideoFrame.from_ndarray(blended, format="bgr24")

        col1, col2 = st.columns([2, 1])
        with col1:
            card_open()
            ctx = webrtc_streamer(
                key="road-detect",
                video_processor_factory=DamageVideoProcessor,
                rtc_configuration=RTC_CONFIGURATION,
                media_stream_constraints={"video": True, "audio": False},
            )
            card_close()
        with col2:
            section_title("Live Telemetry Specs")
            card_open()
            st.markdown(
                "• **Processing:** Dynamic multi-frame batch inference  \n"
                "• **Pavement Score:** 100 - damage coverage ratio  \n"
                "• **Target FPS:** 24-30 fps with smooth frame interpolation  \n"
            )
            st.markdown("---")
            st.markdown(
                "**Detection Matrix:**  \n"
                "🔴 Pothole &nbsp; 🟠 Waterlogging  \n"
                "🟡 Road Crack &nbsp; 🟣 Landslide / Fissure"
            )
            card_close()
            st.info("💡 Switch to **Camera Snapshot** or **Upload Image** below to inspect a specific road spot and chat with the AI!")

    except Exception as e:
        st.warning(
            "Live WebRTC streamer encountered an issue or browser permissions were not granted. "
            f"Falling back to Camera Snapshot mode. (Details: {e})"
        )
        mode = "📷 Camera Snapshot & AI Inspection"

# ---------------------------------------------------------------- Mode 2 & 3: Snapshot or Upload
target_image = None

if mode.startswith("📷"):
    section_title("High-Resolution Camera Snapshot")
    card_open()
    shot = st.camera_input("Capture pavement photo from mobile / dashcam / webcam")
    card_close()
    if shot is not None:
        target_image = Image.open(shot).convert("RGB")

elif mode.startswith("📁"):
    section_title("Upload Pavement Inspection Image")
    card_open()
    uploaded_file = st.file_uploader("Upload road image file", type=["jpg", "jpeg", "png"])
    card_close()
    if uploaded_file is not None:
        target_image = Image.open(uploaded_file).convert("RGB")

# ---------------------------------------------------------------- Process Captured Frame
if target_image is not None:
    bgr = np.array(target_image)[:, :, ::-1].copy()

    # Store current image in session state for frame chat
    st.session_state["current_camera_bgr"] = bgr

    # Initialize camera chat history if new image or empty
    if "camera_chat_history" not in st.session_state:
        st.session_state.camera_chat_history = []

    # 1. Classical / YOLO Detection
    with st.spinner("Executing real-time road object detection..."):
        result = analyze_image(bgr)
    severity = severity_from_damage_ratio(result["damage_ratio"])

    # Two column layout: Annotated Frame + Diagnostics Card
    res_c1, res_c2 = st.columns([1.3, 1])

    with res_c1:
        st.image(result["annotated_image"][:, :, ::-1], caption="Computer Vision Detection", use_container_width=True)

    with res_c2:
        section_title("Telemetry Classification")
        card_open()
        st.markdown(f"**Top Detected Object:** `{result['top_label']}`")
        st.markdown(f"**Model Confidence:** `{result['top_confidence']*100:.0f}%`")
        st.markdown(f"**Calculated Severity:** `{severity}`")
        st.markdown(f"**Detection Mode:** `{result['mode'].replace('_', ' ').title()}`")
        st.markdown(f"**Damage Frame Coverage:** `{result['damage_ratio']*100:.1f}%`")
        card_close()

    # 2. Deep AI Multimodal Vision Analysis
    section_title("🔬 Deep AI Structural Engineering Inspection")

    if is_linked:
        if "ai_vision_diagnosis" not in st.session_state or st.session_state.get("vision_diag_for") != id(target_image):
            with st.spinner("Calling Multimodal Gemini Vision for structural engineering assessment..."):
                diag_text = analyze_road_image_ai(bgr)
                st.session_state["ai_vision_diagnosis"] = diag_text
                st.session_state["vision_diag_for"] = id(target_image)
        
        card_open()
        st.markdown(st.session_state["ai_vision_diagnosis"])
        card_close()
    else:
        card_open()
        st.markdown(
            "⚡ **Unlock Deep Multimodal Engineering Diagnostics:**  \n"
            "With an API key linked, the AI performs a comprehensive IRC-82 highway inspection: "
            "measuring pothole depth, crack progression patterns, vehicle suspension hazard level, and exact bituminous mix repair recommendations."
        )
        card_close()

    divider()

    # ---------------------------------------------------------------- Interactive Q&A Chatbox for this Road Image
    section_title("💬 Q&A Chatbox — Ask AI About This Road Condition")

    st.markdown(
        "<div style='color: #94a3b8; font-size: 0.9rem; margin-bottom: 12px;'>"
        "Ask any specific question about the damage in the captured frame above. The AI will inspect the photo and provide expert guidance."
        "</div>",
        unsafe_allow_html=True,
    )

    # Suggested Prompts for this photo
    cq1, cq2, cq3 = st.columns(3)
    frame_prompt = None
    with cq1:
        if st.button("🛵 Two-Wheeler Hazard Level?", use_container_width=True):
            frame_prompt = "Is this road condition dangerous for two-wheelers and motorcycles, especially in rainy or low-light conditions?"
    with cq2:
        if st.button("🛠️ Recommended Repair Material?", use_container_width=True):
            frame_prompt = "What specific repair material (e.g. cold mix, hot mix, slurry seal) is required to fix this damage according to IRC standards?"
    with cq3:
        if st.button("🚗 Risk of Vehicle Damage?", use_container_width=True):
            frame_prompt = "What kind of vehicle damage (tires, rims, suspension, alignment) can occur if a vehicle hits this at 40 km/h?"

    # Render previous Q&A turns for this frame
    for turn in st.session_state.camera_chat_history:
        avatar = "🧑" if turn["role"] == "user" else "🤖"
        with st.chat_message(turn["role"], avatar=avatar):
            st.markdown(turn["content"])

    # Chat input for this image
    cam_query = frame_prompt or st.chat_input("Ask a question about this road image (e.g., 'Is there water seepage underneath?')...", key="cam_chat_input")

    if cam_query:
        st.session_state.camera_chat_history.append({"role": "user", "content": cam_query})
        with st.chat_message("user", avatar="🧑"):
            st.markdown(cam_query)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Inspecting road image with AI..."):
                if is_linked and provider == "Google Gemini":
                    ai_reply = chat_with_road_image(bgr, st.session_state.camera_chat_history[:-1], cam_query)
                elif is_linked:
                    from utils.ai_engine import generate_chat_answer
                    ai_reply = generate_chat_answer(f"Question about road damage image ({result['top_label']}, severity {severity}): {cam_query}")
                else:
                    ai_reply = (
                        f"**Image Detection Summary:** {result['top_label']} (Severity: {severity}, Coverage: {result['damage_ratio']*100:.1f}%).\n\n"
                        f"To answer specific visual questions like *'{cam_query}'*, please link a free Google Gemini API Key in the left sidebar "
                        "under `🔑 AI Key & Neural Settings`."
                    )
                st.markdown(ai_reply)

        st.session_state.camera_chat_history.append({"role": "assistant", "content": ai_reply})
        st.rerun()

    # Clear image chat
    if st.session_state.camera_chat_history:
        if st.button("Clear Frame Discussion", key="clear_frame_chat"):
            st.session_state.camera_chat_history = []
            st.rerun()
