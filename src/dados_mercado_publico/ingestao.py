"""Caso de uso: uma execução de ingestão, da fonte à camada analítica."""

import logging
from datetime import UTC, datetime
from pathlib import Path

import httpx
import psycopg

from dados_mercado_publico import bruto
from dados_mercado_publico.analitico import publicar
from dados_mercado_publico.fontes import fred

_log = logging.getLogger(__name__)


def ingerir_fred(
    *,
    serie: str,
    chave: str,
    raiz: Path,
    cliente: httpx.Client,
    conexao: psycopg.Connection,
) -> int:
    """Devolve quantas linhas a série tem depois desta execução."""
    inicio = datetime.now(UTC)
    _log.info("ingestao iniciada fonte=fred serie=%s", serie)

    corpo, observacoes = fred.buscar(serie, chave, cliente)
    manifesto = bruto.gravar(
        raiz / "bruto",
        fonte="fred",
        dataset=serie,
        corpo=corpo,
        # A chave de API fica fora do manifesto de propósito: ele é versionável
        # e não pode carregar credencial.
        url=f"{fred.URL}?series_id={serie}",
        versao_contrato=fred.VERSAO_CONTRATO,
        linhas=len(observacoes),
        coletado_em=inicio,
    )
    if manifesto is None:
        _log.info("conteudo identico ao anterior; sem particao nova serie=%s", serie)

    total = publicar(
        conexao,
        fonte="fred",
        serie=serie,
        observacoes=observacoes,
        coletado_em=inicio,
    )
    _log.info(
        "ingestao concluida serie=%s observacoes=%d linhas=%d duracao_s=%.2f",
        serie,
        len(observacoes),
        total,
        (datetime.now(UTC) - inicio).total_seconds(),
    )
    return total
