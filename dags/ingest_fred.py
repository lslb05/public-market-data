"""Daily DAG: ingests the configured FRED series and publishes them to series_vintage.

The ingestion logic lives in `public_market_data` (tested by `pytest` outside
Airflow); this module only handles orchestration.
"""

from __future__ import annotations

from datetime import datetime

import httpx
from airflow.decorators import dag, task

from public_market_data.config import Settings
from public_market_data.ingestion.fred import ingest_fred
from public_market_data.postgres import connect

FRED_SERIES = ["GDP"]


@dag(
    dag_id="ingest_fred",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["public-market-data", "fred"],
)
def ingest_fred_dag() -> None:
    @task
    def ingest(series: str) -> int:
        config = Settings()
        if not config.fred_api_key:
            raise RuntimeError("PUBLIC_MARKET_DATA_FRED_API_KEY not set")

        connection = connect(config.postgres_dsn)
        try:
            with httpx.Client() as client:
                return ingest_fred(
                    series=series,
                    api_key=config.fred_api_key,
                    root=config.data_dir,
                    client=client,
                    connection=connection,
                )
        finally:
            connection.close()

    ingest.expand(series=FRED_SERIES)


ingest_fred_dag()
