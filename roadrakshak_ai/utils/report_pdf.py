"""
Professional PDF report generator for RoadRakshak AI.
Produces a branded summary report (title page, stats, top priority table)
using reportlab, so authorities have a shareable printable document.
"""
import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

BRAND_COLOR = colors.HexColor("#0b3d91")
ACCENT_COLOR = colors.HexColor("#00b8d9")


def generate_pdf_report(df, title="RoadRakshak AI — Road Condition Report", city_filter=None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=22 * mm, bottomMargin=18 * mm)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleBrand", parent=styles["Title"], textColor=BRAND_COLOR, fontSize=22)
    subtitle_style = ParagraphStyle("Subtitle", parent=styles["Normal"], textColor=colors.grey, fontSize=10)
    section_style = ParagraphStyle("Section", parent=styles["Heading2"], textColor=ACCENT_COLOR, spaceBefore=14)

    story = []
    story.append(Paragraph(title, title_style))
    scope = f"Scope: {city_filter}" if city_filter else "Scope: All monitored areas"
    story.append(Paragraph(f"{scope} &nbsp;|&nbsp; Generated: {datetime.utcnow().strftime('%d %b %Y, %H:%M UTC')}", subtitle_style))
    story.append(Spacer(1, 10))

    if df.empty:
        story.append(Paragraph("No reports available for the selected scope.", styles["Normal"]))
        doc.build(story)
        return buffer.getvalue()

    # --- Summary stats ---
    total = len(df)
    by_status = df["status"].value_counts()
    high_risk = len(df[df["risk_score"] >= 80])

    story.append(Paragraph("Executive Summary", section_style))
    summary_data = [
        ["Total Reports", "Open", "In Progress", "Repaired/Verified", "Critical (Risk ≥ 80)"],
        [
            str(total),
            str(int(by_status.get("OPEN", 0))),
            str(int(by_status.get("ASSIGNED", 0) + by_status.get("IN PROGRESS", 0))),
            str(int(by_status.get("REPAIRED", 0) + by_status.get("VERIFIED", 0))),
            str(high_risk),
        ],
    ]
    t = Table(summary_data, hAlign="LEFT", colWidths=[85] * 5)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke]),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # --- Priority repair list ---
    story.append(Paragraph("Priority Repair List (Top 15 by Risk Score)", section_style))
    top = df.sort_values("risk_score", ascending=False).head(15)
    table_data = [["Road", "Issue Type", "Severity", "Risk Score", "Reports", "Status"]]
    for r in top.itertuples():
        table_data.append([
            (r.road_name or "Unnamed")[:28],
            r.issue_type or "-",
            r.severity or "-",
            f"{r.risk_score:.0f}",
            str(r.report_count),
            r.status,
        ])
    t2 = Table(table_data, hAlign="LEFT", colWidths=[110, 75, 60, 55, 50, 75])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.whitesmoke]),
    ]))
    story.append(t2)
    story.append(Spacer(1, 14))

    story.append(Paragraph(
        "Generated automatically by RoadRakshak AI — Intelligent Road Damage, Accident & Alert "
        "Management System. Risk scores combine damage severity, AI detection confidence, issue "
        "type, and duplicate citizen reports.",
        subtitle_style,
    ))

    doc.build(story)
    return buffer.getvalue()
