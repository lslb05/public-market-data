"""Camada analítica: Parquet publicado e consulta por data de conhecimento."""

from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path

import duckdb
import polars as pl

from dados_mercado_publico.contratos import ObservacaoFred

CHAVE = ["serie", "data_evento", "data_publicacao"]

_ESQUEMA_CONSULTA = {"data_evento": pl.Date, "valor": pl.Float64}

_ESQUEMA = {
    "serie": pl.String,
    "data_evento": pl.Date,
    "data_publicacao": pl.Date,
    "vigente_ate": pl.Date,
    "valor": pl.Float64,
    "data_disponibilidade": pl.Date,
}


def publicar(
    destino: Path,
    *,
    serie: str,
    observacoes: Sequence[ObservacaoFred],
    coletado_em: datetime,
) -> int:
    """Acrescenta observações ao Parquet da série e devolve o total de linhas.

    Reingerir o mesmo conteúdo não altera o arquivo: a chave é
    (serie, data_evento, data_publicacao) e a primeira ocorrência vence, o que
    preserva a data de disponibilidade em que aquele valor foi visto primeiro.
    """
    if not observacoes:
        return pl.read_parquet(destino).height if destino.exists() else 0

    novas = pl.DataFrame(
        {
            "serie": [serie] * len(observacoes),
            "data_evento": [o.data_evento for o in observacoes],
            "data_publicacao": [o.data_publicacao for o in observacoes],
            "vigente_ate": [o.vigente_ate for o in observacoes],
            "valor": [o.valor for o in observacoes],
            "data_disponibilidade": [coletado_em.date()] * len(observacoes),
        },
        schema=_ESQUEMA,
    )
    if destino.exists():
        novas = pl.concat([pl.read_parquet(destino), novas])

    quadro = novas.unique(subset=CHAVE, keep="first", maintain_order=True).sort(CHAVE)
    destino.parent.mkdir(parents=True, exist_ok=True)
    quadro.write_parquet(destino)
    return quadro.height


def consultar_em(parquet: Path, *, serie: str, em: date) -> pl.DataFrame:
    """Devolve a série como era conhecida em `em`.

    O corte é a janela de vigência publicada pela fonte, e não a nossa data de
    coleta: o ALFRED informa quando cada valor passou a valer e até quando foi a
    leitura corrente. Fonte sem safra não tem esse par, e ali o limite passa a
    ser `data_disponibilidade` — a diferença está registrada no README.
    """
    with duckdb.connect() as conexao:
        linhas = conexao.execute(
            """
            SELECT data_evento, valor
            FROM read_parquet(?)
            WHERE serie = ?
              AND data_publicacao <= ?
              AND vigente_ate >= ?
            ORDER BY data_evento
            """,
            [str(parquet), serie, em, em],
        ).fetchall()

    # fetchall em vez de .pl(): a conversao nativa do DuckDB para Polars exige
    # pyarrow, e o ganho nao paga a dependencia.
    return pl.DataFrame(linhas, schema=_ESQUEMA_CONSULTA, orient="row")
