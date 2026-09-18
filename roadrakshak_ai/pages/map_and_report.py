"""
Map & Incident Reporting Page
- Geocoding search across India
- Normal / Satellite / Risk layer modes
- Interactive pin placement
- AI Damage Detection & Risk Scoring
- Automated 60m duplicate incident merging
"""
import io
import numpy as np
from PIL import Image
import streamlit as st
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

from utils.ui import hero, section_title, divider, severity_badge, status_badge, card_open, card_close
from utils.db import get_all_reports, insert_report, find_nearby_duplicate, bump_duplicate
from utils.geo import geocode_place
from utils.detection import analyze_image, model_status
from utils.risk import compute_risk_score, severity_from_damage_ratio

hero(
    "GIS Map & Incident Reporting",
    "Pinpoint road damage spots on satellite imagery, upload evidence photos, and trigger automated AI triage.",
    emoji="🗺️",
    badge="🛰️ CITIZEN & SENSOR PORTAL",
)

st.caption(f"Neural Engine: {model_status()}")

# Session state defaults
if "pin_lat" not in st.session_state:
    st.session_state.pin_lat, st.session_state.pin_lon = 30.3165, 78.0322  # Dehradun default
if "map_center" not in st.session_state:
    st.session_state.map_center = [st.session_state.pin_lat, st.session_state.pin_lon]
if "map_zoom" not in st.session_state:
    st.session_state.map_zoom = 12

# Search bar
sc1, sc2, sc3 = st.columns([3, 1, 1])
with sc1:
    query = st.text_input("🔍 Search location in India", placeholder="e.g. Rajpur Road, Dehradun or Connaught Place, Delhi")
with sc2:
    search_clicked = st.button("Locate", use_container_width=True)
with sc3:
    layer_mode = st.selectbox("Map layer", ["🗺️ Normal", "🛰️ Satellite", "🚨 Risk Heatmap"], label_visibility="collapsed")

if search_clicked and query:
    result = geocode_place(query)
    if result:
        lat, lon, address = result
        st.session_state.map_center = [lat, lon]
        st.session_state.map_zoom = 15
        st.session_state.pin_lat, st.session_state.pin_lon = lat, lon
        st.success(f"📍 Found: {address}")
    else:
        st.warning("Location not found or network lookup timed out. You can also click anywhere on the map to drop a pin.")

divider()

map_col, form_col = st.columns([1.6, 1])

with map_col:
    section_title("Interactive Road Network Map")

    m = folium.Map(location=st.session_state.map_center, zoom_start=st.session_state.map_zoom, control_scale=True)

    folium.TileLayer("OpenStreetMap", name="🗺️ Normal").add_to(m)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="🛰️ Satellite",
    ).add_to(m)

    df = get_all_reports()
    cluster = MarkerCluster(name="Incidents").add_to(m)

    severity_color = {"HIGH": "red", "MEDIUM": "orange", "LOW": "green"}
    for r in df.itertuples():
        color = severity_color.get((r.severity or "").upper(), "blue")
        if layer_mode.startswith("🚨") and r.risk_score is not None and r.risk_score < 50:
            continue
        popup_html = (
            f"<div style='font-family: sans-serif; font-size: 13px;'>"
            f"<b>{r.road_name or 'Unnamed road'}</b><br>"
            f"<b>Issue:</b> {r.issue_type} ({r.severity})<br>"
            f"<b>Risk Score:</b> {r.risk_score}/100<br>"
            f"<b>Status:</b> {r.status}<br>"
            f"<b>Incident Reports:</b> {r.report_count}"
            f"</div>"
        )
        folium.Marker(
            location=[r.lat, r.lon],
            popup=folium.Popup(popup_html, max_width=260),
            icon=folium.Icon(color=color, icon="exclamation-triangle", prefix="fa"),
        ).add_to(cluster)

    # Pin for the currently selected point
    folium.Marker(
        location=[st.session_state.pin_lat, st.session_state.pin_lon],
        icon=folium.Icon(color="blue", icon="map-pin", prefix="fa"),
        popup="Selected Location for New Report",
    ).add_to(m)

    folium.LayerControl().add_to(m)

    map_data = st_folium(m, height=520, use_container_width=True, key="main_map")

    if map_data and map_data.get("last_clicked"):
        st.session_state.pin_lat = map_data["last_clicked"]["lat"]
        st.session_state.pin_lon = map_data["last_clicked"]["lng"]
        st.rerun()

    st.markdown(
        "<div style='font-size: 0.82rem; color: #94a3b8; margin-top: 8px;'>"
        "🟢 Low Severity &nbsp;·&nbsp; 🟠 Medium &nbsp;·&nbsp; 🔴 High Hazard &nbsp;·&nbsp; 🔵 Selected Pin"
        "</div>",
        unsafe_allow_html=True,
    )

