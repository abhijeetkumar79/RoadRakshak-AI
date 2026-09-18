"""
Authority Command Center — Municipal & PWD Engineering Dashboard.
- Priority dispatch ranked by risk score
- Multi-stage repair workflow: OPEN -> ASSIGNED -> IN PROGRESS -> REPAIRED -> VERIFIED
- Before/After photo audit
- Decentralized citizen re-verification feedback loop
"""
import numpy as np
from PIL import Image
import streamlit as st
import plotly.express as px

from utils.ui import hero, section_title, divider, severity_badge, status_badge, card_open, card_close, kpi_card
from utils.db import (
    get_all_reports, update_status, add_verification, get_verification_counts,
)
from utils.risk import priority_label

hero(
    "Authority Command Center",
    "Municipal & Highway Authority Incident Dispatch, Repair Progress Lifecycle & Citizen Audit Queue.",
    emoji="🏛️",
    badge="🏢 PWD / MUNICIPAL DISPATCH",
)

df = get_all_reports()

# City filter bar
f_col1, f_col2 = st.columns([1.5, 3])
with f_col1:
    city_options = ["All Jurisdictions"] + sorted(df["city"].dropna().unique().tolist()) if not df.empty else ["All Jurisdictions"]
    selected_city = st.selectbox("Municipal Zone / City", city_options)
    if selected_city != "All Jurisdictions":
        df = df[df["city"] == selected_city]

# KPI row
c1, c2, c3, c4 = st.columns(4)
crit_n = int((df["risk_score"] >= 80).sum()) if not df.empty else 0
high_n = int(df["risk_score"].between(55, 79.9).sum()) if not df.empty else 0
res_n = int(df["status"].isin(["REPAIRED", "VERIFIED"]).sum()) if not df.empty else 0

with c1:
    kpi_card("Active Pipeline", str(len(df)), "📋", "Total registered")
with c2:
    kpi_card("Critical Priority", str(crit_n), "🚨", "Risk score ≥ 80")
with c3:
    kpi_card("High Priority", str(high_n), "🟠", "Risk score 55–79")
with c4:
    kpi_card("Work Completed", str(res_n), "🟢", "Repaired / Audited")

divider()

col_a, col_b = st.columns([1, 1])
with col_a:
    section_title("Severity Distribution")
    if not df.empty:
        fig = px.histogram(
            df, x="severity", color="severity",
            color_discrete_map={"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#10b981"},
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_family="Plus Jakarta Sans", font_color="#e2e8f0", showlegend=False,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            margin=dict(t=10, b=20, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No incident records available.")

with col_b:
    section_title("Workflow Pipeline Progress")
    if not df.empty:
        order = ["OPEN", "ASSIGNED", "IN PROGRESS", "REPAIRED", "VERIFIED"]
        vc = df["status"].value_counts().reindex(order).fillna(0)
        fig2 = px.bar(
            x=vc.index, y=vc.values, labels={"x": "Status Step", "y": "Incident Count"},
            color=vc.index,
            color_discrete_map={
                "OPEN": "#ef4444",
                "ASSIGNED": "#f59e0b",
                "IN PROGRESS": "#3b82f6",
                "REPAIRED": "#10b981",
                "VERIFIED": "#00f0ff",
            },
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font_family="Plus Jakarta Sans", font_color="#e2e8f0", showlegend=False,
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            margin=dict(t=10, b=20, l=10, r=10),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No incident records available.")

divider()

# Priority list
section_title("Priority-Ranked Repair Queue")
if df.empty:
    st.info("No reports logged for this jurisdiction.")
else:
    top = df.sort_values("risk_score", ascending=False).head(20)
    for r in top.itertuples():
        card_open()
        h1, h2, h3, h4 = st.columns([2.5, 1, 1, 1.2])
        with h1:
            st.markdown(f"**#{r.id} — {r.road_name or 'Unnamed Road'}**  \n<span style='color:#94a3b8; font-size:0.85rem;'>{r.area}, {r.city}</span>", unsafe_allow_html=True)
        with h2:
            st.markdown(severity_badge(r.severity), unsafe_allow_html=True)
        with h3:
            st.markdown(f"Risk: <b style='font-family: monospace; color: #00f0ff;'>{r.risk_score:.0f}</b>/100", unsafe_allow_html=True)
        with h4:
            st.markdown(status_badge(r.status), unsafe_allow_html=True)

        st.caption(f"{priority_label(r.risk_score)} · Duplicate Reports: {r.report_count} · Classification: {r.issue_type}")

        with st.expander(f"🛠️ Manage Incident #{r.id} Dispatch & Verification"):
            e1, e2 = st.columns(2)
            with e1:
                st.markdown("**Update Operational Status:**")
                status_choices = ["OPEN", "ASSIGNED", "IN PROGRESS", "REPAIRED", "VERIFIED"]
                curr_idx = status_choices.index(r.status) if r.status in status_choices else 0
                new_status = st.selectbox(
                    "Workflow Stage", status_choices, index=curr_idx, key=f"status_{r.id}",
                )
                if st.button("Apply Status Change", key=f"update_{r.id}"):
                    update_status(r.id, new_status)
                    st.success(f"Incident #{r.id} moved to '{new_status}'.")
                    st.rerun()

            with e2:
                st.markdown("**Evidence Verification:**")
                after_photo = st.file_uploader("Upload Contractor Completion Proof", type=["jpg", "jpeg", "png"], key=f"after_{r.id}")
                if after_photo is not None and st.button("Submit Completion Proof", key=f"mark_repaired_{r.id}"):
                    update_status(r.id, "REPAIRED", after_image_path=f"after_{r.id}.jpg")
                    st.success("Uploaded completion proof — incident queued for citizen verification.")
                    st.rerun()

            st.markdown("---")
            st.markdown("**Citizen Feedback & Ground Truth Validation:**")
            v1, v2, v3 = st.columns([1, 1, 2])
            with v1:
                if st.button("✅ Confirm Repaired", key=f"yes_{r.id}"):
                    add_verification(r.id, "yes")
                    st.rerun()
            with v2:
                if st.button("❌ Dispute Repair", key=f"no_{r.id}"):
                    add_verification(r.id, "no")
                    st.rerun()
            with v3:
                votes = get_verification_counts(r.id)
                yes_n, no_n = votes.get("yes", 0), votes.get("no", 0)
                if no_n > yes_n and no_n >= 2:
                    st.warning(f"⚠️ Citizen Audit Flagged: {no_n} citizen(s) dispute repair quality ({yes_n} confirmed).")
                elif yes_n or no_n:
                    st.caption(f"👍 {yes_n} confirmed · 👎 {no_n} disputed")
        card_close()
