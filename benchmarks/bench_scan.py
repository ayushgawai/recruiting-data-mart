#!/usr/bin/env python
"""Benchmark entrypoint: python benchmarks/bench_scan.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from recmart.benchmark import run
import json
if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
