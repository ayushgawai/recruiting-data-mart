"""Deterministic synthetic candidate/application events (no PII, fake ids)."""
from __future__ import annotations
import csv, json, random
from datetime import date, timedelta
from pathlib import Path
from . import STAGES, SOURCES

DEPTS = ["engineering", "data", "product", "sales", "operations"]
# stage-to-next conversion used by the generator
CONV = {"applied": 0.60, "screen": 0.55, "interview": 0.50, "onsite": 0.45, "offer": 0.70}

def generate(n_candidates: int = 1000, seed: int = 42, start: date = date(2025, 1, 1)):
    """Yield (candidates, applications, stage_events) as lists of dicts."""
    rng = random.Random(seed)
    candidates, applications, events = [], [], []
    app_id = 0
    for cid in range(1, n_candidates + 1):
        source = rng.choice(SOURCES)
        cand = {"candidate_id": f"C{cid:06d}", "source": source,
                "created_date": (start + timedelta(days=rng.randint(0, 180))).isoformat()}
        candidates.append(cand)
        app_id += 1
        req = f"R{rng.randint(1,20):03d}"
        app_date = date.fromisoformat(cand["created_date"]) + timedelta(days=rng.randint(0, 3))
        applications.append({"application_id": f"A{app_id:06d}", "candidate_id": cand["candidate_id"],
                             "requisition_id": req, "source": source, "applied_date": app_date.isoformat()})
        # funnel walk
        current = app_date
        for stage in STAGES:
            events.append({"application_id": f"A{app_id:06d}", "candidate_id": cand["candidate_id"],
                           "requisition_id": req, "stage": stage, "source": source,
                           "event_date": current.isoformat()})
            if stage == "hired":
                break
            if rng.random() > CONV[stage]:
                # rejected/withdrawn after this stage
                events.append({"application_id": f"A{app_id:06d}", "candidate_id": cand["candidate_id"],
                               "requisition_id": req, "stage": "rejected", "source": source,
                               "event_date": (current + timedelta(days=rng.randint(1, 5)) ).isoformat()})
                break
            current += timedelta(days=rng.randint(2, 14))
    requisitions = [{"requisition_id": f"R{i:03d}", "department": DEPTS[i % len(DEPTS)],
                     "title": f"Role {i}", "opened_date": start.isoformat()} for i in range(1, 21)]
    return candidates, applications, requisitions, events

def write_raw(out: Path, n_candidates: int = 1000, seed: int = 42) -> Path:
    """Write raw events partitioned by stage (stage=<s>/events.jsonl), Athena-style."""
    out = Path(out); candidates, apps, reqs, events = generate(n_candidates, seed)
    (out / "candidates.jsonl").write_text("\n".join(json.dumps(r) for r in candidates), encoding="utf-8")
    (out / "applications.jsonl").write_text("\n".join(json.dumps(r) for r in apps), encoding="utf-8")
    (out / "requisitions.jsonl").write_text("\n".join(json.dumps(r) for r in reqs), encoding="utf-8")
    for stage in STAGES + ["rejected"]:
        part = out / "stage_events" / f"stage={stage}"
        part.mkdir(parents=True, exist_ok=True)
        rows = [e for e in events if e["stage"] == stage]
        (part / "events.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return out
