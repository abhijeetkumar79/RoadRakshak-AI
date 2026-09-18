"""
Shared UI helpers — CSS injection, sidebar layout widgets, and reusable
glassmorphic components across RoadRakshak AI.
"""
import os
import streamlit as st

CSS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "style.css")


def inject_css():
    """Inject custom cyber theme CSS if file exists."""
    if os.path.exists(CSS_PATH):
        with open(CSS_PATH, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def render_sidebar_header():
    """Render top brand card in the left sidebar."""
    st.markdown(
        """
        <div class="rr-sidebar-brand">
            <div class="rr-sidebar-logo-title">
                <span>🛣️</span> RoadRakshak AI
            </div>
            <div class="rr-sidebar-tagline">
                Intelligent Road Sentinel
            </div>
            <div class="rr-status-pill">
                <span class="rr-status-dot"></span>
                <span>SYSTEM ONLINE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_telemetry(df=None):
    """Render live telemetry snapshot grid in the left sidebar."""
    if df is None:
        try:
            from utils.db import get_all_reports
            df = get_all_reports()
        except Exception:
            df = None

    total_reports = len(df) if df is not None and not df.empty else 0
    open_reports = int((df["status"].isin(["OPEN", "ASSIGNED", "IN PROGRESS"])).sum()) if df is not None and not df.empty else 0
    critical_reports = int((df["risk_score"] >= 80).sum()) if df is not None and not df.empty else 0

    st.markdown(
        f"""
        <div style="margin: 10px 0 6px 0; font-size: 0.72rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em;">
            📡 Live Telemetry
        </div>
        <div class="rr-sidebar-telemetry">
            <div class="rr-sidebar-chip">
                <div class="rr-sidebar-chip-val" style="color: #00f0ff;">{total_reports}</div>
                <div class="rr-sidebar-chip-lbl">Total Incidents</div>
            </div>
            <div class="rr-sidebar-chip">
                <div class="rr-sidebar-chip-val" style="color: #f59e0b;">{open_reports}</div>
                <div class="rr-sidebar-chip-lbl">Open Tasks</div>
            </div>
            <div class="rr-sidebar-chip">
                <div class="rr-sidebar-chip-val" style="color: #ef4444;">{critical_reports}</div>
                <div class="rr-sidebar-chip-lbl">Critical Risk</div>
            </div>
            <div class="rr-sidebar-chip">
                <div class="rr-sidebar-chip-val" style="color: #10b981;">98.4%</div>
                <div class="rr-sidebar-chip-lbl">Uptime</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_api_key_widget():
    """Render interactive API key input & provider status in the sidebar."""
    from .ai_engine import get_api_status

    is_linked, provider, model_name, masked = get_api_status()

    expander_title = "🔑 AI Key: Linked & Active" if is_linked else "🔑 Link Google Gemini Key"
    with st.expander(expander_title, expanded=not is_linked):
        if is_linked:
            st.markdown(
                f"<div style='font-size:0.75rem; color:#34d399; font-weight:700; margin-bottom:4px;'>"
                f"🟢 {provider} Linked"
                f"</div>"
                f"<div style='font-size:0.7rem; color:#94a3b8; margin-bottom:8px;'>"
                f"Engine: {model_name}<br>Active Key: <code>{masked}</code>"
                f"</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='font-size:0.75rem; color:#f59e0b; font-weight:700; margin-bottom:4px;'>"
                "⚪ Local Rule Engine Active"
                "</div>"
                "<div style='font-size:0.7rem; color:#94a3b8; margin-bottom:8px;'>"
                "Link a free Google Gemini key (or Claude / OpenAI) for real-time vision diagnostics and open-domain Q&A."
                "</div>",
                unsafe_allow_html=True,
            )

        current_val = st.session_state.get("user_api_key", "")
        new_key = st.text_input(
            "API Key",
            value=current_val,
            type="password",
            placeholder="AIzaSy... or sk-...",
            key="sidebar_api_key_input",
            help="Supports Google Gemini (recommended), Anthropic, or OpenAI API key.",
        )

        b1, b2 = st.columns(2)
        with b1:
            if st.button("Save", key="save_key_btn", use_container_width=True):
                st.session_state["user_api_key"] = new_key.strip()
                st.rerun()
        with b2:
            if current_val and st.button("Reset", key="reset_key_btn", use_container_width=True):
                st.session_state["user_api_key"] = ""
                st.rerun()

        st.markdown(
            "<div style='font-size: 0.68rem; color: #64748b; margin-top: 6px; text-align: center;'>"
            "<a href='https://aistudio.google.com/app/apikey' target='_blank' style='color:#00f0ff; text-decoration:none;'>⚡ Get free Gemini API Key</a>"
            "</div>",
            unsafe_allow_html=True,
        )


def render_sidebar_footer():
    """Render persistent emergency contacts & version in sidebar."""
    st.markdown(
        """
        <div class="rr-sidebar-footer">
            <div style="font-weight: 600; color: #94a3b8; margin-bottom: 6px;">
                🚨 Emergency Dispatch
            </div>
            <div class="rr-hotline-pill">
                <span>National Highway Helpline</span>
                <span style="font-family: monospace; font-weight: 700;">1033</span>
            </div>
            <div class="rr-hotline-pill" style="margin-top: 6px; background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.25); color: #93c5fd;">
                <span>Emergency Response System</span>
                <span style="font-family: monospace; font-weight: 700;">112</span>
            </div>
            <div style="margin-top: 14px; text-align: center; color: #475569; font-size: 0.7rem;">
                Pilot City: <b>Dehradun (UK)</b><br>
                RoadRakshak Sentinel v2.4 Pro
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, emoji: str = "🛣️", badge: str = "🛡️ NATIONAL INFRASTRUCTURE SENTINEL"):
    """Render modern cyber hero banner."""
    st.markdown(
        f"""
        <div class="rr-hero">
            <div class="rr-hero-badge">{badge}</div>
            <h1><span class="rr-float">{emoji}</span> {title}</h1>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_title(text: str):
    """Render styled section header."""
    st.markdown(f'<div class="rr-section-title">{text}</div>', unsafe_allow_html=True)


def severity_badge(severity: str) -> str:
    """Return HTML string for colored severity badge."""
    s = (severity or "").upper()
    css_class = {"HIGH": "rr-badge-high", "MEDIUM": "rr-badge-medium", "LOW": "rr-badge-low"}.get(s, "rr-badge-info")
    return f'<span class="rr-badge {css_class}">{s or "N/A"}</span>'


def status_badge(status: str) -> str:
    """Return HTML string for colored status badge."""
    mapping = {
        "OPEN": "rr-badge-high",
        "ASSIGNED": "rr-badge-medium",
        "IN PROGRESS": "rr-badge-medium",
        "REPAIRED": "rr-badge-low",
        "VERIFIED": "rr-badge-info",
    }
    css_class = mapping.get(status, "rr-badge-info")
    return f'<span class="rr-badge {css_class}">{status}</span>'


def divider():
    """Render glowing horizontal divider."""
    st.markdown('<hr class="rr-divider">', unsafe_allow_html=True)


def card_open():
    """Open a glass card container."""
    st.markdown('<div class="rr-card">', unsafe_allow_html=True)


def card_close():
    """Close a glass card container."""
    st.markdown('</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, icon: str = "📊", trend: str = ""):
    """Render an enhanced glass KPI card."""
    trend_html = f'<div style="font-size: 0.72rem; color: #34d399; margin-top: 4px;">{trend}</div>' if trend else ""
    st.markdown(
        f"""
        <div class="rr-kpi-card">
            <div class="rr-kpi-label">{label}</div>
            <div class="rr-kpi-val">
                <span>{icon}</span>
                <span>{value}</span>
            </div>
            {trend_html}
        </div>
        """,
        unsafe_allow_html=True,
    )
