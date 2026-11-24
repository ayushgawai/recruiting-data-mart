"""S3 ingest of candidate/application events.

Real S3: if boto3 is installed and source is s3://, objects are downloaded
to a local staging dir. Without boto3 / for local paths, the same partition
layout is read directly — so the pipeline is testable offline. Partition
layout (Athena/Hive style):

    <source>/candidates.jsonl
    <source>/applications.jsonl
    <source>/requisitions.jsonl
    <source>/stage_events/stage=<stage>/events.jsonl
"""
from __future__ import annotations
import json, re
from pathlib import Path
from urllib.parse import urlparse

def parse_s3_uri(uri: str) -> tuple[str, str]:
    p = urlparse(uri)
    if p.scheme != "s3" or not p.netloc:
        raise ValueError(f"not an s3 uri: {uri}")
    return p.netloc, p.path.lstrip("/")

def is_s3(uri: str) -> bool:
    return uri.startswith("s3://")

def download_s3(uri: str, staging: Path) -> Path:
    """Download s3 prefix to staging (requires boto3). Raises clearly if absent."""
    try:
        import boto3  # type: ignore
    except ImportError as e:
        raise RuntimeError("boto3 required for s3:// ingest: pip install 'recruiting-data-mart[s3]'") from e
    bucket, prefix = parse_s3_uri(uri)
    s3 = boto3.client("s3")
    staging.mkdir(parents=True, exist_ok=True)
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            rel = key[len(prefix):].lstrip("/") if prefix else key
            if not rel or key.endswith("/"):
                continue
            dest = staging / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, key, str(dest))
    return staging

def resolve_source(source: str, staging: Path | None = None) -> Path:
    if is_s3(source):
        return download_s3(source, staging or Path("data/raw_s3"))
    return Path(source)

def read_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]

def list_partitions(root: Path) -> list[str]:
    base = Path(root) / "stage_events"
    if not base.exists():
        return []
    return sorted(d.name.split("=", 1)[1] for d in base.iterdir() if d.is_dir() and "=" in d.name)

def read_stage_events(root: Path, stage: str | None = None) -> tuple[list[dict], dict]:
    """Read stage events with partition pruning.

    Returns (rows, stats) where stats records partitions/files scanned —
    this is what the pruning test asserts on. If stage is given, only
    stage=<stage>/ is opened (like Athena partition pruning).
    """
    base = Path(root) / "stage_events"
    partitions = list_partitions(root)
    to_scan = [stage] if stage else partitions
    rows, files, scanned_parts = [], 0, []
    for part in to_scan:
        d = base / f"stage={part}"
        if not d.exists():
            continue
        scanned_parts.append(part)
        for f in sorted(d.glob("*.jsonl")):
            files += 1
            rows.extend(read_jsonl(f))
    stats = {"partitions_total": len(partitions), "partitions_scanned": scanned_parts,
             "files_scanned": files, "rows": len(rows)}
    return rows, stats

def ingest(source: str, staging: Path | None = None) -> dict:
    root = resolve_source(source, staging)
    candidates = read_jsonl(root / "candidates.jsonl")
    applications = read_jsonl(root / "applications.jsonl")
    requisitions = read_jsonl(root / "requisitions.jsonl")
    events, stats = read_stage_events(root)
    return {"root": root, "candidates": candidates, "applications": applications,
            "requisitions": requisitions, "stage_events": events, "scan_stats": stats}
