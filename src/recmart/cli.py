"""CLI: recmart build --source s3://... | recmart query --stage interview | recmart bench"""
from __future__ import annotations
import argparse, json
from pathlib import Path
from .ingest import ingest
from .models import build_mart
from .queries import funnel, stage_count, time_to_stage, source_roi
from .synthetic import write_raw

DEFAULT_DB = Path("data/mart/recruiting.db")
DEFAULT_RAW = Path("data/raw")

def main(argv=None):
    p = argparse.ArgumentParser(prog="recmart")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build"); b.add_argument("--source", default=str(DEFAULT_RAW),
                        help="s3://bucket/prefix or local raw dir"); b.add_argument("--db", default=str(DEFAULT_DB))
    b.add_argument("--demo", action="store_true", help="generate synthetic raw data first (1000 candidates)")
    q = sub.add_parser("query"); q.add_argument("--stage"); q.add_argument("--db", default=str(DEFAULT_DB))
    q.add_argument("--funnel", action="store_true"); q.add_argument("--time-to-stage", action="store_true")
    q.add_argument("--source-roi", action="store_true")
    be = sub.add_parser("bench"); be.add_argument("--out", default=None)
    args = p.parse_args(argv)

    if args.cmd == "build":
        if args.demo and not args.source.startswith("s3://"):
            write_raw(Path(args.source)); print(f"demo raw data -> {args.source}")
        data = ingest(args.source)
        counts = build_mart(data, Path(args.db))
        print(json.dumps({"db": args.db, "scan": data["scan_stats"], "tables": counts}, indent=2))
    elif args.cmd == "query":
        db = Path(args.db)
        if not db.exists():
            p.error(f"mart not built: {db} (run: recmart build --demo)")
        if args.stage:
            print(json.dumps({"stage": args.stage, "applications": stage_count(db, args.stage)}))
        elif args.time_to_stage:
            print(json.dumps(time_to_stage(db), indent=2))
        elif args.source_roi:
            print(json.dumps(source_roi(db), indent=2))
        else:
            print(json.dumps(funnel(db), indent=2))
    elif args.cmd == "bench":
        from .benchmark import run
        print(json.dumps(run(Path(args.out) if args.out else None), indent=2))

if __name__ == "__main__":
    main()
