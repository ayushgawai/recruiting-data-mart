"""Mart models: build dim/fact tables in SQLite (portable SQL mirrors sql/*.sql)."""
from __future__ import annotations
import sqlite3
from pathlib import Path

SCHEMA = """
DROP TABLE IF EXISTS dim_candidate; DROP TABLE IF EXISTS dim_requisition;
DROP TABLE IF EXISTS fact_application; DROP TABLE IF EXISTS fact_stage_event;
CREATE TABLE dim_candidate(candidate_id TEXT PRIMARY KEY, source TEXT, created_date TEXT);
CREATE TABLE dim_requisition(requisition_id TEXT PRIMARY KEY, department TEXT, title TEXT, opened_date TEXT);
CREATE TABLE fact_application(application_id TEXT PRIMARY KEY, candidate_id TEXT, requisition_id TEXT, source TEXT, applied_date TEXT);
CREATE TABLE fact_stage_event(application_id TEXT, candidate_id TEXT, requisition_id TEXT, stage TEXT, source TEXT, event_date TEXT);
CREATE INDEX idx_stage ON fact_stage_event(stage);
CREATE INDEX idx_stage_date ON fact_stage_event(stage, event_date);
"""

def build_mart(data: dict, db_path: Path) -> dict:
    db_path = Path(db_path); db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path); con.executescript(SCHEMA)
    con.executemany("INSERT OR REPLACE INTO dim_candidate VALUES (?,?,?)",
                    [(c["candidate_id"], c["source"], c["created_date"]) for c in data["candidates"]])
    con.executemany("INSERT OR REPLACE INTO dim_requisition VALUES (?,?,?,?)",
                    [(r["requisition_id"], r["department"], r["title"], r["opened_date"]) for r in data["requisitions"]])
    con.executemany("INSERT OR REPLACE INTO fact_application VALUES (?,?,?,?,?)",
                    [(a["application_id"], a["candidate_id"], a["requisition_id"], a["source"], a["applied_date"]) for a in data["applications"]])
    con.executemany("INSERT INTO fact_stage_event VALUES (?,?,?,?,?,?)",
                    [(e["application_id"], e["candidate_id"], e["requisition_id"], e["stage"], e["source"], e["event_date"]) for e in data["stage_events"]])
    con.commit()
    counts = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
              for t in ["dim_candidate", "dim_requisition", "fact_application", "fact_stage_event"]}
    con.close(); return counts
