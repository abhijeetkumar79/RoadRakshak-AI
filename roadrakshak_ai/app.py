"""
RoadRakshak AI — Intelligent Road Damage, Accident & Alert Management System
Main entry point and navigation hub. Run with: streamlit run app.py
"""
import streamlit as st

from utils.ui import (
    inject_css,
    render_sidebar_header,
    render_sidebar_telemetry,
    render_sidebar_api_key_widget,
    render_sidebar_footer,
)
from utils.db import init_db
from utils.seed_data import reset_and_seed

# ---------------------------------------------------------------- Page Config (Top-level)
st.set_page_config(
    page_title="RoadRakshak AI — Road Damage & Safety Sentinel",
    page_icon="🛣️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize styles and seed database
inject_css()
init_db()
reset_and_seed(n=28)

# ---------------------------------------------------------------- Navigation Definition
pages = {
    "Navigation Hub": [
        st.Page("pages/home.py", title="Home & Overview", icon="🏠", default=True),
    ],
    "Citizen & Field Portal": [
        st.Page("pages/map_and_report.py", title="Map & Incident Report", icon="🗺️"),
        st.Page("pages/live_detection.py", title="Live AI Camera Scanner", icon="📸"),
        st.Page("pages/ai_assistant.py", title="AI RoadRakshak Assistant", icon="🤖"),
    ],
    "Municipal & Operations": [
        st.Page("pages/authority_dashboard.py", title="Authority Command Center", icon="🏛️"),
        st.Page("pages/reports.py", title="Analytics & PDF Exports", icon="📄"),
    ],
}

pg = st.navigation(pages)

# ---------------------------------------------------------------- Left Sidebar Widgets
with st.sidebar:
    render_sidebar_header()
    render_sidebar_telemetry()
    render_sidebar_api_key_widget()

# Run the selected page
pg.run()

# Persistent Sidebar Footer
with st.sidebar:
    render_sidebar_footer()
