import json

import pytest

from public_market_data.errors import SourceError, SourceUnavailable, UnexpectedSchema
from public_market_data.sources import fred

from .conftest import MakeMockClient


def test_reads_vintages_and_handles_missing_value(
    make_mock_client: MakeMockClient, fred_body: bytes
) -> None:
    client, _ = make_mock_client(200, fred_body)

    _, observations = fred.fetch("GDP", "key", client)

    assert len(observations) == 3
    assert observations[0].value == pytest.approx(21561.139)
    assert observations[2].value is None


def test_new_field_in_payload_stops_ingestion(
    make_mock_client: MakeMockClient, fred_body: bytes
) -> None:
    payload = json.loads(fred_body)
    payload["observations"][0]["confidence_interval"] = "0.4"
    client, _ = make_mock_client(200, json.dumps(payload).encode())

    with pytest.raises(UnexpectedSchema):
        fred.fetch("GDP", "key", client)


def test_client_error_does_not_retry(make_mock_client: MakeMockClient) -> None:
    client, calls = make_mock_client(404, b"")

    with pytest.raises(SourceError):
        fred.fetch("NONEXISTENT", "key", client, wait_s=0)

    assert len(calls) == 1


def test_unavailability_exhausts_the_attempts(make_mock_client: MakeMockClient) -> None:
    client, calls = make_mock_client(503, b"")

    with pytest.raises(SourceUnavailable):
        fred.fetch("GDP", "key", client, wait_s=0)

    assert len(calls) == 3
