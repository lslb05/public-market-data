"""Camada analítica: séries em Postgres, consultáveis por data de conhecimento."""

from collections.abc import Sequence
from datetime import date, datetime

import polars as pl
import psycopg

from dados_mercado_publico.contratos import ObservacaoFred

_ESQUEMA_CONSULTA = {"data_evento": pl.Date, "valor": pl.Float64}


def publicar(
    conexao: psycopg.Connection,
    *,
    fonte: str,
    serie: str,
    observacoes: Sequence[ObservacaoFred],
    coletado_em: datetime,
) -> int:
    """Grava observações e devolve o total de linhas da série.

    A chave é (fonte, serie, data_evento, data_publicacao); `ON CONFLICT DO
    NOTHING` faz a primeira ocorrência vencer, preservando a
    `data_disponibilidade` em que aquele valor foi visto pela primeira vez.
    """
    if observacoes:
        conexao.cursor().executemany(
            """
            INSERT INTO series_vintage
                (fonte, serie, data_evento, data_publicacao, vigente_ate,
                 valor, data_disponibilidade)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fonte, serie, data_evento, data_publicacao) DO NOTHING
            """,
            [
                (
                    fonte,
                    serie,
                    o.data_evento,
                    o.data_publicacao,
                    o.vigente_ate,
                    o.valor,
                    coletado_em.date(),
                )
                for o in observacoes
            ],
        )
    linha = conexao.execute(
        "SELECT count(*) FROM series_vintage WHERE fonte = %s AND serie = %s",
        (fonte, serie),
    ).fetchone()
    assert linha is not None
    return int(linha[0])


def existe(conexao: psycopg.Connection, *, fonte: str, serie: str) -> bool:
    """Indica se a série já teve alguma observação publicada."""
    linha = conexao.execute(
        "SELECT 1 FROM series_vintage WHERE fonte = %s AND serie = %s LIMIT 1",
        (fonte, serie),
    ).fetchone()
    return linha is not None


def consultar_em(
    conexao: psycopg.Connection, *, fonte: str, serie: str, em: date
) -> pl.DataFrame:
    """Devolve a série como era conhecida em `em`.

    O corte é a janela de vigência publicada pela fonte, e não a nossa data de
    coleta: o ALFRED informa quando cada valor passou a valer e até quando foi a
    leitura corrente. Fonte sem safra é outra história e fica documentada no
    README quando chegar.
    """
    linhas = conexao.execute(
        """
        SELECT data_evento, valor
        FROM series_vintage
        WHERE fonte = %s AND serie = %s
          AND data_publicacao <= %s
          AND vigente_ate >= %s
        ORDER BY data_evento
        """,
        (fonte, serie, em, em),
    ).fetchall()
    return pl.DataFrame(linhas, schema=_ESQUEMA_CONSULTA, orient="row")
