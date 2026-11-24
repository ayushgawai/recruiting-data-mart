"""Airflow DAG: ingest S3 -> build mart -> funnel checks. Requires apache-airflow (optional extra).

Schedule: daily. Tasks call the same recmart functions the CLI uses, so the
DAG is a thin orchestrator, not a second implementation.
"""
try:
    from airflow import DAG
    from airflow.operators.python import PythonOperator
except ImportError:  # allows importing this file without Airflow installed (tests/docs)
    DAG = None

from datetime import datetime

def _build(**ctx):
    from recmart.ingest import ingest
    from recmart.models import build_mart
    from pathlib import Path
    source = ctx["params"].get("source", "s3://recruiting-raw/events/")
    build_mart(ingest(source), Path("data/mart/recruiting.db"))

def _check(**_):
    from recmart.queries import funnel
    from pathlib import Path
    rows = funnel(Path("data/mart/recruiting.db"))
    assert rows[0]["applications"] >= rows[-2]["applications"], "funnel not monotonic-ish"

if DAG is not None:
    with DAG("recruiting_mart_daily", start_date=datetime(2025, 1, 1), schedule="@daily",
             catchup=False, params={"source": "s3://recruiting-raw/events/"}) as dag:
        PythonOperator(task_id="ingest_and_build", python_callable=_build)
        PythonOperator(task_id="funnel_check", python_callable=_check)
