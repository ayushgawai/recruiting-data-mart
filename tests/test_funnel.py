"""Golden funnel counts on a fixed 6-application fixture + partition pruning."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from recmart.ingest import read_stage_events
from recmart.models import build_mart
from recmart.queries import funnel, stage_count, time_to_stage, source_roi
from recmart.synthetic import write_raw

# Fixed fixture: A1 reaches hired, A2 offer, A3 interview, A4 screen, A5/A6 applied only
FIXTURE_EVENTS = []
def ev(app, stage, day):
    FIXTURE_EVENTS.append({"application_id": app, "candidate_id": f"C{app[1:]}",
                           "requisition_id": "R001", "stage": stage, "source": "referral",
                           "event_date": f"2025-01-{day:02d}"})
ev("A1","applied",1); ev("A1","screen",3); ev("A1","interview",6); ev("A1","onsite",10); ev("A1","offer",14); ev("A1","hired",16)
ev("A2","applied",1); ev("A2","screen",3); ev("A2","interview",6); ev("A2","onsite",10); ev("A2","offer",14)
ev("A3","applied",1); ev("A3","screen",3); ev("A3","interview",6)
ev("A4","applied",1); ev("A4","screen",3)
ev("A5","applied",1); ev("A6","applied",1)
GOLDEN = {"applied": 6, "screen": 4, "interview": 3, "onsite": 2, "offer": 2, "hired": 1, "rejected": 0}

def _mart(tmp_path):
    data = {
        "candidates": [{"candidate_id": f"C{i}", "source": "referral", "created_date": "2025-01-01"} for i in range(1,7)],
        "requisitions": [{"requisition_id": "R001", "department": "engineering", "title": "Role 1", "opened_date": "2025-01-01"}],
        "applications": [{"application_id": f"A{i}", "candidate_id": f"C{i}", "requisition_id": "R001",
                          "source": "referral", "applied_date": "2025-01-01"} for i in range(1,7)],
        "stage_events": FIXTURE_EVENTS}
    db = tmp_path / "mart.db"; build_mart(data, db); return db

def test_golden_funnel_counts(tmp_path):
    rows = {r["stage"]: r["applications"] for r in funnel(_mart(tmp_path))}
    assert rows == GOLDEN

def test_stage_query_and_time_to_stage(tmp_path):
    db = _mart(tmp_path)
    assert stage_count(db, "interview") == 3
    tts = {r["stage"]: r["avg_days"] for r in time_to_stage(db)}
    assert tts["interview"] == 5.0  # Jan 1 -> Jan 6 for A1,A2,A3
    assert tts["hired"] == 15.0
    roi = source_roi(db)[0]
    assert roi["source"] == "referral" and roi["hires"] == 1 and roi["applications"] == 6

def test_partition_pruning(tmp_path):
    """stage=interview query must scan exactly 1 of 7 partitions."""
    raw = write_raw(tmp_path / "raw", n_candidates=200, seed=7)
    rows, stats = read_stage_events(raw, stage="interview")
    assert stats["partitions_total"] == 7
    assert stats["partitions_scanned"] == ["interview"]
    assert stats["files_scanned"] == 1
    assert all(r["stage"] == "interview" for r in rows)
    all_rows, all_stats = read_stage_events(raw)
    assert all_stats["files_scanned"] == 7 and len(all_rows) > len(rows)

def test_synthetic_funnel_is_monotonic(tmp_path):
    raw = write_raw(tmp_path / "raw", n_candidates=500, seed=42)
    from recmart.ingest import ingest
    db = tmp_path / "m.db"; build_mart(ingest(str(raw)), db)
    counts = [r["applications"] for r in funnel(db) if r["stage"] != "rejected"]
    assert counts == sorted(counts, reverse=True) and counts[0] == 500
