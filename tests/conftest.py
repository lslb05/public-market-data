from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from public_market_data.postgres import connect

MakeMockClient = Callable[[int, bytes], tuple[httpx.Client, list[int]]]


@pytest.fixture
def fred_body() -> bytes:
    return (Path(__file__).parent / "fixtures" / "fred_gdp.json").read_bytes()


@pytest.fixture
def make_mock_client() -> MakeMockClient:
    """Creates an httpx client that always responds the same way and counts calls."""

    def make(status: int, body: bytes) -> tuple[httpx.Client, list[int]]:
        calls: list[int] = []

        def respond(_: httpx.Request) -> httpx.Response:
            calls.append(status)
            return httpx.Response(status, content=body)

        return httpx.Client(transport=httpx.MockTransport(respond)), calls

    return make


@pytest.fixture(scope="session")
def _postgres_dsn() -> Iterator[str]:
    """Brings up an ephemeral containerized Postgres for the whole test session.

    One container per session instead of per test: bringing up the container
    is what's expensive; isolating data between tests is the `connection`
    fixture's job.
    """
    with PostgresContainer("postgres:16-alpine") as container:
        url = container.get_connection_url()
        yield "postgresql://" + url.split("://", 1)[1]


@pytest.fixture
def connection(_postgres_dsn: str) -> Iterator[psycopg.Connection]:
    connection = connect(_postgres_dsn)
    connection.execute("TRUNCATE TABLE series_vintage")
    yield connection
    connection.close()


@pytest.fixture
def dsn(_postgres_dsn: str) -> Iterator[str]:
    connection = connect(_postgres_dsn)
    connection.execute("TRUNCATE TABLE series_vintage")
    connection.close()
    yield _postgres_dsn
