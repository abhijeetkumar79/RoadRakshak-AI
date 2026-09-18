"""
RoadRakshak AI — Main Home & Overview Dashboard.
"""
import streamlit as st
import plotly.express as px

from utils.ui import hero, section_title, divider, card_open, card_close, kpi_card
from utils.db import get_all_reports, road_health_scores
from utils.detection import model_status

# Hero
hero(
    "RoadRakshak AI Sentinel",
    "Intelligent Pan-India Road Damage, Accident Detection & Infrastructure Sentinel — "
    "Piloted on Dehradun's Municipal Road Network.",
    emoji="🛣️",
    badge="🛡️ NATIONAL INFRASTRUCTURE MONITORING PILOT",
)

df = get_all_reports()

# KPI row
c1, c2, c3, c4 = st.columns(4)
total_count = len(df)
open_count = int((df["status"].isin(["OPEN", "ASSIGNED", "IN PROGRESS"])).sum()) if not df.empty else 0
crit_count = int((df["risk_score"] >= 80).sum()) if not df.empty else 0
resolved_count = int((df["status"].isin(["REPAIRED", "VERIFIED"])).sum()) if not df.empty else 0

with c1:
    kpi_card("Total Reports", str(total_count), "📋", "All-time logged")
with c2:
    kpi_card("Active Issues", str(open_count), "🚧", "Pending resolution")
with c3:
    kpi_card("Critical Hazards", str(crit_count), "🚨", "Risk score ≥ 80")
with c4:
    kpi_card("Repaired / Verified", str(resolved_count), "✅", "Restored to safety")

divider()

# Charts + Road health
left, right = st.columns([1.2, 1])

with left:
    section_title("Damage Breakdown by Category")
    if not df.empty:
        fig = px.pie(
            df, names="issue_type", hole=0.55,
            color_discrete_sequence=["#00f0ff", "#7c4dff", "#f59e0b", "#ef4444", "#10b981", "#3b82f6", "#ec4899"],
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="Plus Jakarta Sans",
            font_color="#e2e8f0",
            legend=dict(
                font=dict(size=12, color="#94a3b8"),
                orientation="h",
                yanchor="bottom",
                y=-0.25,
                xanchor="center",
                x=0.5,
            ),
            margin=dict(t=10, b=30, l=10, r=10),
        )
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            marker=dict(line=dict(color='#080c14', width=2)),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No reports yet — submit one from the Map & Report page.")

with right:
    section_title("Road Health Index")
    scores = road_health_scores()
    if not scores.empty:
        for row in scores.itertuples():
            card_open()
            col_t, col_s = st.columns([3, 1])
            with col_t:
                st.markdown(f"**{row.road_name}**")
            with col_s:
                st.markdown(f"<span style='font-family: monospace; font-weight: 700; color: #00f0ff;'>{row.health_score}/100</span>", unsafe_allow_html=True)
            st.progress(min(max(row.health_score / 100, 0.0), 1.0))
            st.caption(f"{row.status} · {row.open_reports} open hazard(s)")
            card_close()
    else:
        st.info("Road health metrics will appear here as incidents are logged.")

divider()

# Feature showcase
section_title("Platform Architecture & Modules")
f1, f2, f3, f4 = st.columns(4)
features = [
    ("🛰️", "Interactive GIS Satellite Map", "Search any location in India, pinpoint road damage coordinates, and visualize incident clusters."),
    ("🤖", "Live Edge AI Neural Scanner", "Real-time webcam and camera feed analysis detecting potholes, cracks, and road fissures instantly."),
    ("🏛️", "Authority Command Center", "Rank-ordered repair dispatch queue, engineer task assignments, and dual citizen re-verification."),
    ("💬", "AI Natural Language Sentinel", "Instant conversational queries over active road incidents, regional risk hot spots, and health indices."),
]
for col, (icon, title, desc) in zip([f1, f2, f3, f4], features):
    with col:
        card_open()
        st.markdown(f"#### {icon} {title}")
        st.caption(desc)
        card_close()

divider()
st.caption(
    f"RoadRakshak AI · {model_status()} · Architecture scales to NHAI & state municipal corporations."
)
