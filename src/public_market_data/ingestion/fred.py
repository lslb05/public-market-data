"""Use case: one ingestion run, from the source to the analytics layer."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg

from public_market_data import raw
from public_market_data.analytics import publish
from public_market_data.sources import fred

_log = logging.getLogger(__name__)


def ingest_fred(
    *,
    series: str,
    api_key: str,
    root: Path,
    client: httpx.Client,
    connection: psycopg.Connection,
) -> int:
    """Returns how many rows the series has after this run."""
    start = datetime.now(UTC)
    _log.info("ingestion started source=fred series=%s", series)

    body, observations = fred.fetch(series, api_key, client)
    manifest = raw.write(
        root / "raw",
        source="fred",
        dataset=series,
        body=body,
        # The API key stays out of the manifest on purpose: it's versionable
        # and must not carry a credential.
        url=f"{fred.URL}?series_id={series}",
        contract_version=fred.CONTRACT_VERSION,
        rows=len(observations),
        collected_at=start,
    )
    if manifest is None:
        _log.info(
            "content identical to the previous run; no new partition series=%s", series
        )

    total = publish(
        connection,
        source="fred",
        series=series,
        observations=observations,
        collected_at=start,
    )
    _log.info(
        "ingestion finished series=%s observations=%d rows=%d duration_s=%.2f",
        series,
        len(observations),
        total,
        (datetime.now(UTC) - start).total_seconds(),
    )
    return total
