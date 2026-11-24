"""Athena scan-bytes model for a 50M-row stage table + scaled-down local measure.

Honest model (documented, not measured on Athena):
- Stage table: 50M rows, Parquet, partitioned by stage (7 values incl. rejected).
- Row: 6 columns. Full scan reads all columns for all rows.
- Pruned query `WHERE stage='interview'`: partition pruning reads 1/7 of rows
  (uniform assumption; real skew changes this) and column pruning reads only
  3 of 6 columns needed (application_id, stage, event_date).
Bytes below are estimates from per-column Parquet sizes (dictionary/RLE
compressed), cross-checked by measuring a scaled-down local dataset.
"""
from __future__ import annotations
import json, time
from pathlib import Path

TOTAL_ROWS = 50_000_000
PARTITIONS = 7
# compressed bytes/row per column in Parquet for this schema (typical)
COL_BYTES = {"application_id": 9, "candidate_id": 9, "requisition_id": 4,
             "stage": 1, "source": 2, "event_date": 4}
QUERY_COLS = ["application_id", "stage", "event_date"]

def estimate(rows: int = TOTAL_ROWS) -> dict:
    full_per_row = sum(COL_BYTES.values())
    pruned_per_row = sum(COL_BYTES[c] for c in QUERY_COLS)
    full = rows * full_per_row
    pruned = (rows // PARTITIONS) * pruned_per_row  # 1 partition, subset of cols
    return {"rows": rows, "full_scan_bytes": full, "pruned_scan_bytes": pruned,
            "full_scan_gb": round(full / 1e9, 2), "pruned_scan_mb": round(pruned / 1e6, 1),
            "reduction_x": round(full / pruned, 1) if pruned else None,
            "athena_cost_full_usd": round(full / 1e12 * 5, 2),   # Athena $5/TB scanned
            "athena_cost_pruned_usd": round(pruned / 1e12 * 5, 4)}

def measure_local(n_candidates: int = 20000):
    """Scaled-down sanity check: time/stage-filter rows on a local synthetic set."""
    from .synthetic import generate
    t0 = time.time(); _, _, _, events = generate(n_candidates, seed=1)
    full_rows = len(events)
    interview = [e for e in events if e["stage"] == "interview"]
    return {"scaled_candidates": n_candidates, "scaled_stage_rows": full_rows,
            "interview_rows": len(interview), "elapsed_s": round(time.time() - t0, 3)}

def run(out: Path | None = None) -> dict:
    result = {"athena_estimate_50m": estimate(), "local_scaled_measure": measure_local()}
    if out:
        Path(out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result

if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
