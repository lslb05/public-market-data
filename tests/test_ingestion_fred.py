import json
from datetime import date
from pathlib import Path

import psycopg
import pytest

from public_market_data.analytics import query_at
from public_market_data.ingestion.fred import ingest_fred

from .conftest import MakeMockClient


def test_query_at_past_date_ignores_later_revision(
    make_mock_client: MakeMockClient,
    fred_body: bytes,
    tmp_path: Path,
    connection: psycopg.Connection,
) -> None:
    client, _ = make_mock_client(200, fred_body)
    ingest_fred(
        series="GDP", api_key="key", root=tmp_path, client=client, connection=connection
    )

    before = query_at(connection, source="fred", series="GDP", at=date(2020, 5, 1))
    after = query_at(connection, source="fred", series="GDP", at=date(2020, 6, 1))

    assert before["value"].to_list() == [pytest.approx(21561.139)]
    assert after["value"].to_list() == [pytest.approx(21481.367)]


def test_reingestion_does_not_duplicate(
    make_mock_client: MakeMockClient,
    fred_body: bytes,
    tmp_path: Path,
    connection: psycopg.Connection,
) -> None:
    client, _ = make_mock_client(200, fred_body)

    first = ingest_fred(
        series="GDP", api_key="key", root=tmp_path, client=client, connection=connection
    )
    second = ingest_fred(
        series="GDP", api_key="key", root=tmp_path, client=client, connection=connection
    )

    assert first == second == 3
    assert len(list((tmp_path / "raw" / "fred" / "GDP").glob("collected=*"))) == 1


def test_raw_zone_keeps_the_original_body(
    make_mock_client: MakeMockClient,
    fred_body: bytes,
    tmp_path: Path,
    connection: psycopg.Connection,
) -> None:
    client, _ = make_mock_client(200, fred_body)
    ingest_fred(
        series="GDP", api_key="key", root=tmp_path, client=client, connection=connection
    )

    partition = next((tmp_path / "raw" / "fred" / "GDP").glob("collected=*"))

    assert (partition / "data.json").read_bytes() == fred_body


def test_manifest_does_not_store_the_api_key(
    make_mock_client: MakeMockClient,
    fred_body: bytes,
    tmp_path: Path,
    connection: psycopg.Connection,
) -> None:
    client, _ = make_mock_client(200, fred_body)
    ingest_fred(
        series="GDP",
        api_key="user-secret",
        root=tmp_path,
        client=client,
        connection=connection,
    )

    path = next((tmp_path / "raw" / "fred" / "GDP").glob("collected=*/manifest.json"))
    manifest = json.loads(path.read_text(encoding="utf-8"))

    assert "user-secret" not in manifest["url"]
    assert manifest["rows"] == 3
