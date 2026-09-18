"""
Reports & Analytics Page — Filter records and generate official PDF engineering briefs.
"""
import streamlit as st
from utils.ui import hero, section_title, divider, card_open, card_close, kpi_card
from utils.db import get_all_reports
from utils.report_pdf import generate_pdf_report

hero(
    "Analytics & PDF Audit Briefs",
    "Filter multi-criteria incident datasets and compile official, executive-ready PDF engineering reports.",
    emoji="📄",
    badge="📑 AUDIT & COMPLIANCE",
)

df = get_all_reports()

section_title("Incident Filter Matrix")
card_open()
f1, f2, f3, f4 = st.columns(4)
with f1:
    city = st.selectbox("Municipal Zone", ["All"] + sorted(df["city"].dropna().unique().tolist())) if not df.empty else "All"
with f2:
    issue = st.selectbox("Damage Category", ["All"] + sorted(df["issue_type"].dropna().unique().tolist())) if not df.empty else "All"
with f3:
    status = st.selectbox("Resolution State", ["All", "OPEN", "ASSIGNED", "IN PROGRESS", "REPAIRED", "VERIFIED"])
with f4:
    min_risk = st.slider("Minimum Risk Threshold", 0, 100, 0)
card_close()

filtered = df.copy()
if not filtered.empty:
    if city != "All":
        filtered = filtered[filtered["city"] == city]
    if issue != "All":
        filtered = filtered[filtered["issue_type"] == issue]
    if status != "All":
        filtered = filtered[filtered["status"] == status]
    filtered = filtered[filtered["risk_score"] >= min_risk]

divider()

col_header, col_stats = st.columns([2, 1])
with col_header:
    section_title(f"Filtered Records ({len(filtered)} items)")
with col_stats:
    st.markdown(f"<div style='text-align: right; padding-top: 22px; color: #94a3b8; font-size: 0.85rem;'>Database synchronized</div>", unsafe_allow_html=True)

if filtered.empty:
    st.info("No records matched the selected query parameters.")
else:
    show_cols = ["id", "road_name", "area", "city", "issue_type", "severity",
                 "risk_score", "report_count", "status", "created_at"]
    st.dataframe(
        filtered[show_cols].sort_values("risk_score", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

divider()

section_title("Export Official PDF Engineering Report")
card_open()
st.markdown(
    "Generate a digitally formatted PDF summary report containing aggregated incident statistics, "
    "severity breakdowns, and priority lists for municipal engineers and state road transport authorities."
)

scope_label = None if city == "All" else city
pdf_col1, pdf_col2 = st.columns([1.5, 2])
with pdf_col1:
    if st.button("📑 Generate Official PDF Brief", type="primary", use_container_width=True):
        with st.spinner("Compiling document tables & charts..."):
            pdf_bytes = generate_pdf_report(filtered, city_filter=scope_label)
        st.download_button(
            "⬇️ Download PDF Document",
            data=pdf_bytes,
            file_name=f"RoadRakshak_Report_{city if city != 'All' else 'PanIndia'}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
        st.success("✅ Engineering PDF compiled successfully — click Download above.")
card_close()
