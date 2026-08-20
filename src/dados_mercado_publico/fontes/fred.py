"""Adaptador do FRED/ALFRED.

A API devolve, por observação, a janela em que aquele valor foi a leitura
corrente. Pedimos a janela real-time inteira para receber todas as safras da
série, e não apenas a leitura de hoje.
"""

import logging
import time
from datetime import date

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from dados_mercado_publico.erros import ErroDeFonte, FonteIndisponivel, SchemaInesperado

URL = "https://api.stlouisfed.org/fred/series/observations"
VERSAO_CONTRATO = "fred.series.observations.v1"

_TENTATIVAS = 3
_TIMEOUT_S = 30.0

_log = logging.getLogger(__name__)


class ObservacaoFred(BaseModel):
    """Uma observação de série do ALFRED, na safra em que foi publicada.

    `data_publicacao` é quando o valor passou a valer para `data_evento`, e
    `vigente_ate` é o último dia em que ele foi a leitura corrente. É esse
    par que permite reconstruir o que se sabia numa data passada. Os quatro
    campos são o contrato estrutural que `analitico.Observacao` exige de
    toda fonte.
    """

    # Campo novo no payload é mudança de schema: precisa parar a ingestão,
    # não passar despercebido para dentro da camada analítica.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    data_evento: date = Field(alias="date")
    data_publicacao: date = Field(alias="realtime_start")
    vigente_ate: date = Field(alias="realtime_end")
    valor: float | None = Field(alias="value")

    @field_validator("valor", mode="before")
    @classmethod
    def _ponto_significa_ausente(cls, valor: object) -> object:
        return None if valor == "." else valor


class RespostaFred(BaseModel):
    # O envelope carrega paginação e ordenação que não são contrato nosso.
    model_config = ConfigDict(extra="ignore")

    observations: list[ObservacaoFred]


def buscar(
    serie: str,
    chave: str,
    cliente: httpx.Client,
    espera_s: float = 1.0,
) -> tuple[bytes, list[ObservacaoFred]]:
    """Devolve o corpo cru e as observações validadas.

    O corpo cru volta junto porque a zona bruta guarda o que a fonte mandou, e
    não a nossa interpretação dele.
    """
    parametros = {
        "series_id": serie,
        "api_key": chave,
        "file_type": "json",
        # A janela real-time completa é o que faz o ALFRED devolver as safras
        # antigas em vez de apenas a corrente.
        "realtime_start": "1776-07-04",
        "realtime_end": "9999-12-31",
    }
    corpo = _obter(parametros, cliente, espera_s)
    try:
        resposta = RespostaFred.model_validate_json(corpo)
    except ValidationError as erro:
        raise SchemaInesperado(f"payload do FRED mudou de forma para {serie}") from erro
    return corpo, resposta.observations


def _obter(parametros: dict[str, str], cliente: httpx.Client, espera_s: float) -> bytes:
    ultima: Exception | None = None
    for tentativa in range(1, _TENTATIVAS + 1):
        try:
            resposta = cliente.get(URL, params=parametros, timeout=_TIMEOUT_S)
        except httpx.TransportError as erro:
            ultima = erro
        else:
            if resposta.status_code < 400:
                return resposta.content
            # 4xx é erro nosso — chave inválida, série inexistente. Repetir não
            # conserta e ainda queima o limite de requisições.
            if resposta.status_code < 500:
                raise ErroDeFonte(f"FRED respondeu {resposta.status_code}")
            ultima = ErroDeFonte(f"FRED respondeu {resposta.status_code}")
        if tentativa < _TENTATIVAS:
            _log.warning("tentativa %d falhou; repetindo", tentativa)
            time.sleep(espera_s * tentativa)

    raise FonteIndisponivel(
        f"FRED não respondeu em {_TENTATIVAS} tentativas"
    ) from ultima
