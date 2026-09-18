"""
RoadRakshak AI Assistant
========================

A grounded query assistant for the dashboard. It always answers using the
live report data in the database (counts, risk scores, road health, status)
so it never invents numbers.

Two backends:
  1. LLM backend (optional) — if an ANTHROPIC_API_KEY environment variable
     is set and the `anthropic` package is installed, free-form questions
     are answered by an LLM that is given a compact summary of the current
     data as context, so answers stay grounded in what's actually stored.
  2. Rule-based backend (always available, zero extra setup) — keyword
     matching over common question types: counts, high-risk roads, status
     of a specific road, road health score, and help.

The rule-based backend is tried first for structured questions; the LLM
backend (if available) is used as a fallback for open-ended questions.
"""
import os
import pandas as pd

from .db import get_all_reports, road_health_scores


def _summary_context(df: pd.DataFrame) -> str:
    if df.empty:
        return "There are currently no reports in the database."
    total = len(df)
    by_status = df["status"].value_counts().to_dict()
    by_issue = df["issue_type"].value_counts().to_dict()
    top_risk = df.sort_values("risk_score", ascending=False).head(5)[
        ["road_name", "issue_type", "risk_score", "status"]
    ].to_dict("records")
    return (
        f"Total reports: {total}. By status: {by_status}. By issue type: {by_issue}. "
        f"Top 5 highest-risk open items: {top_risk}."
    )


def _rule_based_answer(query: str, df: pd.DataFrame):
    q = query.lower().strip()

    if df.empty:
        return "There are no reports in the system yet — submit one from the Map & Report page to get started."

    if any(k in q for k in ["how many", "total reports", "count"]):
        if "pothole" in q:
            n = len(df[df["issue_type"] == "Pothole"])
            return f"There are **{n}** pothole reports currently in the system."
        if "accident" in q:
            n = len(df[df["issue_type"] == "Accident"])
            return f"There are **{n}** accident reports currently in the system."
        if "open" in q:
            n = len(df[df["status"] == "OPEN"])
            return f"There are **{n}** OPEN (unresolved) reports."
        if "resolved" in q or "repaired" in q or "verified" in q:
            n = len(df[df["status"].isin(["REPAIRED", "VERIFIED"])])
            return f"**{n}** reports have been marked repaired/verified."
        return f"There are **{len(df)}** total reports in the system."

    if "high risk" in q or "critical" in q or "worst road" in q or "priority" in q:
        top = df.sort_values("risk_score", ascending=False).head(5)
        lines = [f"- **{r.road_name or 'Unnamed road'}** ({r.issue_type}) — risk {r.risk_score}/100, status {r.status}"
                 for r in top.itertuples()]
        return "Here are the highest-risk open items:\n" + "\n".join(lines)

    if "health score" in q or "road health" in q:
        scores = road_health_scores()
        if scores.empty:
            return "No road health data available yet."
        lines = [f"- **{r.road_name}**: {r.health_score}/100 ({r.status})" for r in scores.itertuples()]
        return "Current road health scores:\n" + "\n".join(lines)

    for road in df["road_name"].dropna().unique():
        if road and road.lower() in q:
            sub = df[df["road_name"] == road]
            open_n = len(sub[sub["status"].isin(["OPEN", "ASSIGNED", "IN PROGRESS"])])
            avg_risk = round(sub["risk_score"].mean(), 1)
            return (f"**{road}** has {len(sub)} total report(s), {open_n} still open, "
                    f"and an average risk score of {avg_risk}/100.")

    if any(k in q for k in ["help", "what can you", "features"]):
        return (
            "I can answer questions like:\n"
            "- *How many potholes have been reported?*\n"
            "- *What are the highest risk roads right now?*\n"
            "- *What's the health score of Chakrata Road?*\n"
            "- *How many reports are still open?*\n\n"
            "You can also report a new issue from **Map & Report**, or generate a PDF from **Reports**."
        )

    return None  # not handled by rules — fall through to LLM / generic reply


def _llm_answer(query: str, df: pd.DataFrame):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        context = _summary_context(df)
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=(
                "You are the RoadRakshak AI assistant embedded in a road-damage monitoring dashboard. "
                "Answer ONLY using the data summary provided. If the summary doesn't contain the answer, "
                "say you don't have that information yet. Be concise and use markdown."
            ),
            messages=[{"role": "user", "content": f"Data summary: {context}\n\nQuestion: {query}"}],
        )
        return "".join(block.text for block in resp.content if hasattr(block, "text"))
    except Exception:
        return None


def answer(query: str, chat_history: list = None) -> str:
    """Answer user questions using unified AI engine (Gemini/Claude/OpenAI) or local rules."""
    try:
        from .ai_engine import generate_chat_answer
        return generate_chat_answer(query, chat_history=chat_history)
    except Exception:
        df = get_all_reports()
        return _rule_based_answer(query, df) or (
            "I'm operating in local database mode. Ask me about counts, highest risk roads, or road health."
        )
