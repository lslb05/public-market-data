from pathlib import Path

import pytest

from dados_mercado_publico.cli import main
from dados_mercado_publico.ingestao import ingerir_fred

from .conftest import CriaCliente


@pytest.fixture(autouse=True)
def dados_em_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DADOS_MERCADO_PUBLICO_DADOS_DIR", str(tmp_path))
    monkeypatch.delenv("DADOS_MERCADO_PUBLICO_FRED_API_KEY", raising=False)


def test_ingerir_sem_chave_orienta_em_vez_de_estourar() -> None:
    assert main(["ingerir", "--fonte", "fred", "--serie", "GDP"]) == 2


def test_consultar_serie_nao_ingerida_falha() -> None:
    assert (
        main(["consultar", "--fonte", "fred", "--serie", "GDP", "--em", "2020-05-01"])
        == 2
    )


def test_consultar_imprime_a_safra_daquela_data(
    cliente_falso: CriaCliente,
    corpo_fred: bytes,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cliente, _ = cliente_falso(200, corpo_fred)
    ingerir_fred(serie="GDP", chave="chave", raiz=tmp_path, cliente=cliente)

    codigo = main(
        ["consultar", "--fonte", "fred", "--serie", "GDP", "--em", "2020-05-01"]
    )

    assert codigo == 0
    assert "21561.139" in capsys.readouterr().out
