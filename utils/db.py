"""
RoadRakshak AI — Database layer (SQLite)

Tables
------
reports:
    id, road_name, area, city, state, lat, lon, issue_type,
    severity, confidence, risk_score, image_path, status,
    report_count, created_at, updated_at

verifications:
    id, report_id, vote ('yes'/'no'), created_at

All functions are thin wrappers around sqlite3 so the rest of the app
never has to write raw SQL.
"""
import sqlite3
import os
from datetime import datetime
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "roadrakshak.db")


@contextmanager
def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                road_name TEXT,
                area TEXT,
                city TEXT,
                state TEXT,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                issue_type TEXT,
                severity TEXT,
                confidence REAL,
                risk_score REAL,
                image_path TEXT,
                after_image_path TEXT,
                status TEXT DEFAULT 'OPEN',
                report_count INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS verifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER,
                vote TEXT,
                created_at TEXT,
                FOREIGN KEY(report_id) REFERENCES reports(id)
            )
        """)


def insert_report(data: dict) -> int:
    now = datetime.utcnow().isoformat()
    data = {**data, "created_at": now, "updated_at": now}
    cols = ", ".join(data.keys())
    placeholders = ", ".join(["?"] * len(data))
    with get_conn() as conn:
        cur = conn.execute(f"INSERT INTO reports ({cols}) VALUES ({placeholders})", list(data.values()))
        return cur.lastrowid


def bump_duplicate(report_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE reports SET report_count = report_count + 1, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), report_id),
        )


def find_nearby_duplicate(lat, lon, issue_type, radius_m=60):
    """Return the id of an existing OPEN/ASSIGNED report of the same issue_type
    within `radius_m` meters, or None."""
    from .geo import haversine_m
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, lat, lon FROM reports WHERE issue_type = ? AND status IN ('OPEN','ASSIGNED','IN PROGRESS')",
            (issue_type,),
        ).fetchall()
    for row in rows:
        if haversine_m(lat, lon, row["lat"], row["lon"]) <= radius_m:
            return row["id"]
    return None


def get_all_reports():
    import pandas as pd
    with get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM reports ORDER BY created_at DESC", conn)
    return df


def update_status(report_id: int, status: str, after_image_path: str = None):
    with get_conn() as conn:
        if after_image_path:
            conn.execute(
                "UPDATE reports SET status = ?, after_image_path = ?, updated_at = ? WHERE id = ?",
                (status, after_image_path, datetime.utcnow().isoformat(), report_id),
            )
        else:
            conn.execute(
                "UPDATE reports SET status = ?, updated_at = ? WHERE id = ?",
                (status, datetime.utcnow().isoformat(), report_id),
            )


def add_verification(report_id: int, vote: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO verifications (report_id, vote, created_at) VALUES (?, ?, ?)",
            (report_id, vote, datetime.utcnow().isoformat()),
        )


def get_verification_counts(report_id: int):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT vote, COUNT(*) as c FROM verifications WHERE report_id = ? GROUP BY vote", (report_id,)
        ).fetchall()
    return {r["vote"]: r["c"] for r in rows}


def road_health_scores():
    """Aggregate a 0-100 health score per road_name from stored reports."""
    import pandas as pd
    df = get_all_reports()
    if df.empty:
        return pd.DataFrame(columns=["road_name", "health_score", "status", "open_reports"])

    def score_for_group(g):
        open_reports = g[g["status"].isin(["OPEN", "ASSIGNED", "IN PROGRESS"])]
        penalty = (open_reports["risk_score"].fillna(0) * open_reports["report_count"].fillna(1)).sum()
        penalty = min(penalty / 8, 100)
        return max(0, round(100 - penalty, 1))

    grouped = df.groupby("road_name").apply(score_for_group).reset_index()
    grouped.columns = ["road_name", "health_score"]

    def status_label(s):
        if s >= 75:
            return "🟢 Good"
        elif s >= 50:
            return "🟡 Moderate"
        else:
            return "🔴 Critical"

    grouped["status"] = grouped["health_score"].apply(status_label)
    open_counts = df[df["status"].isin(["OPEN", "ASSIGNED", "IN PROGRESS"])].groupby("road_name").size()
    grouped["open_reports"] = grouped["road_name"].map(open_counts).fillna(0).astype(int)
    return grouped.sort_values("health_score")
