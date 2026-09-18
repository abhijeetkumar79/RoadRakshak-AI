"""
RoadRakshak AI — Unified AI Engine Service
============================================
Supports Google Gemini (Recommended for Vision + Chat), Anthropic Claude,
and OpenAI. Uses standard `requests` for zero-dependency portability.
"""
import os
import io
import base64
import json
import cv2
import numpy as np
import requests
import streamlit as st
import pandas as pd

from .db import get_all_reports, road_health_scores


def get_active_api_key() -> str:
    """Resolve API key from session state, st.secrets, .env, or environment variables."""
    # 1. User entered in UI session state
    if "user_api_key" in st.session_state and st.session_state["user_api_key"].strip():
        return st.session_state["user_api_key"].strip()

    # 2. Streamlit secrets (.streamlit/secrets.toml)
    try:
        if hasattr(st, "secrets"):
            for secret_key in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
                if secret_key in st.secrets and str(st.secrets[secret_key]).strip():
                    return str(st.secrets[secret_key]).strip()
    except Exception:
        pass

    # 3. .env file in project directory
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k, v = k.strip(), v.strip().strip("'\"")
                        if k in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"] and v:
                            return v
    except Exception:
        pass

    # 4. System Environment variables
    for env_var in ["GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]:
        val = os.environ.get(env_var, "").strip()
        if val:
            return val
    return ""


def detect_provider(api_key: str) -> str:
    """Detect AI provider from key format or session setting."""
    if not api_key:
        return "none"
    if api_key.startswith("sk-ant"):
        return "anthropic"
    if api_key.startswith("sk-"):
        return "openai"
    # Default is Gemini (usually starts with AIzaSy... or custom key)
    return "gemini"


def get_api_status():
    """Return (is_linked, provider_name, model_name, masked_key)."""
    key = get_active_api_key()
    if not key:
        return False, "Offline Rule Engine", "Local SQLite Rule Engine", ""

    provider = detect_provider(key)
    masked = f"{key[:4]}...{key[-4:]}" if len(key) >= 8 else "***"

    if provider == "gemini":
        return True, "Google Gemini", "Gemini 2.5 Flash (Vision & Chat)", masked
    elif provider == "anthropic":
        return True, "Anthropic Claude", "Claude 3.5 Sonnet", masked
    elif provider == "openai":
        return True, "OpenAI", "GPT-4o Mini", masked
    return True, "Custom AI Key", "LLM Assistant", masked


def _encode_bgr_to_base64_jpeg(bgr_image: np.ndarray, quality: int = 85) -> str:
    """Convert OpenCV BGR image array to JPEG base64 string."""
    success, encoded = cv2.imencode(".jpg", bgr_image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not success:
        raise ValueError("Could not encode image to JPEG")
    return base64.b64encode(encoded.tobytes()).decode("utf-8")


def _get_live_database_summary(df: pd.DataFrame = None) -> str:
    """Compile compact, accurate summary of current reports to ground LLM answers."""
    if df is None:
        try:
            df = get_all_reports()
        except Exception:
            return "No database records available."

    if df.empty:
        return "The database currently contains 0 reports."

    total = len(df)
    by_status = df["status"].value_counts().to_dict()
    by_issue = df["issue_type"].value_counts().to_dict()
    critical_n = int((df["risk_score"] >= 80).sum())

    top_risks = df.sort_values("risk_score", ascending=False).head(5)[
        ["road_name", "area", "city", "issue_type", "risk_score", "status"]
    ].to_dict("records")

    health_summary = []
    try:
        health_df = road_health_scores()
        if not health_df.empty:
            for r in health_df.head(6).itertuples():
                health_summary.append(f"{r.road_name}: {r.health_score}/100 ({r.status})")
    except Exception:
        pass

    return (
        f"Total Logged Incidents: {total}.\n"
        f"Status Breakdown: {json.dumps(by_status)}.\n"
        f"Damage Types Breakdown: {json.dumps(by_issue)}.\n"
        f"Critical Risk Incidents (Score >= 80): {critical_n}.\n"
        f"Top 5 Highest Risk Incidents: {json.dumps(top_risks)}.\n"
        f"Road Health Scores: {'; '.join(health_summary)}."
    )


# ---------------------------------------------------------------- Gemini Provider
def _call_gemini_api(api_key: str, contents: list, system_instruction: str = None) -> str:
    """Make direct REST call to Gemini 2.5 Flash generateContent API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1024,
        },
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=25)
    if resp.status_code != 200:
        error_msg = resp.text
        try:
            err_json = resp.json()
            error_msg = err_json.get("error", {}).get("message", resp.text)
        except Exception:
            pass
        raise RuntimeError(f"Gemini API Error ({resp.status_code}): {error_msg}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return "No response generated by Gemini."

    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


# ---------------------------------------------------------------- Anthropic Provider
def _call_anthropic_api(api_key: str, messages: list, system_prompt: str = None) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1000,
        "messages": messages,
    }
    if system_prompt:
        payload["system"] = system_prompt

    resp = requests.post(url, json=payload, headers=headers, timeout=25)
    if resp.status_code != 200:
        raise RuntimeError(f"Anthropic API Error ({resp.status_code}): {resp.text}")

    data = resp.json()
    return "".join(b.get("text", "") for b in data.get("content", []))


# ---------------------------------------------------------------- OpenAI Provider
def _call_openai_api(api_key: str, messages: list) -> str:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": messages,
        "max_tokens": 1000,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=25)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI API Error ({resp.status_code}): {resp.text}")

    data = resp.json()
    return data["choices"][0]["message"]["content"]


# ---------------------------------------------------------------- High-Level API Functions
def generate_chat_answer(query: str, chat_history: list = None, df: pd.DataFrame = None) -> str:
    """
    Answer general road safety & database telemetry questions.
    Uses linked LLM if key is present, otherwise falls back to the rule-based engine.
    """
    key = get_active_api_key()
    provider = detect_provider(key)

    # 1. Fallback to rule engine if no API key
    if not key or provider == "none":
        from .chatbot import _rule_based_answer
        if df is None:
            df = get_all_reports()
        rule_reply = _rule_based_answer(query, df)
        if rule_reply:
            return rule_reply
        return (
            "I'm currently running in **Local Rule-Based Mode** without an active API key. "
            "I can reliably answer queries about report counts, high-risk roads, and road health scores.\n\n"
            "💡 *Tip: Enter your Google Gemini, Claude, or OpenAI API key in the left sidebar "
            "to unlock open-ended reasoning and deep conversational answers!*"
        )

    # 2. Call LLM with live database grounding
    context = _get_live_database_summary(df)
    system_prompt = (
        "You are RoadRakshak AI Sentinel, an intelligent copilot for Indian road infrastructure, "
        "pavement monitoring, accident prevention, and municipal repair management.\n"
        "You have direct access to the live telemetry database:\n"
        f"{context}\n\n"
        "GUIDELINES:\n"
        "1. Base answers on the live database numbers and facts whenever asked about incident counts, status, or road scores.\n"
        "2. Follow Indian Road Congress (IRC:SP:20, IRC:82) and Ministry of Road Transport & Highways (MoRTH) standards.\n"
        "3. Provide structured, concise, and helpful answers using markdown, bullet points, and bold tags."
    )

    try:
        if provider == "gemini":
            # Format contents for Gemini
            contents = []
            if chat_history:
                for msg in chat_history[-6:]:
                    role = "user" if msg["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            contents.append({"role": "user", "parts": [{"text": query}]})
            return _call_gemini_api(key, contents, system_prompt)

        elif provider == "anthropic":
            messages = []
            if chat_history:
                for msg in chat_history[-6:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": query})
            return _call_anthropic_api(key, messages, system_prompt)

        elif provider == "openai":
            messages = [{"role": "system", "content": system_prompt}]
            if chat_history:
                for msg in chat_history[-6:]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": query})
            return _call_openai_api(key, messages)

    except Exception as e:
        # If API fails, fall back to rule-based answer
        from .chatbot import _rule_based_answer
        if df is None:
            df = get_all_reports()
        fallback = _rule_based_answer(query, df)
        if fallback:
            return f"*(API Call Warning: {str(e)} — Falling back to local data)*\n\n{fallback}"
        return f"⚠️ Could not reach {provider.title()} API ({str(e)}). Please verify your API key in the left sidebar."


def analyze_road_image_ai(bgr_image: np.ndarray, user_instructions: str = None) -> str:
    """
    Perform deep multimodal AI road engineering inspection on a captured camera frame.
    """
    key = get_active_api_key()
    provider = detect_provider(key)

    if not key or provider != "gemini":
        if provider in ["anthropic", "openai"]:
            pass  # Could support multimodal OpenAI/Claude if needed, but Gemini is default
        else:
            return (
                "⚠️ **Multimodal Vision requires an active Google Gemini API Key.**  \n"
                "Please enter your Gemini API key in the left sidebar under '🔑 AI Key Configuration' "
                "to enable real-time neural image diagnostics, pothole depth estimations, and repair plans."
            )

    try:
        jpeg_b64 = _encode_bgr_to_base64_jpeg(bgr_image)
        prompt = (
            "You are an expert Civil & Highway Structural Inspection Engineer evaluating this road camera frame. "
            "Analyze the image and provide a concise, structured engineering assessment:\n"
            "1. **Surface Defects Identified**: (Specify Pothole, Alligator/Longitudinal Cracks, Waterlogging, Landslide, Rutting, or Broken Edge).\n"
            "2. **Estimated Severity & Dimensions**: (Low / Medium / High / Critical with physical description).\n"
            "3. **Traffic Hazard Impact**: (Impact on 2-wheelers vs cars/trucks, wet-weather hydroplaning risk).\n"
            "4. **Urgency & IRC Maintenance Guideline**: (e.g., immediate cold-mix asphalt patch, bituminous overlay, drainage clearance per IRC:82).\n"
            "Keep the response professional, bulleted, and actionable for municipal engineers."
        )
        if user_instructions:
            prompt += f"\n\nSpecific user question: {user_instructions}"

        contents = [
            {
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/jpeg",
                            "data": jpeg_b64,
                        }
                    },
                ],
            }
        ]

        system_instruction = "You are RoadRakshak AI Vision Sentinel, specialized in Indian highway damage and pothole detection."
        return _call_gemini_api(key, contents, system_instruction)

    except Exception as e:
        return f"⚠️ Vision Analysis Error: {str(e)}. Please check your API key in the left sidebar."


def chat_with_road_image(bgr_image: np.ndarray, chat_history: list, question: str) -> str:
    """
    Interactive multi-turn Q&A specifically about the captured road snapshot.
    """
    key = get_active_api_key()
    provider = detect_provider(key)

    if not key or provider != "gemini":
        return (
            "⚠️ **Interactive Vision Q&A requires a Google Gemini API Key.**  \n"
            "Please link your Gemini API Key in the left sidebar to ask questions about this road image."
        )

    try:
        jpeg_b64 = _encode_bgr_to_base64_jpeg(bgr_image)

        contents = []
        # First turn contains the image and initial inspection context
        first_prompt = (
            "You are evaluating this road camera frame for safety and municipal repairs. "
            f"The user asks: {question}"
        )
        first_parts = [
            {"text": first_prompt},
            {
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": jpeg_b64,
                }
            },
        ]

        # Build conversation turns
        if chat_history:
            # Reconstruct turns
            contents.append({"role": "user", "parts": first_parts})
            for msg in chat_history:
                role = "user" if msg["role"] == "user" else "model"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            contents.append({"role": "user", "parts": [{"text": question}]})
        else:
            contents.append({"role": "user", "parts": first_parts})

        system_instruction = (
            "You are RoadRakshak AI, an interactive highway safety inspector. "
            "Inspect the provided road image carefully to answer all questions accurately and concisely."
        )
        return _call_gemini_api(key, contents, system_instruction)

    except Exception as e:
        return f"⚠️ Vision Q&A Error: {str(e)}"
