from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

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
