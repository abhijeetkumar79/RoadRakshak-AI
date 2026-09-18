"""
Risk scoring logic.

Risk Score (0-100) combines:
  - damage severity (Low / Medium / High)
  - AI detection confidence
  - number of duplicate citizen reports for the same spot
  - issue type weight (accidents & landslides weigh higher than a minor crack)
"""

SEVERITY_BASE = {"LOW": 25, "MEDIUM": 55, "HIGH": 85}

ISSUE_WEIGHT = {
    "Pothole": 1.0,
    "Road Crack": 0.75,
    "Waterlogging": 0.9,
    "Landslide": 1.15,
    "Broken Road": 1.05,
    "Accident": 1.2,
    "Other": 0.7,
}


def compute_risk_score(severity: str, confidence: float, issue_type: str, report_count: int = 1) -> float:
    base = SEVERITY_BASE.get(severity.upper(), 50)
    weight = ISSUE_WEIGHT.get(issue_type, 0.9)
    confidence_factor = 0.6 + (confidence * 0.4)  # confidence in [0,1]
    duplicate_boost = min((report_count - 1) * 3, 20)  # more citizen reports -> higher priority
    score = base * weight * confidence_factor + duplicate_boost
    return round(min(max(score, 0), 100), 1)


def severity_from_damage_ratio(ratio: float) -> str:
    """Map a 0-1 'damage coverage ratio' from the detector into a severity bucket."""
    if ratio >= 0.18:
        return "HIGH"
    elif ratio >= 0.07:
        return "MEDIUM"
    return "LOW"


def priority_label(risk_score: float) -> str:
    if risk_score >= 80:
        return "🔴 IMMEDIATE"
    elif risk_score >= 55:
        return "🟠 HIGH PRIORITY"
    elif risk_score >= 30:
        return "🟡 SCHEDULE MAINTENANCE"
    return "🟢 LOW PRIORITY"
