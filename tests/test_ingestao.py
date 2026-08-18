import json
from datetime import date
from pathlib import Path

import pytest

from dados_mercado_publico.analitico import consultar_em
from dados_mercado_publico.ingestao import ingerir_fred

from .conftest import CriaCliente


def test_consulta_em_data_passada_ignora_revisao(
    cliente_falso: CriaCliente, corpo_fred: bytes, tmp_path: Path
) -> None:
    cliente, _ = cliente_falso(200, corpo_fred)
    ingerir_fred(serie="GDP", chave="chave", raiz=tmp_path, cliente=cliente)
    parquet = tmp_path / "analitico" / "fred" / "GDP.parquet"

    antes = consultar_em(parquet, serie="GDP", em=date(2020, 5, 1))
    depois = consultar_em(parquet, serie="GDP", em=date(2020, 6, 1))

    assert antes["valor"].to_list() == [pytest.approx(21561.139)]
    assert depois["valor"].to_list() == [pytest.approx(21481.367)]


def test_reingestao_nao_duplica(
    cliente_falso: CriaCliente, corpo_fred: bytes, tmp_path: Path
) -> None:
    cliente, _ = cliente_falso(200, corpo_fred)

    primeira = ingerir_fred(serie="GDP", chave="chave", raiz=tmp_path, cliente=cliente)
    segunda = ingerir_fred(serie="GDP", chave="chave", raiz=tmp_path, cliente=cliente)

    assert primeira == segunda == 3
    assert len(list((tmp_path / "bruto" / "fred" / "GDP").glob("coleta=*"))) == 1


def test_zona_bruta_guarda_o_corpo_original(
    cliente_falso: CriaCliente, corpo_fred: bytes, tmp_path: Path
) -> None:
    cliente, _ = cliente_falso(200, corpo_fred)
    ingerir_fred(serie="GDP", chave="chave", raiz=tmp_path, cliente=cliente)

    particao = next((tmp_path / "bruto" / "fred" / "GDP").glob("coleta=*"))

    assert (particao / "dados.json").read_bytes() == corpo_fred


def test_manifesto_nao_guarda_a_chave_de_api(
    cliente_falso: CriaCliente, corpo_fred: bytes, tmp_path: Path
) -> None:
    cliente, _ = cliente_falso(200, corpo_fred)
    ingerir_fred(
        serie="GDP", chave="segredo-do-usuario", raiz=tmp_path, cliente=cliente
    )

    caminho = next(
        (tmp_path / "bruto" / "fred" / "GDP").glob("coleta=*/manifesto.json")
    )
    manifesto = json.loads(caminho.read_text(encoding="utf-8"))

    assert "segredo-do-usuario" not in manifesto["url"]
    assert manifesto["linhas"] == 3
