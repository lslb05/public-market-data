"""Analytics layer: series in Postgres, queryable by knowledge date."""

from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol

import polars as pl
import psycopg

_QUERY_SCHEMA = {"event_date": pl.Date, "value": pl.Float64}


class Observation(Protocol):
    """What every source needs to expose to get into series_vintage.

    Structural, not inherited: each source's contract (FredObservation,
    BcbObservation, ...) lives next to the adapter that produces it, in
    `sources/<source>.py`. This layer doesn't know any of them by name — it
    only requires these four fields.

    Note: these attribute names are Python-side only. The `series_vintage`
    table and its column names (fonte, serie, data_evento, data_publicacao,
    vigente_ate, valor, data_disponibilidade) are a public contract read
    directly via SQL by other projects in the portfolio and must not change
    independently of them — see the SQL literals below.
    """

    event_date: date
    publication_date: date
    valid_until: date
    value: float | None


def publish(
    connection: psycopg.Connection,
    *,
    source: str,
    series: str,
    observations: Sequence[Observation],
    collected_at: datetime,
) -> int:
    """Writes observations and returns the series' total row count.

    The key is (fonte, serie, data_evento, data_publicacao); `ON CONFLICT DO
    NOTHING` makes the first occurrence win, preserving the
    `data_disponibilidade` on which that value was first seen.
    """
    if observations:
        connection.cursor().executemany(
            """
            INSERT INTO series_vintage
                (fonte, serie, data_evento, data_publicacao, vigente_ate,
                 valor, data_disponibilidade)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (fonte, serie, data_evento, data_publicacao) DO NOTHING
            """,
            [
                (
                    source,
                    series,
                    o.event_date,
                    o.publication_date,
                    o.valid_until,
                    o.value,
                    collected_at.date(),
                )
                for o in observations
            ],
        )
    row = connection.execute(
        "SELECT count(*) FROM series_vintage WHERE fonte = %s AND serie = %s",
        (source, series),
    ).fetchone()
    assert row is not None
    return int(row[0])


def exists(connection: psycopg.Connection, *, source: str, series: str) -> bool:
    """Says whether the series has had any observation published yet."""
    row = connection.execute(
        "SELECT 1 FROM series_vintage WHERE fonte = %s AND serie = %s LIMIT 1",
        (source, series),
    ).fetchone()
    return row is not None


def query_at(
    connection: psycopg.Connection, *, source: str, series: str, at: date
) -> pl.DataFrame:
    """Returns the series as it was known on `at`.

    The cutoff is the validity window the source published, not our
    collection date: ALFRED reports when each value started being valid and
    until when it was the current reading. A source without vintages is a
    different story, documented in the README when it arrives.
    """
    rows = connection.execute(
        """
        SELECT data_evento, valor
        FROM series_vintage
        WHERE fonte = %s AND serie = %s
          AND data_publicacao <= %s
          AND vigente_ate >= %s
        ORDER BY data_evento
        """,
        (source, series, at, at),
    ).fetchall()
    return pl.DataFrame(rows, schema=_QUERY_SCHEMA, orient="row")
