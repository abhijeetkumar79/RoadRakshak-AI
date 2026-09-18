"""
Seeds the database with realistic demo reports around Dehradun so the map,
dashboard, and reports pages aren't empty on first run. Safe to run multiple
times only if the table is empty — call `reset_and_seed()` to force refresh.
"""
import random
from .db import init_db, insert_report, get_all_reports, get_conn
from .risk import compute_risk_score

DEHRADUN_ROADS = [
    {"road_name": "Chakrata Road", "area": "Prem Nagar", "lat": 30.3560, "lon": 77.9520},
    {"road_name": "Rajpur Road", "area": "Rajpur", "lat": 30.3690, "lon": 78.0850},
    {"road_name": "Sahastradhara Road", "area": "Sahastradhara", "lat": 30.3810, "lon": 78.1120},
    {"road_name": "Haridwar Road", "area": "Clement Town", "lat": 30.2990, "lon": 78.0180},
    {"road_name": "GMS Road", "area": "GMS Road", "lat": 30.3260, "lon": 78.0350},
    {"road_name": "Ballupur Road", "area": "Ballupur", "lat": 30.3400, "lon": 78.0430},
]

ISSUE_TYPES = ["Pothole", "Road Crack", "Waterlogging", "Broken Road", "Landslide", "Accident"]
SEVERITIES = ["LOW", "MEDIUM", "HIGH"]
STATUSES = ["OPEN", "ASSIGNED", "IN PROGRESS", "REPAIRED", "VERIFIED"]


def reset_and_seed(n=28, force=False):
    init_db()
    existing = get_all_reports()
    if not existing.empty and not force:
        return len(existing)

    if force:
        with get_conn() as conn:
            conn.execute("DELETE FROM reports")
            conn.execute("DELETE FROM verifications")

    random.seed(42)
    for _ in range(n):
        road = random.choice(DEHRADUN_ROADS)
        issue = random.choice(ISSUE_TYPES)
        severity = random.choices(SEVERITIES, weights=[0.35, 0.4, 0.25])[0]
        confidence = round(random.uniform(0.55, 0.97), 2)
        report_count = random.choices([1, 2, 3, 5, 8, 17], weights=[40, 20, 15, 10, 10, 5])[0]
        risk = compute_risk_score(severity, confidence, issue, report_count)
        status = random.choices(STATUSES, weights=[0.4, 0.15, 0.15, 0.15, 0.15])[0]
        insert_report({
            "road_name": road["road_name"],
            "area": road["area"],
            "city": "Dehradun",
            "state": "Uttarakhand",
            "lat": road["lat"] + random.uniform(-0.01, 0.01),
            "lon": road["lon"] + random.uniform(-0.01, 0.01),
            "issue_type": issue,
            "severity": severity,
            "confidence": confidence,
            "risk_score": risk,
            "image_path": None,
            "after_image_path": None,
            "status": status,
            "report_count": report_count,
        })
    return n
