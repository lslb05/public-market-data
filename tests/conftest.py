from collections.abc import Callable, Iterator
from pathlib import Path

import httpx
import psycopg
import pytest
from testcontainers.community.postgres import PostgresContainer

from dados_mercado_publico.postgres import conectar

CriaCliente = Callable[[int, bytes], tuple[httpx.Client, list[int]]]


@pytest.fixture
def corpo_fred() -> bytes:
    return (Path(__file__).parent / "fixtures" / "fred_gdp.json").read_bytes()


@pytest.fixture
def cliente_falso() -> CriaCliente:
    """Cria um cliente httpx que responde sempre igual e conta as chamadas."""

    def criar(status: int, corpo: bytes) -> tuple[httpx.Client, list[int]]:
        chamadas: list[int] = []

        def responder(_: httpx.Request) -> httpx.Response:
            chamadas.append(status)
            return httpx.Response(status, content=corpo)

        return httpx.Client(transport=httpx.MockTransport(responder)), chamadas

    return criar


@pytest.fixture(scope="session")
def _postgres_dsn() -> Iterator[str]:
    """Sobe um Postgres efêmero em container para a sessão de testes inteira.

    Um container por sessão em vez de por teste: subir o container é o que
    pesa; isolar dado entre testes é responsabilidade da fixture `conexao`.
    """
    with PostgresContainer("postgres:16-alpine") as container:
        url = container.get_connection_url()
        yield "postgresql://" + url.split("://", 1)[1]


@pytest.fixture
def conexao(_postgres_dsn: str) -> Iterator[psycopg.Connection]:
    conexao = conectar(_postgres_dsn)
    conexao.execute("TRUNCATE TABLE series_vintage")
    yield conexao
    conexao.close()


@pytest.fixture
def dsn(_postgres_dsn: str) -> Iterator[str]:
    conexao = conectar(_postgres_dsn)
    conexao.execute("TRUNCATE TABLE series_vintage")
    conexao.close()
    yield _postgres_dsn
