from pathlib import Path

import psycopg
import pytest

from public_market_data.cli import main
from public_market_data.ingestion.fred import ingest_fred

from .conftest import MakeMockClient


@pytest.fixture(autouse=True)
def data_in_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, dsn: str) -> None:
    monkeypatch.setenv("PUBLIC_MARKET_DATA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DADOS_MERCADO_PUBLICO_POSTGRES_DSN", dsn)
    monkeypatch.delenv("PUBLIC_MARKET_DATA_FRED_API_KEY", raising=False)


def test_ingest_without_key_explains_instead_of_crashing() -> None:
    assert main(["ingest", "--source", "fred", "--series", "GDP"]) == 2


def test_query_series_not_ingested_fails() -> None:
    assert (
        main(["query", "--source", "fred", "--series", "GDP", "--at", "2020-05-01"])
        == 2
    )


def test_query_prints_that_dates_vintage(
    make_mock_client: MakeMockClient,
    fred_body: bytes,
    tmp_path: Path,
    connection: psycopg.Connection,
    capsys: pytest.CaptureFixture[str],
) -> None:
    client, _ = make_mock_client(200, fred_body)
    ingest_fred(
        series="GDP", api_key="key", root=tmp_path, client=client, connection=connection
    )

    code = main(["query", "--source", "fred", "--series", "GDP", "--at", "2020-05-01"])

    assert code == 0
    assert "21561.139" in capsys.readouterr().out
