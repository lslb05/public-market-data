import json

import pytest

from dados_mercado_publico.erros import ErroDeFonte, FonteIndisponivel, SchemaInesperado
from dados_mercado_publico.fontes import fred

from .conftest import CriaCliente


def test_le_safras_e_trata_valor_ausente(
    cliente_falso: CriaCliente, corpo_fred: bytes
) -> None:
    cliente, _ = cliente_falso(200, corpo_fred)

    _, observacoes = fred.buscar("GDP", "chave", cliente)

    assert len(observacoes) == 3
    assert observacoes[0].valor == pytest.approx(21561.139)
    assert observacoes[2].valor is None


def test_campo_novo_no_payload_para_a_ingestao(
    cliente_falso: CriaCliente, corpo_fred: bytes
) -> None:
    payload = json.loads(corpo_fred)
    payload["observations"][0]["confidence_interval"] = "0.4"
    cliente, _ = cliente_falso(200, json.dumps(payload).encode())

    with pytest.raises(SchemaInesperado):
        fred.buscar("GDP", "chave", cliente)


def test_erro_do_cliente_nao_repete(cliente_falso: CriaCliente) -> None:
    cliente, chamadas = cliente_falso(404, b"")

    with pytest.raises(ErroDeFonte):
        fred.buscar("INEXISTENTE", "chave", cliente, espera_s=0)

    assert len(chamadas) == 1


def test_indisponibilidade_esgota_as_tentativas(cliente_falso: CriaCliente) -> None:
    cliente, chamadas = cliente_falso(503, b"")

    with pytest.raises(FonteIndisponivel):
        fred.buscar("GDP", "chave", cliente, espera_s=0)

    assert len(chamadas) == 3
