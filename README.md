# recruiting-data-mart

Recruiting analytics data mart over candidate/application pipeline data: S3 ingest of candidate and application events, Airflow orchestration, Snowflake/Redshift-style mart models (candidate, application, requisition, stage), funnel and time-to-stage queries, and source-ROI rollups.

## Design

```
                         +----------------------+
  ATS / event producers  |  S3 raw (Hive parts) |
  ---------------------->|  s3://.../candidates.jsonl
                         |            applications.jsonl
                         |            requisitions.jsonl
                         |            stage_events/stage=<stage>/events.jsonl
                         +-----------+----------+
                                     |  ingest (boto3 for s3://, local dir otherwise)
                                     v
                         +-----------+----------+
  Airflow @daily ------> |  recmart build       |  thin DAG: ingest_and_build -> funnel_check
                         +-----------+----------+
                                     v
              +----------------------+----------------------+
              |  Mart (SQLite locally; sql/*.sql for        |
              |  Snowflake/Redshift)                        |
              |    dim_candidate      dim_requisition       |
              |    fact_application   fact_stage_event      |
              +-----+----------------+----------------+-----+
                    v                v                v
              funnel counts   time-to-stage    source-ROI rollup
              (recmart query) (recmart query   (recmart query
                               --time-to-stage) --source-roi)
```

| Layer | Implementation | Notes |
|---|---|---|
| Ingest | `src/recmart/ingest.py` | `s3://` via boto3 (optional extra) downloaded to staging; local dirs read directly with identical layout. Hive-style `stage=<stage>/` partitions enable pruning. |
| Raw layout | `candidates.jsonl`, `applications.jsonl`, `requisitions.jsonl`, `stage_events/stage=<s>/events.jsonl` | JSONL for the demo; Parquet is the production recommendation (benchmark assumes Parquet). |
| Mart models | `src/recmart/models.py` (SQLite) + `sql/*.sql` (Snowflake/Redshift-style) | `dim_candidate`, `dim_requisition`, `fact_application`, `fact_stage_event`. |
| Orchestration | `airflow/dags/recruiting_mart_dag.py` | Daily DAG calling the same functions as the CLI; degrades to importable no-op without Airflow installed. |
| Queries | `src/recmart/queries.py` | Funnel, per-stage count, time-to-stage (avg days from applied), source ROI. |
| Synthetic data | `src/recmart/synthetic.py` | Deterministic (seeded), fake ids only (`C000001`, …), stage conversion probabilities in one place. |
| Benchmark | `src/recmart/benchmark.py`, `benchmarks/bench_scan.py` | Athena scan-bytes *model* for a 50M-row stage table + a scaled-down local measure. |

## Run

```bash
pip install -e .            # core has zero dependencies; Python >= 3.10
recmart build --demo        # generate synthetic raw data (1000 candidates) and build data/mart/recruiting.db
recmart build --source s3://my-bucket/recruiting/events/   # real S3 (pip install -e '.[s3]')
recmart build --source data/raw                            # local raw dir

recmart query --stage interview
recmart query               # funnel (default)
recmart query --time-to-stage
recmart query --source-roi
```

Example `recmart query --stage interview` output shape:

```json
{"stage": "interview", "applications": 123}
```

(The exact number depends on the synthetic seed/data built.)

## Tests

```bash
pip install -e '.[dev]'
python -m pytest tests -q
```

Tests cover: golden funnel counts on a fixed 6-application fixture (`applied 6, screen 4, interview 3, onsite 2, offer 2, hired 1`), exact time-to-stage on that fixture, a partition/pruning check (`stage=interview` scans exactly 1 of 7 partitions / 1 file), monotonicity of the synthetic funnel, and S3 URI parsing. No network or boto3 needed.

## Benchmark (Athena scan bytes, 50M-row stage table)

```bash
python benchmarks/bench_scan.py
# or: recmart bench
```

This is a **modelled estimate, not a measurement on Athena** — scaled down honestly:

- Stage table: 50M rows, Parquet, partitioned by `stage` (7 partitions), 6 columns, ~29 compressed bytes/row.
- Full scan: 50,000,000 × 29 B = **1.45 GB** (~$0.01 at Athena's $5/TB).
- Pruned query (`WHERE stage='interview'`, 3 of 6 columns): 1/7 of rows × 14 B/row ≈ **100.0 MB** (~$0.0005).
- Reduction: **~14.5×**, from partition pruning (7×) × column pruning (~2.07×).

The script also runs a scaled-down local check (20k synthetic candidates, count interview rows and elapsed time) so the logic is exercised without claiming a 50M-row run happened. Uniform partition sizes are assumed; real stage skew (far more `applied` than `hired`) makes pruning *better* for late stages and *worse* for `applied`.

## Limitations (honest)

- **Local execution unverified in the publishing environment:** the session that assembled this repo could not execute `python`/`pytest` (permission mode allowed only read-only commands), so test/benchmark outputs above are derived from the deterministic code and the documented byte model, not copied from a live run. Run `python -m pytest tests -q` and `python benchmarks/bench_scan.py` locally — they are expected to pass, but that was not confirmed before pushing. Pushed anyway per instructions, with this note.
- SQLite is the local mart engine; `sql/*.sql` is Snowflake/Redshift-style and has not been run against either warehouse.
- S3 path requires boto3 and real credentials; it is not integration-tested against AWS here. Athena numbers are estimates from per-column Parquet byte assumptions, not Athena query-stats.
- Source-ROI costs per application are illustrative config constants (`queries.py`), not real spend data. Funnel assumes a linear stage order; skipped stages / re-applications are not modelled. No PII handling, deduplication beyond `INSERT OR REPLACE` on dims, or incremental/CDC loads — full rebuild each run.
- Airflow DAG is minimal (two tasks, no sensors/retries/SLAs) and requires the `airflow` extra.

## License

MIT — see `LICENSE`.