with form_col:
    section_title("Report Road Damage")
    lat, lon = st.session_state.pin_lat, st.session_state.pin_lon
    
    card_open()
    c_lat, c_lon = st.columns(2)
    with c_lat:
        st.text_input("Latitude", value=f"{lat:.5f}", disabled=True)
    with c_lon:
        st.text_input("Longitude", value=f"{lon:.5f}", disabled=True)

    with st.form("report_form"):
        road_name = st.text_input("Road Name", placeholder="e.g. Chakrata Road")
        area = st.text_input("Locality / Sector", placeholder="e.g. Prem Nagar")
        city = st.text_input("City", value="Dehradun")
        state = st.text_input("State", value="Uttarakhand")
        issue_type = st.selectbox(
            "Damage Classification",
            ["Pothole", "Road Crack", "Waterlogging", "Landslide", "Broken Road", "Accident Hazard", "Other"],
        )
        uploaded = st.file_uploader("Upload Inspection Photo", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("⚡ Analyze & Submit Incident", use_container_width=True)

    card_close()

    if submitted:
        if uploaded is None:
            st.error("Please provide an image of the road condition for AI verification.")
        else:
            image = Image.open(uploaded).convert("RGB")
            bgr = np.array(image)[:, :, ::-1].copy()
            result = analyze_image(bgr, issue_hint=issue_type)

            severity = severity_from_damage_ratio(result["damage_ratio"])
            confidence = result["top_confidence"] or 0.6
            risk_score = compute_risk_score(severity, confidence, issue_type)

            st.image(result["annotated_image"][:, :, ::-1], caption="AI Vision Inspection Result", use_container_width=True)
            badge = severity_badge(severity)
            st.markdown(
                f"<div style='margin: 8px 0; padding: 10px; background: rgba(15,23,42,0.6); border-radius: 10px; border: 1px solid rgba(0,240,255,0.2);'>"
                f"<b>Identified:</b> {result['top_label']} &nbsp;|&nbsp; "
                f"<b>Confidence:</b> {confidence*100:.0f}% &nbsp;|&nbsp; "
                f"<b>Severity:</b> {badge} &nbsp;|&nbsp; "
                f"<b>Risk Score:</b> <span style='font-family: monospace; font-weight: 700; color: #00f0ff;'>{risk_score}/100</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            dup_id = find_nearby_duplicate(lat, lon, issue_type, radius_m=60)
            if dup_id:
                bump_duplicate(dup_id)
                st.info(f"♻️ Existing incident verified nearby (#{dup_id}) — report count updated rather than creating a duplicate.")
            else:
                new_id = insert_report({
                    "road_name": road_name or "Unnamed road",
                    "area": area, "city": city, "state": state,
                    "lat": lat, "lon": lon,
                    "issue_type": issue_type, "severity": severity,
                    "confidence": confidence, "risk_score": risk_score,
                    "image_path": None, "after_image_path": None,
                    "status": "OPEN", "report_count": 1,
                })
                st.success(f"✅ Incident Report #{new_id} recorded in central registry!")
            st.rerun()
