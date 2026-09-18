"""
RoadRakshak AI Assistant — Intelligent Q&A Chatbox
Grounded in live database telemetry and powered by linked AI (Gemini / Claude / OpenAI).
"""
import streamlit as st
from utils.ui import hero, section_title, divider, card_open, card_close
from utils.ai_engine import get_api_status, generate_chat_answer
from utils.db import get_all_reports

hero(
    "RoadRakshak AI Assistant",
    "Conversational intelligence grounded in live road damage telemetry, risk hotspots, and municipal health scores.",
    emoji="🤖",
    badge="🧠 CONVERSATIONAL SENTINEL",
)

# ---------------------------------------------------------------- AI Provider & Status Banner
is_linked, provider, model_name, masked_key = get_api_status()

status_col1, status_col2 = st.columns([2.5, 1])
with status_col1:
    if is_linked:
        st.markdown(
            f"<div style='display:inline-flex; align-items:center; gap:8px; padding:6px 14px; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.3); border-radius:999px; font-size:0.8rem; font-weight:700; color:#34d399; margin-bottom:12px;'>"
            f"<span style='width:8px; height:8px; border-radius:50%; background:#10b981;'></span>"
            f"<span>{provider} Active ({model_name}) · Key: <code>{masked_key}</code></span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='display:inline-flex; align-items:center; gap:8px; padding:6px 14px; background:rgba(245,158,11,0.12); border:1px solid rgba(245,158,11,0.3); border-radius:999px; font-size:0.8rem; font-weight:700; color:#fcd34d; margin-bottom:12px;'>"
            "<span style='width:8px; height:8px; border-radius:50%; background:#f59e0b;'></span>"
            "<span>Local Rule Engine Active · Link API key in left sidebar for open-ended LLM</span>"
            "</div>",
            unsafe_allow_html=True,
        )

with status_col2:
    if "chat_history" in st.session_state and len(st.session_state.chat_history) > 1:
        if st.button("🗑️ Clear Chat", key="clear_chat_btn", use_container_width=True):
            st.session_state.chat_history = [
                {"role": "assistant", "content": "Chat history cleared. How can I assist you with road safety and maintenance today?"}
            ]
            st.rerun()

# ---------------------------------------------------------------- Chat State Initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant",
            "content": (
                "👋 **Greetings! I am the RoadRakshak AI Sentinel.**\n\n"
                "I am directly connected to the live Dehradun road database. Ask me anything about:\n"
                "• **Real-time Incident Counts** (*e.g., how many potholes or open hazards exist?*)\n"
                "• **High-Risk Hotspots** (*e.g., which roads have a risk score above 80?*)\n"
                "• **Road Health Indices** (*e.g., what is the condition of Chakrata Road?*)\n"
                "• **Indian Road Congress (IRC) Repair Standards** (*e.g., how to treat alligator cracking?*)"
            ),
        }
    ]

# ---------------------------------------------------------------- Quick Prompt Chips
section_title("💡 Suggested Quick Inquiries")
p1, p2, p3, p4 = st.columns(4)

selected_prompt = None
with p1:
    if st.button("🚨 Top High-Risk Roads?", use_container_width=True):
        selected_prompt = "What are the highest risk roads and critical open incidents right now?"
with p2:
    if st.button("📊 Open Incidents Count?", use_container_width=True):
        selected_prompt = "How many open reports are currently pending repair across all roads?"
with p3:
    if st.button("🩺 Chakrata Road Health?", use_container_width=True):
        selected_prompt = "What is the health score and current condition of Chakrata Road?"
with p4:
    if st.button("🛠️ Pothole Repair Spec?", use_container_width=True):
        selected_prompt = "What is the standard IRC specification for emergency pothole patching?"

# ---------------------------------------------------------------- Chat History Container
section_title("💬 Interactive Q&A Session")

chat_container = st.container()
with chat_container:
    for msg in st.session_state.chat_history:
        avatar = "🧑" if msg["role"] == "user" else "🤖"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

# Handle user input from quick prompt or chat input bar
user_query = selected_prompt or st.chat_input("Ask a question about road hazards, repair queue, or infrastructure standards...")

if user_query:
    # Append user message
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    with chat_container:
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_query)

    # Generate response
    with chat_container:
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner(f"Analyzing live telemetry database via {provider}..."):
                df = get_all_reports()
                reply = generate_chat_answer(user_query, chat_history=st.session_state.chat_history[:-1], df=df)
                st.markdown(reply)

    # Append assistant message
    st.session_state.chat_history.append({"role": "assistant", "content": reply})
    st.rerun()

divider()

# Optional in-page key helper
if not is_linked:
    with st.expander("🔑 Quick API Key Setup (Unlock Full Intelligence)"):
        st.markdown(
            "To unlock free-form conversational understanding, road engineering knowledge, and full reasoning:  \n"
            "1. Get a free key from **[Google AI Studio](https://aistudio.google.com/app/apikey)**.  \n"
            "2. Paste it in the **Left Sidebar** under `🔑 AI Key & Neural Settings`, or paste it below:"
        )
        in_page_key = st.text_input("Paste Gemini API Key", type="password", key="in_page_api_key")
        if st.button("Link Key", key="in_page_save_key"):
            if in_page_key.strip():
                st.session_state["user_api_key"] = in_page_key.strip()
                st.success("API Key successfully linked!")
                st.rerun()
