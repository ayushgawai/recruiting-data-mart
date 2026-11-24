"""Funnel, time-to-stage, and source-ROI queries over the mart."""
from __future__ import annotations
import sqlite3
from pathlib import Path
from . import STAGES

def _con(db): return sqlite3.connect(Path(db))

def funnel(db) -> list[dict]:
    con = _con(db)
    rows = con.execute("SELECT stage, COUNT(DISTINCT application_id) FROM fact_stage_event GROUP BY stage").fetchall()
    con.close(); counts = dict(rows)
    out, prev = [], None
    for s in STAGES:
        c = counts.get(s, 0)
        out.append({"stage": s, "applications": c,
                    "conversion_from_prev": round(c / prev, 4) if prev else None})
        prev = c or prev
    out.append({"stage": "rejected", "applications": counts.get("rejected", 0), "conversion_from_prev": None})
    return out

def stage_count(db, stage: str) -> int:
    con = _con(db)
    n = con.execute("SELECT COUNT(DISTINCT application_id) FROM fact_stage_event WHERE stage=?", (stage,)).fetchone()[0]
    con.close(); return n

def time_to_stage(db) -> list[dict]:
    """Avg days from applied to each stage, per application that reached it."""
    con = _con(db)
    rows = con.execute("""
      SELECT stage, AVG(julianday(event_date) - julianday(applied_date)), COUNT(*)
      FROM (SELECT f.application_id, f.stage, MIN(f.event_date) AS event_date, a.applied_date
            FROM fact_stage_event f JOIN fact_application a USING(application_id)
            GROUP BY f.application_id, f.stage, a.applied_date)
      GROUP BY stage""").fetchall()
    con.close()
    order = {s: i for i, s in enumerate(STAGES + ["rejected"])}
    return [{"stage": s, "avg_days": round(d, 2), "n": n} for s, d, n in sorted(rows, key=lambda r: order.get(r[0], 99))]

# illustrative fully-loaded cost per source (USD per application) for ROI rollup
COST_PER_APPLICATION = {"linkedin": 42.0, "referral": 5.0, "job_board": 18.0, "agency": 120.0, "direct": 2.0}

def source_roi(db) -> list[dict]:
    con = _con(db)
    rows = con.execute("""
      SELECT a.source, COUNT(DISTINCT a.application_id),
             COUNT(DISTINCT CASE WHEN f.stage='hired' THEN a.application_id END)
      FROM fact_application a LEFT JOIN fact_stage_event f USING(application_id)
      GROUP BY a.source""").fetchall()
    con.close(); out = []
    for source, apps, hires in rows:
        cost = COST_PER_APPLICATION.get(source, 0.0) * apps
        out.append({"source": source, "applications": apps, "hires": hires,
                    "hire_rate": round(hires / apps, 4) if apps else 0,
                    "est_cost_usd": cost, "cost_per_hire_usd": round(cost / hires, 2) if hires else None})
    return sorted(out, key=lambda r: (r["cost_per_hire_usd"] is None, r["cost_per_hire_usd"]))
